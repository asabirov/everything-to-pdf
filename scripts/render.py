#!/usr/bin/env python3
"""Render Markdown, text, images, local HTML or a web page as a PDF."""
import argparse
from base64 import b64encode
from contextlib import contextmanager
import errno
from html import escape
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TEMP_PREFIX = '.everything-to-pdf-'

# Markdown, text and images become local HTML, so they keep the themed render path.
KINDS = {'.html': 'html', '.htm': 'html',
         '.md': 'markdown', '.markdown': 'markdown',
         '.txt': 'text', '.text': 'text', '.log': 'text',
         '.png': 'image', '.jpg': 'image', '.jpeg': 'image',
         '.gif': 'image', '.svg': 'image', '.webp': 'image'}
BROWSERS = ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser')
MAC_BROWSERS = ('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Chromium.app/Contents/MacOS/Chromium')
# Routine platform complaints a headless browser makes whether or not it succeeded.
BROWSER_NOISE = re.compile(r'dbus|org\.freedesktop|gpu|vulkan|libva|fontconfig|'
                           r'sandbox namespace|egl|gl display', re.I)
# Statuses a browser can still get past, because it asks differently: a block on
# the client rather than on the page. 401 is not among them -- any credentials are
# in the URL, and the probe sends them too, so a 401 is a real refusal.
BROWSER_DECIDES = frozenset({403, 405, 406, 501})
# Everything legal in a path or query, so only non-ASCII and spaces get encoded.
URL_SAFE = "/%:@-._~!$&'()*+,;=?"



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
        if role == 'output' and failed.name.startswith(TEMP_PREFIX):
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


def input_kind(target, override):
    """`webpage` for an http(s) URL; for a local file the override, or None for now."""
    if urlsplit(target).scheme.lower() in ('http', 'https'):
        if override not in (None, 'webpage'):
            raise RenderError(f'an http(s) URL is a web page, not {override}')
        return 'webpage'
    # Only `://` means a URL, so a file named `report:v2.md` stays a file.
    if '://' in target:
        raise RenderError('only http and https URLs are supported as web pages')
    if override == 'webpage':
        raise RenderError('--as webpage needs an http(s) URL')
    return override


def local_kind(source, override):
    """Deferred until the input is known to be a readable file, so its own
    diagnostics report a missing path or a directory before an extension."""
    if override:
        return override
    kind = KINDS.get(source.suffix.lower())
    if kind is None:
        raise RenderError(f'input {json.dumps(str(source))}: unrecognised extension; '
                          f'pass --as {{{", ".join(sorted(set(KINDS.values())))}}}')
    return kind


def document_markup(source, kind):
    """Markdown, text or an image as HTML whose relative links resolve beside it."""
    if kind == 'image':
        return (f'<!doctype html><meta charset="utf-8"><title>{escape(source.name)}</title>'
                '<style>img { max-height: 100vh }</style>'
                f'<img src="{quote(source.name)}" alt="{escape(source.name)}">')
    try:
        text = source.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        raise RenderError(f'input {json.dumps(str(source))}: not UTF-8 text') from None
    if kind == 'markdown':
        try:
            import markdown
        except ImportError:
            raise RenderError('Markdown input needs the markdown package '
                              'from requirements.txt') from None
        body = markdown.markdown(text, extensions=['tables', 'fenced_code'])
        style = 'pre, code { font-family: monospace }'
    else:
        body = '<pre>' + escape(text) + '</pre>'
        style = 'pre { font-family: monospace }'
    return (f'<!doctype html><meta charset="utf-8"><title>{escape(source.name)}</title>'
            f'<style>{style}</style>{body}')


def render(source, output, theme, kind):
    from weasyprint import CSS, HTML
    from weasyprint.urls import URLFetcher

    with filesystem('input', source):
        source = source.resolve(strict=True)
        if not source.is_file():
            reason = 'is a directory' if source.is_dir() else 'not a regular file'
            raise OSError(errno.EINVAL, reason, str(source))
    kind = local_kind(source, kind)
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
            page = (dict(filename=str(source)) if kind == 'html' else
                    dict(string=document_markup(source, kind), base_url=source.as_uri()))
            document = HTML(url_fetcher=fetcher, **page).render(stylesheets=styles)
        with filesystem('output', output), tempfile.NamedTemporaryFile(prefix=TEMP_PREFIX, suffix='.pdf',
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


def browser_binary(explicit):
    if explicit:
        if not os.access(explicit, os.X_OK) or not Path(explicit).is_file():
            raise RenderError(f'browser {json.dumps(explicit)}: not an executable file')
        return explicit
    for name in BROWSERS:
        found = shutil.which(name)
        if found:
            return found
    for path in MAC_BROWSERS:
        if os.access(path, os.X_OK):
            return path
    raise RenderError('no Chrome or Chromium on PATH; install one or pass --browser')


def browser_reason(result):
    """The browser's own complaint, without the platform noise it always prints."""
    output = (result.stderr or '') + (result.stdout or '')
    lines = [line for line in output.splitlines()
             if line.strip() and not BROWSER_NOISE.search(line)]
    return compact(lines[-1]) if lines else 'no diagnostic output'


def probe_request(url):
    """urllib needs an ASCII URL and a header for credentials; a browser takes the
    Unicode form, and credentials embedded in it, exactly as the user typed them."""
    parts = urlsplit(url)
    host = parts.hostname or ''
    try:
        netloc = host if host.isascii() else host.encode('idna').decode('ascii')
    except UnicodeError:
        raise RenderError('web page host is not a usable domain name') from None
    if parts.port:
        netloc += f':{parts.port}'
    headers = {}
    if parts.username is not None:
        secret = f'{unquote(parts.username)}:{unquote(parts.password or "")}'
        headers['Authorization'] = 'Basic ' + b64encode(secret.encode()).decode()
    return Request(urlunsplit((parts.scheme, netloc, quote(parts.path, safe=URL_SAFE),
                               quote(parts.query, safe=URL_SAFE), '')),
                   method='HEAD', headers=headers)


def check_reachable(url, timeout):
    """A browser prints its own error page and still exits 0, so probe the URL first.

    Failures a browser cannot get past stop the render: a name that does not
    resolve, a refused connection, a page that is not there. A status blocking the
    client rather than the page is returned instead, for the caller to warn about,
    because only the browser can settle it.
    """
    try:
        with urlopen(probe_request(url), timeout=timeout) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
    except (URLError, OSError, ValueError) as error:
        reason = compact(getattr(error, 'reason', None) or error)
        raise RenderError(f'cannot reach the web page: {reason}') from None
    if status < 400:
        return None
    if status not in BROWSER_DECIDES:
        raise RenderError(f'web page answered HTTP {status} to a HEAD request')
    return status


def render_webpage(url, output, browser, timeout):
    """A second engine: the browser runs the page, so this skill's theme never applies."""
    binary = browser_binary(browser)
    deferred = check_reachable(url, timeout)
    print('notice: a browser prints web pages, so the print theme, the page-number '
          'footer and the offline resource limits do not apply', file=sys.stderr)
    with filesystem('output', output):
        output = output.absolute()
        output.parent.resolve(strict=True)
    profile = Path(tempfile.mkdtemp(prefix='everything-to-pdf-profile-'))
    temp = None
    try:
        with filesystem('output', output), tempfile.NamedTemporaryFile(
                prefix=TEMP_PREFIX, suffix='.pdf', dir=output.parent, delete=False) as handle:
            temp = Path(handle.name)
        command = [binary, '--headless', '--disable-gpu', '--no-first-run',
                   f'--user-data-dir={profile}', '--no-pdf-header-footer',
                   '--generate-pdf-document-outline', f'--print-to-pdf={temp}', url]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RenderError(f'web page did not finish within {timeout:g}s; '
                              'raise --timeout or check the URL') from None
        except OSError as error:
            raise RenderError(f'cannot run the browser: '
                              f'{compact(error.strerror or type(error).__name__)}') from None
        if result.returncode != 0:
            raise RenderError(f'browser exited {result.returncode}: {browser_reason(result)}')
        data = temp.read_bytes()
        # The page objects double as the page count and as proof this is a real PDF.
        pages = len(re.findall(rb'/Type\s*/Page(?![s])', data))
        if not data.startswith(b'%PDF') or not pages:
            raise RenderError(f'browser wrote no readable PDF: {browser_reason(result)}')
        with filesystem('output', output):
            os.replace(temp, output)
        temp = None
        if deferred:
            print(f'warning: the URL answered HTTP {deferred} to the HEAD probe, so '
                  'the browser may have been shown a refusal or login page instead '
                  'of the document; read page 1 before delivering it', file=sys.stderr)
        return pages
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
        shutil.rmtree(profile, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='a local .html, .md, .txt or image file, '
                                      'or an http(s) URL')
    parser.add_argument('output', type=Path)
    parser.add_argument('--as', dest='kind', metavar='KIND',
                        choices=sorted(set(KINDS.values()) | {'webpage'}),
                        help='input kind, when the extension does not say it')
    parser.add_argument('--theme', type=Path, help='theme file; local inputs only')
    parser.add_argument('--browser', help='Chrome or Chromium to print web pages with')
    parser.add_argument('--timeout', type=float, default=90, metavar='SECONDS',
                        help='how long a web page may take (default 90)')
    args = parser.parse_args()
    try:
        kind = input_kind(args.input, args.kind)
        if kind == 'webpage':
            if args.theme is not None:
                raise RenderError('--theme does not apply to a web page; '
                                  'the browser prints it')
            pages = render_webpage(args.input, args.output, args.browser, args.timeout)
        else:
            pages = render(Path(args.input), args.output,
                           args.theme or ROOT / 'assets/design-system.md', kind)
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
