import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a4xkAAAAASUVORK5CYII=')


class Rendering(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.source = self.home / 'source'
        self.source.mkdir()
        self.html = self.source / 'input.html'
        self.pdf = self.home / 'output.pdf'

    def run_cli(self, html, *args, success=True):
        self.html.write_text('<!doctype html><meta charset="utf-8">' + html)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/render.py'),
                                 str(self.html), str(self.pdf), *map(str, args)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0 if success else 1, result.stderr)
        self.assertFalse(list(self.home.glob('.html-to-pdf-*')))
        return result

    def test_paginated_text_bookmarks_and_repeated_header(self):
        rows = ''.join(f'<tr><td>Service {i:03}</td><td>USD {i}</td></tr>' for i in range(100))
        self.run_cli('<h1>Monthly costs</h1><h2>Allocation</h2><table><thead>'
                     '<tr><th>Service name</th><th>Spend</th></tr></thead><tbody>'
                     + rows + '</tbody></table><p>Final sentinel</p>')
        with pymupdf.open(self.pdf) as doc:
            self.assertGreater(len(doc), 2)
            text = ''.join(page.get_text() for page in doc)
            for i in range(100):
                self.assertIn(f'Service {i:03}', text)
            self.assertIn('Final sentinel', text)
            self.assertEqual([row[1] for row in doc.get_toc()], ['Monthly costs', 'Allocation'])
            for page in doc:
                if 'Service 0' in page.get_text():
                    self.assertIn('Service name', page.get_text())

    def test_theme_geometry_and_invalid_theme_preserve_pdf(self):
        default = (ROOT / 'assets/design-system.md').read_text()
        self.run_cli('<h1>Theme sample</h1><p>Preserved content</p>')
        with pymupdf.open(self.pdf) as doc:
            original_width = doc[0].rect.width
        theme = self.home / 'theme.md'
        theme.write_text(default.replace('"A4"', '"Letter"').replace('#586348', '#AA2233'))
        self.run_cli('<h1>Theme sample</h1>', '--theme', theme)
        with pymupdf.open(self.pdf) as doc:
            self.assertNotEqual(doc[0].rect.width, original_width)
            colors = [s['color'] for b in doc[0].get_text('dict')['blocks'] if 'lines' in b
                      for line in b['lines'] for s in line['spans']]
            self.assertIn(0xAA2233, colors)
        example = (ROOT / 'examples/monthly-finops.html').read_text()
        theme.write_text(default.replace('#F3F1EA', '#112233').replace('#DCDCD2', '#CC4455'))
        for override in ('', '<style>.metrics td {background: #223344} .rule {border-color: #556677}</style>'):
            self.run_cli(example + override, '--theme', theme)
            with pymupdf.open(self.pdf) as doc:
                page = doc[0]
                metric = page.search_for('$84,240')[0]
                pixel = page.get_pixmap().pixel(int(metric.x0 - 2), int(metric.y0 + 2))
                expected_pixel = (34, 51, 68) if override else (17, 34, 51)
                # Raster conversion can round an RGB channel down by one.
                for actual, expected in zip(pixel, expected_pixel):
                    self.assertLessEqual(abs(actual - expected), 1)
                review = page.search_for('Monthly FinOps review')[0]
                rules = [d for d in page.get_drawings()
                         if d['rect'].width > 400
                         and review.y0 - 20 < d['rect'].y0 < review.y0]
                self.assertTrue(rules, 'example rule must be present above review text')
                expected = (85, 102, 119) if override else (204, 68, 85)
                self.assertEqual(tuple(round(c * 255) for c in rules[0]['fill']), expected)
        prior = self.pdf.read_bytes()
        for bad in (default.replace('"size_pt"', '"unknown"'),
                    default.replace('"sans-serif"', '"serif; background:url(x)"'),
                    default.replace('"size_pt": 10', '"size_pt": true'),
                    default.replace('"size_pt": 10', '"size_pt": NaN'),
                    default.replace('"size_pt": 10', '"size_pt": 10, "size_pt": 12'),
                    default + '\n```json\n{}\n```\n', '```json\n{bad}\n```'):
            with self.subTest(theme=bad[:20]):
                theme.write_text(bad)
                self.run_cli('<h1>Bad theme</h1>', '--theme', theme, success=False)
                self.assertEqual(self.pdf.read_bytes(), prior)

    def test_assets_failure_recovery_and_warning(self):
        self.run_cli('<p>Original</p>')
        prior = self.pdf.read_bytes()
        outside = self.home / 'outside.png'
        outside.write_bytes(PNG)
        (self.source / 'escape.png').symlink_to(outside)
        for asset in ('missing.png', '../outside.png', 'escape.png',
                      'https://example.invalid/logo.png', 'file://remote/logo.png'):
            result = self.run_cli(f'<img src="{asset}"><p>Changed</p>', success=False)
            if asset == 'missing.png':
                self.assertIn('missing.png: missing file', result.stderr)
            self.assertNotIn('%s', result.stderr)
            self.assertEqual(self.pdf.read_bytes(), prior)
        self.run_cli('<link rel="stylesheet" href="missing.css"><p>CSS failure</p>', success=False)
        self.assertEqual(self.pdf.read_bytes(), prior)
        (self.source / 'broken.png').write_text('not an image')
        self.run_cli('<img src="broken.png">', success=False)
        assets = self.source / 'assets'
        assets.mkdir()
        (assets / 'pixel.png').write_bytes(PNG)
        (assets / 'style.css').write_text('p {background-image:url(pixel.png)}')
        result = self.run_cli('<link rel="stylesheet" href="assets/style.css">'
                             '<p>Recovered</p><img src="assets/pixel.png">'
                             '<style>p {made-up-property: yes}</style>')
        self.assertIn('warning: renderer:', result.stderr)
        self.assertIn(str(self.pdf), result.stdout)
        with pymupdf.open(self.pdf) as doc:
            self.assertIn('Recovered', doc[0].get_text())
            self.assertTrue(doc[0].get_images())
        # Failures must identify the responsible role, actual path, and reason.
        missing = self.home / 'missing.html'
        missing_theme = self.home / 'missing-theme.md'
        missing_parent = self.home / 'missing-output'
        readonly = self.home / 'readonly'
        readonly.mkdir()
        protected = self.source / 'protected.html'
        protected.write_text('<p>Protected</p>')
        protected.chmod(0)
        readonly.chmod(0o500)
        try:
            cases = [
                (missing, self.pdf, [], 'input', missing, 'missing'),
                (self.source, self.pdf, [], 'input', self.source, 'directory'),
                (self.html, self.pdf, ['--theme', missing_theme], 'theme', missing_theme, 'missing'),
                (self.html, self.pdf, ['--theme', self.source], 'theme', self.source, 'directory'),
                (self.html, missing_parent / 'out.pdf', [], 'output', missing_parent, 'missing'),
                (self.html, self.source, [], 'output', self.source, 'directory'),
            ]
            if os.name == 'posix' and os.geteuid() != 0:
                cases += [
                    (protected, self.pdf, [], 'input', protected, 'permission'),
                    (self.html, self.pdf, ['--theme', protected], 'theme', protected, 'permission'),
                    (self.html, readonly / 'out.pdf', [], 'output', readonly, 'permission'),
                ]
            saved = self.pdf.read_bytes()
            for source, output, args, role, path, reason in cases:
                with self.subTest(role=role, path=path, reason=reason):
                    result = subprocess.run([sys.executable, str(ROOT / 'scripts/render.py'),
                                             str(source), str(output), *map(str, args)],
                                            capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(role, result.stderr)
                    self.assertIn(str(path), result.stderr)
                    self.assertIn(reason, result.stderr.lower())
                    self.assertLess(len(result.stderr), 600)
                    self.assertEqual(self.pdf.read_bytes(), saved)
                    self.assertFalse(list(self.home.rglob('.html-to-pdf-*')))
        finally:
            readonly.chmod(0o700)
            protected.chmod(0o600)
        self.pdf = self.home / ('long  directory ' + 'x' * 150) / 'full  output.pdf'
        self.pdf.parent.mkdir()
        result = self.run_cli('<p>Long output path</p>')
        self.assertEqual(json.loads(result.stdout.split(': ', 1)[1]), str(self.pdf))
        encoded = base64.b64encode(PNG).decode()
        self.run_cli(f'<img src="data:image/png;base64,{encoded}"><p>Embedded</p>')


if __name__ == '__main__':
    unittest.main()
