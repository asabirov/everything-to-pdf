# everything-to-pdf

Convert Markdown, text or code, images, local HTML or a web page to PDF.

It is an agent skill ([SKILL.md](SKILL.md)) with a deterministic command-line
renderer behind it. The agent picks a theme and runs the renderer once; the
renderer turns the input into a paginated PDF without changing its content.

![Page 1 of the bundled example, rendered with the default theme](docs/example-page-1.png)

*Page 1 of [examples/monthly-finops.html](examples/monthly-finops.html), rendered
with the bundled theme. The company and figures are synthetic.*

## Why it exists, and what it turned down

An agent asked for a PDF should hand back the document it was given, laid out for
print, not a rewritten version of it. This skill renders the supplied content as it
is, in one deterministic pass.

What it does not do:

- **No LLM rendering loop.** The model chooses the theme. The renderer does the rest.
- **No browser for local files.** Local inputs go through WeasyPrint, which runs no
  JavaScript and fetches nothing from the network. Only a web page needs a browser.
- **No summarizing or editing.** It does not shorten content, edit existing PDFs or
  convert office documents.
- **No promises it can't keep.** It does not promise browser-perfect CSS, PDF/UA
  conformance, or byte-identical output across platforms or renderer and font
  upgrades.

## The design

### Two engines

The input decides the engine, and the engine decides what you get.

```mermaid
flowchart LR
    md[Markdown] --> html[Local HTML]
    txt[Text or code] --> html
    img[Image] --> html
    file[HTML file] --> html
    html --> wp["WeasyPrint<br>themed, offline, files confined"]
    url[http/https URL] --> probe[HEAD probe] --> chrome["Headless Chrome<br>no theme, runs JavaScript"]
    wp --> pdf[PDF]
    chrome --> pdf
```

| Input | Recognized by | Engine | Theme |
| --- | --- | --- | --- |
| Local HTML | `.html`, `.htm` | WeasyPrint | applies |
| Markdown | `.md`, `.markdown` | WeasyPrint | applies |
| Text, code | `.txt`, `.text`, `.log`, or `--as text` | WeasyPrint | applies |
| Image | `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp` | WeasyPrint | applies |
| Web page | an http or https URL | headless Chrome | does not apply |

Markdown, text and images are turned into local HTML first, so they get everything
local HTML gets. Markdown supports tables and fenced code blocks, and its headings
become PDF bookmarks. It passes raw HTML through, so a Markdown file can carry its own
`<style>` block and is trusted as much as an HTML file. Text and code are escaped, set
in monospace, and wrapped. A tall image is scaled to fit one page. An unknown
extension fails and asks for `--as html|markdown|text|image|webpage` instead of
guessing.

### Web pages are the exception

WeasyPrint can't run JavaScript or fetch from the network, so a URL goes to Chrome or
Chromium. The CLI prints a notice on every web-page render, because the PDF loses:

- the theme: `--theme` with a URL is an error;
- the page-number footer and the theme's paper size and margins. The page's own print
  CSS sets the paper, or Chrome's Letter default if it sets nothing;
- the offline guarantee and file confinement. Chrome fetches whatever the page asks
  for and runs its scripts.

It keeps bookmarks from headings, the atomic output replacement and the page count.

**Chrome exits 0 even when it printed the wrong page, so read page 1.** Before
starting Chrome, the CLI sends a HEAD request. It fails on a name that does not
resolve, a refused connection, an error status, or a redirect loop. Two cases still
get through. A login screen or bot check answers 200. A 403, 405, 406 or 501 may be
blocking the probe rather than the page, so the CLI passes it to Chrome and prints a
warning naming the status.

A URL with credentials (`https://user:pass@host/`) is refused. For a page behind a
login, save it from your browser and render the saved file.

The probe and Chrome see slightly different networks. The probe uses Python's CA
bundle and the `*_proxy` variables, not Chrome's root store and system proxy. It also
encodes international host names with Python's IDNA codec, which differs from
Chrome's for a few characters: `faß.de` becomes `fass.de` here but `xn--fa-hia.de` in
Chrome.

`--timeout` (default 90 seconds) bounds the probe and the wait for the PDF separately,
so a URL that stalls at both takes about twice as long. On macOS Chrome keeps running
after it writes the PDF. The CLI therefore waits until the file is complete and has
stopped growing, then ends the browser. Normally that takes a fraction of a second,
but a browser that ignores two requests to quit can add 20 seconds. If Chrome reports
that it could not load the page, the CLI stops and repeats Chrome's message. Chrome
prints once the page has loaded, so anything a script adds more than about half a
second later is missing.

Chrome runs with its own sandbox and a throwaway profile, never yours. It is still a
full browser, so isolate untrusted URLs externally. A web PDF shows one fetch at one
moment; record the URL and the time with it.

### Themes

For local inputs the agent picks the theme in this order: a theme the user names,
then the project's own design system, then the bundled fallback. To find a design
system it reads the project instructions, the design files they name,
`docs/design-system.md`, and the available skill catalog for a matching brand design
skill. It does not crawl the project. If the user asked for a theme that can't be
found, the agent reports it instead of quietly using the fallback.

A theme is a Markdown file with one strict JSON block. Copy
[assets/print-theme.md](assets/print-theme.md) into your project, map your design
tokens into its JSON once, note the source in its prose, and pass it with
`--theme /path/to/print-theme.md`. Only the JSON affects rendering. Unknown,
duplicate, unsafe or malformed tokens fail before any output is written.

The bundled fallback uses the light sRGB grays from
[Vercel Geist](https://vercel.com/geist/colors) with print choices of its own: A4,
18 mm margins, 10 pt generic sans-serif. It does not ship Geist fonts. The CLI never
discovers design systems, looks anything up online or downloads fonts. Without
`--theme` it always uses the fallback.

`typography.family` accepts only `sans-serif`, `serif` or `monospace`. For a brand
font, add `@font-face` in the source CSS or a linked local stylesheet, with font files
you are allowed to use placed beside the input. Remote font URLs are blocked. Text,
code and image inputs have a small stylesheet of their own that the theme does not
override.

Source CSS takes precedence over the skill's defaults. Put custom CSS inline or in a
linked local stylesheet; there is no CSS flag. Headings become bookmarks, table
headers repeat across pages, and rows try to stay together. Wide tables, long rows,
fixed positioning and fixed-height boxes can still overflow, so look at the pages.
The converter never hides or rewrites content, but source CSS can hide it. For local
inputs, scripts, video and interactive widgets do not render.

### Files and trust

For a local input, resources resolve against the real input file, and a linked
stylesheet resolves against itself. For a symlinked input, assets belong beside the
target, not the symlink. Allowed resources are embedded `data:` URIs and regular files
inside the input's own directory tree. Network resources, parent traversal and
symlinks pointing outside fail the render. Move shared assets into that tree rather
than widening access. A missing image or stylesheet fails the render. Unsupported CSS
only produces a warning. Plain hyperlinks stay links and are not fetched. Diagnostics
stop at six messages plus a count, and embedded data URIs are redacted.

This is not a sandbox for hostile input. Native libraries, system fonts, resource
exhaustion and files changing mid-render are outside these checks. For untrusted
documents or URLs, use external filesystem and network isolation with CPU, memory and
time limits, and don't render mutually untrusted tenants in one process.

Output is written to a temporary file in the target directory and then moved into
place. A failed render leaves an earlier PDF untouched. A killed process can leave a
`.everything-to-pdf-*.pdf` file behind; it is safe to delete.

## What's where

| Path | What it owns |
| --- | --- |
| [SKILL.md](SKILL.md) | What the agent does: choosing the engine and theme, what to tell the user, how to check the PDF. Holds the skill version. |
| [scripts/render.py](scripts/render.py) | The renderer and CLI. It reads only the theme it is given; all theme discovery happens in the agent. |
| [assets/print-theme.md](assets/print-theme.md) | The bundled fallback theme, and the template for your own. |
| [examples/monthly-finops.html](examples/monthly-finops.html) | A synthetic report to try the renderer on. It is an example, not a template. |
| [tests/test_render.py](tests/test_render.py) | Tests that render real PDFs and inspect them with PyMuPDF. |
| [CHANGELOG.md](CHANGELOG.md) | Changes by version. |

## How to run and verify it

### Install

You need Python 3.10 or later and WeasyPrint's native Pango and font libraries; see
the [WeasyPrint installation guide](https://doc.courtbouillon.org/weasyprint/v69.0/first_steps.html#installation).
On macOS, Homebrew supplies them. On Debian or Ubuntu:

```sh
sudo apt-get install python3-venv libpango-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core
```

Web pages also need Google Chrome or Chromium. The CLI looks for `google-chrome`,
`google-chrome-stable`, `chromium` or `chromium-browser` on `PATH`, then the standard
macOS application paths. `--browser PATH` overrides that. Nothing else needs a
browser.

Copy this folder into your agent's skills directory as `everything-to-pdf` (for
Codex, `${CODEX_HOME:-$HOME/.codex}/skills/everything-to-pdf`). No installer runs.
Keep the virtual environment outside the skill folder:

```sh
python3 -m venv ~/.local/share/everything-to-pdf/venv
~/.local/share/everything-to-pdf/venv/bin/pip install -r /path/to/everything-to-pdf/requirements.txt
```

[requirements.txt](requirements.txt) pins WeasyPrint and Markdown. It pins the
renderer, not its own dependencies, your browser or your system fonts.

### Render the example

```sh
cd /path/to/everything-to-pdf
mkdir -p /tmp/out
~/.local/share/everything-to-pdf/venv/bin/python scripts/render.py examples/monthly-finops.html /tmp/out/report.pdf
```

```text
rendered 2 page(s): "/tmp/out/report.pdf"
```

The image at the top of this page is page 1 of that PDF. The output directory must
already exist. The CLI prints the page count and the JSON-escaped output path, sends
warnings to stderr, and exits with:

| Exit code | Meaning |
| --- | --- |
| 0 | PDF written |
| 1 | Render or validation failed; an earlier PDF is untouched |
| 2 | Wrong command-line syntax |

Other forms, run with the same Python from the skill folder:

```sh
render.py NOTES.md OUT.pdf
render.py IN.html OUT.pdf --theme /path/to/print-theme.md
render.py helper.py OUT.pdf --as text
render.py https://example.com/page OUT.pdf
```

### Run the tests

The tests need PyMuPDF to read the PDFs back. Without it the suite stops at an import
error.

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-test.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

```text
Ran 6 tests in 26.386s

OK
```

That run was on macOS with Chrome installed. The tests cover content, pagination,
bookmarks, theme geometry and validation, Markdown, text and image inputs, local,
nested and embedded resources, refused and broken assets, warnings and output
recovery. The web-page test serves a JavaScript page on localhost; it is skipped
when no browser is installed, so a pass on such a machine covers one test fewer.
Rendering and testing need no agent API and no outbound network. GitHub Actions does
not run these tests, so run them before opening a pull request.

### Update and remove

Before updating, back up the skill folder and its virtual environment together.
Install the new release, build a fresh environment from its requirements, and run the
example and tests before switching over. To roll back, restore both. To uninstall,
delete the skill folder, then its environment. Your sources, themes and PDFs are
never touched.

## License

[MIT](LICENSE)
