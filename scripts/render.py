#!/usr/bin/env python3
"""Render trusted local static HTML with a validated print theme."""
import argparse
from contextlib import contextmanager
import errno
import json
import logging
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class RenderError(Exception):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RenderError('theme contains duplicate keys')
        result[key] = value
    return result


def theme_css(path):
    """Exactly one JSON fence; complete schema, no Markdown interpretation."""
    blocks = re.findall(r'^```json\s*\n(.*?)^```[ \t]*$',
                        path.read_text(encoding='utf-8'), re.M | re.S)
    if len(blocks) != 1:
        raise RenderError('theme needs exactly one fenced json block')
    try:
        tokens = json.loads(blocks[0], object_pairs_hook=unique_object)
    except ValueError:
        raise RenderError('theme JSON is malformed') from None
    schema = {
        'colors': {'text', 'muted', 'accent', 'surface', 'border'},
        'typography': {'family', 'size_pt', 'line_height'},
        'spacing': {'block_mm', 'cell_mm'},
        'page': {'size', 'margin_mm'},
    }
    if not isinstance(tokens, dict) or tokens.keys() != schema.keys():
        raise RenderError('theme must contain only colors, typography, spacing, page')
    for group, keys in schema.items():
        if not isinstance(tokens[group], dict) or tokens[group].keys() != keys:
            raise RenderError(f'theme {group} has missing or unknown keys')
    for value in tokens['colors'].values():
        if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            raise RenderError('theme colors must be six-digit hex colors')
    t, s, p, c = (tokens[k] for k in ('typography', 'spacing', 'page', 'colors'))
    if t['family'] not in ('sans-serif', 'serif', 'monospace'):
        raise RenderError('theme family must be sans-serif, serif, or monospace')
    if p['size'] not in ('A4', 'Letter'):
        raise RenderError('theme page size must be A4 or Letter')
    for label, value, low, high in (
        ('size_pt', t['size_pt'], 8, 18), ('line_height', t['line_height'], 1.1, 2),
        ('block_mm', s['block_mm'], 1, 12), ('cell_mm', s['cell_mm'], 1, 6),
        ('margin_mm', p['margin_mm'], 10, 35),
    ):
        if type(value) not in (int, float) or not low <= value <= high:
            raise RenderError(f'theme {label} must be a number from {low} to {high}')
    properties = '; '.join(f'--color-{key}: {value}' for key, value in c.items())
    return f'''
:root {{ {properties}; }}
@page {{ size: {p['size']}; margin: {p['margin_mm']}mm;
  @bottom-right {{ content: counter(page); color: {c['muted']}; font-size: 8pt; }} }}
html {{ font-family: {t['family']}; font-size: {t['size_pt']}pt;
  line-height: {t['line_height']}; color: {c['text']}; }}
p, ul, ol, table, blockquote {{ margin-block: {s['block_mm']}mm; }}
h1, h2, h3, a {{ color: {c['accent']}; }}
th, td {{ padding: {s['cell_mm']}mm; border-bottom: 0.25mm solid {c['border']}; }}
th, blockquote {{ background: {c['surface']}; }}
.muted, caption, small {{ color: {c['muted']}; }}
'''


def compact(value):
    text = re.sub(r'data:[^\s\"\']+', '[embedded resource]', str(value))
    return ' '.join(text.split())[:160]


@contextmanager
def filesystem(role, path):
    """Identify the failed operation without exposing unbounded OS diagnostics."""
    try:
        yield
    except OSError as error:
        failed = Path(error.filename2 or error.filename or path)
        if role == 'output' and failed.name.startswith('.html-to-pdf-'):
            failed = failed.parent
        label = str(failed.absolute())
        if len(label) > 240:
            label = label[:80] + '…' + label[-159:]
        reason = ('missing file or directory' if isinstance(error, FileNotFoundError)
                  else 'permission denied' if isinstance(error, PermissionError)
                  else compact(error.strerror or type(error).__name__))
        raise RenderError(f'{role} {json.dumps(label)}: {reason}') from None


class Diagnostics(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.errors = 0
        self.count = 0

    def emit(self, record):
        self.errors += record.levelno >= logging.ERROR
        self.count += 1
        if self.count <= 6:
            # Bound and redact arguments before interpolating renderer diagnostics.
            args = record.args
            if isinstance(args, tuple):
                args = tuple(compact(arg) if not isinstance(arg, (int, float)) else arg for arg in args)
            elif isinstance(args, dict):
                args = {key: compact(value) for key, value in args.items()}
            try:
                message = str(record.msg) % args if args else str(record.msg)
            except (TypeError, ValueError):
                message = str(record.msg)
            print(f'warning: renderer: {compact(message)}', file=sys.stderr)


def render(source, output, theme):
    from weasyprint import CSS, HTML
    from weasyprint.urls import URLFetcher

    with filesystem('input', source):
        source = source.resolve(strict=True)
        if not source.is_file():
            reason = 'is a directory' if source.is_dir() else 'not a regular HTML file'
            raise OSError(errno.EINVAL, reason, str(source))
    with filesystem('theme', theme):
        theme = theme.resolve(strict=True)
        css = theme_css(theme)
    with filesystem('output', output):
        output = output.absolute()
        if output.resolve() in (source, theme):
            raise RenderError('output must not replace input or theme')
    root = source.parent

    class LocalFetcher(URLFetcher):
        def __init__(self):
            super().__init__(allowed_protocols={'file', 'data'})
            self.failed = False

        def fetch(self, url, headers=None):
            try:
                parsed = urlsplit(url)
                if parsed.scheme == 'file':
                    if parsed.netloc not in ('', 'localhost'):
                        raise RenderError('remote file authority is forbidden')
                    asset = Path(unquote(parsed.path)).resolve(strict=True)
                    if not asset.is_relative_to(root) or not asset.is_file():
                        raise RenderError('asset is outside source directory or not a file')
                    if asset == output.resolve():
                        raise RenderError('output cannot also be a resource')
                    url = asset.as_uri()
                elif parsed.scheme != 'data':
                    raise RenderError('network resources are forbidden; copy assets beside input')
                return super().fetch(url, headers)
            except Exception as error:
                self.failed = True
                if isinstance(error, FileNotFoundError):
                    reason = 'missing file'
                elif isinstance(error, RenderError):
                    reason = str(error)
                else:
                    reason = f'cannot read resource ({type(error).__name__})'
                # Drop URL query/fragment and embedded data; show a useful local path.
                try:
                    parts = urlsplit(url)
                    label = unquote(parts.path) if parts.scheme == 'file' else parts.scheme + ': resource'
                except ValueError:
                    label = 'malformed resource URL'
                logging.getLogger('weasyprint').error('%s: %s', compact(label), reason)
                raise RenderError(reason) from None

    fetcher = LocalFetcher()
    diagnostics = Diagnostics()
    logger = logging.getLogger('weasyprint')
    old_handlers, old_level, old_propagate = logger.handlers[:], logger.level, logger.propagate
    logger.handlers, logger.propagate = [diagnostics], False
    logger.setLevel(logging.WARNING)
    temp = None
    try:
        styles = [CSS(string=(ROOT / 'assets/print.css').read_text(encoding='utf-8')),
                  CSS(string=css)]
        with filesystem('input', source):
            document = HTML(filename=str(source), url_fetcher=fetcher).render(stylesheets=styles)
        with filesystem('output', output), tempfile.NamedTemporaryFile(prefix='.html-to-pdf-', suffix='.pdf',
                                         dir=output.parent, delete=False) as handle:
            temp = Path(handle.name)
            document.write_pdf(handle)
            handle.flush()
            os.fsync(handle.fileno())
        if fetcher.failed or diagnostics.errors:
            raise RenderError('render failed: resource or renderer errors; prior output preserved')
        with filesystem('output', output):
            os.replace(temp, output)
        temp = None
        return len(document.pages)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
        logger.handlers, logger.level, logger.propagate = old_handlers, old_level, old_propagate
        if diagnostics.count > 6:
            print(f'warning: {diagnostics.count - 6} more renderer diagnostics suppressed', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--theme', type=Path, default=ROOT / 'assets/design-system.md')
    args = parser.parse_args()
    try:
        pages = render(args.input, args.output, args.theme)
    except RenderError as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    except (OSError, ValueError, ImportError) as error:
        print(f'error: runtime {type(error).__name__}; check runtime installation', file=sys.stderr)
        return 1
    except Exception as error:
        print(f'error: renderer failed ({type(error).__name__}); prior output preserved', file=sys.stderr)
        return 1
    print(f'rendered {pages} page(s): {json.dumps(str(args.output.absolute()))}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
