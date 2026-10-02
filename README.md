# everything-to-pdf

An agent skill and deterministic CLI that turns Markdown, plain text or code, an
image, local static HTML, or a web page into a PDF. Local inputs render with
WeasyPrint 69.0 through a minimalist, themeable print stylesheet; a web page is
printed by headless Chrome, which is a different engine with different guarantees.
The skill keeps the supplied content intact: it does not summarize, edit existing
PDFs, or operate an LLM rendering loop. It does not promise arbitrary browser CSS
fidelity or PDF/UA conformance.

The skill version lives in `metadata.version` in `SKILL.md`.

## Inputs

| Input | Recognized by | Engine | Theme |
| --- | --- | --- | --- |
| Local static HTML | `.html`, `.htm` | WeasyPrint | applies |
| Markdown | `.md`, `.markdown` | WeasyPrint | applies |
| Plain text, code | `.txt`, `.text`, `.log`, `--as text` | WeasyPrint | applies |
| Image | `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp` | WeasyPrint | applies |
| Web page | an `http`/`https` URL | headless Chrome | does not apply |

Markdown, text and images are converted to local HTML and rendered on the WeasyPrint
path, so they keep its guarantees: no JavaScript, no network, resources confined to
the input's own directory, and the theme governing the output. Relative links resolve
beside the input file, so a Markdown image sits next to the Markdown. Markdown
supports tables and fenced code blocks; its headings become bookmarks. As Markdown
normally does, it passes raw HTML through, so a Markdown file can carry its own
`<style>` block and is trusted exactly as much as an HTML input — the resource
confinement still applies to anything that HTML asks for. Text and code
are escaped rather than interpreted and set in monospace, with long lines wrapped. A
tall image is scaled to fit one page. `--as html|markdown|text|image|webpage` names
the kind when the extension does not, as with a code file; an unrecognized extension
fails and asks for `--as` rather than guessing.

## Web pages

A web page goes through Chrome or Chromium instead, because WeasyPrint runs no
JavaScript and fetches nothing over the network. That is a real trade, and the CLI
prints it as a notice on every web-page render. A web page loses:

- the theme — `--theme` with a URL is an error, not a silent no-op;
- the page-number footer, and the theme's paper size and margins. The paper comes
  from the page's own print CSS; Chrome's Letter default applies only when the page
  declares nothing, and no flag overrides either;
- the offline guarantee and the resource confinement: Chrome fetches whatever the
  page requests, from wherever, and runs its JavaScript.

It keeps bookmarks from headings, the atomic output replacement, and the reported
page count.

**A web-page render can succeed on the wrong page, so read page 1.** Chrome prints
whatever it is shown and exits 0 either way — including its own "site can't be
reached" page. The CLI therefore sends a HEAD request first and fails on a name that
does not resolve, a refused connection, a status that means the page is not there, or
redirects that never arrive anywhere. Two things still get through: a login screen or
a bot check, both of which answer 200; and 403, 405, 406 or 501, which can be a block
on the HEAD probe rather than on the page, so those are left to Chrome and the CLI
prints a warning naming the status.

**A URL carrying credentials is refused.** `https://user:pass@host/` fails with a
message rather than being fetched; this skill prints pages that are open to it. For a
page behind a login, save it from your own browser and render the saved file.

Two things make the probe see a slightly different internet from Chrome's. It uses
Python's CA bundle and `*_proxy` variables rather than Chrome's root store and system
proxy, so on a Python install without its certificates it can refuse an https URL
Chrome would render. And it resolves an internationalized host with Python's IDNA
codec, which differs from Chrome's for a few characters — `faß.de` becomes `fass.de`
here and stays `xn--fa-hia.de` in Chrome — so for those hosts the probe checks a
different name than Chrome fetches.

`--timeout` bounds the HEAD probe and then the wait for the PDF separately, each at
90 seconds by default, so a URL that stalls at both steps takes about twice that.
Shutting the browser down normally takes a fraction of a second, but a browser that
ignores being asked twice can add 20 seconds. The CLI does not wait for Chrome to exit:
Chrome writes the finished PDF and then, on macOS, keeps running, so the CLI watches
for a PDF that is whole and has stopped growing and then ends the browser. When Chrome
says it could not load the page the CLI stops there and repeats what Chrome said,
rather than waiting out the timeout — but Chrome stays silent on some runs, so the
timeout is still the backstop. Chrome prints when the page finishes loading, so
whatever a script adds more than about half a second later is missing from the PDF.

Chrome runs with its own sandbox and a throwaway profile, never your browser profile;
it is still a full browser, so isolate untrusted URLs externally. A rendered page
reflects one fetch at one moment — record the URL and the time with the output.

## Install and run

Use Python 3.10+ and the native Pango/font dependencies from the
[WeasyPrint installation guide](https://doc.courtbouillon.org/weasyprint/v69.0/first_steps.html#installation).
On Debian/Ubuntu, a typical prerequisite setup is:

```sh
sudo apt-get install python3-venv libpango-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core
```

Web pages additionally need Google Chrome or Chromium. The CLI looks for
`google-chrome`, `google-chrome-stable`, `chromium` or `chromium-browser` on `PATH`,
then the standard macOS application paths, or takes `--browser PATH`. Nothing else
in the skill needs a browser.

Copy this folder, named `everything-to-pdf`, into your agent's skills directory (for
Codex, `${CODEX_HOME:-$HOME/.codex}/skills/everything-to-pdf`). No installer runs
automatically. Keep the virtual environment outside the package:

```sh
python3 -m venv ~/.local/share/everything-to-pdf/venv
~/.local/share/everything-to-pdf/venv/bin/pip install -r /path/to/everything-to-pdf/requirements.txt
mkdir -p /path/to/output
~/.local/share/everything-to-pdf/venv/bin/python /path/to/everything-to-pdf/scripts/render.py \
  /path/to/source/report.html /path/to/output/report.pdf
```

`requirements.txt` pins WeasyPrint and Markdown; Markdown is pure Python and needs
no system libraries. Run the synthetic example using `examples/monthly-finops.html`
as input. The CLI prints the page count and complete JSON-escaped output path,
compact warnings to stderr, and exits 0 on success or 1 on render/validation failure
(2 for CLI syntax). The output directory must already
exist. Output is replaced atomically from a temporary file in the same directory;
failed renders leave any prior PDF intact. Temporary files are removed on ordinary
failure; a killed process may leave a `.everything-to-pdf-*.pdf` file that can be
deleted.

## Theme and layout

The theme applies to every input except a web page. Theme selection is authoring-time
guidance in [SKILL.md](SKILL.md): explicit user
theme first, then the relevant project's design system, then the bundled Geist
print fallback. Discovery is limited to project instructions, the design
files they name, the project's own `docs/design-system.md`, and the available skill
catalog; it does not crawl the project. Optional design skills such as `internal-tool-design`
(`internal-tool:design` / internal-tool plugin `design`) and `private-org-design` apply only to their
matching project/brand; none is required. Use relevant print/light guidance and
report missing explicitly requested sources instead of silently falling back.

Copy [assets/print-theme.md](assets/print-theme.md) into the user's project,
adapt the design tokens once into its complete JSON schema, record the source and
print choices in its prose, then reuse it with `--theme /path/to/print-theme.md`.
An explicit compatible theme can be used directly. The default file cites official
Vercel Geist light sRGB colors and separates them from this skill's print adaptations;
it is not a full Geist component or typography implementation. The CLI performs no
design-system discovery, network lookup, or font download. Without `--theme` it
always uses the bundled fallback. Markdown prose in the theme file is author
guidance, not rendered content; no Markdown/YAML parser is used to read it.
Unknown, duplicate, unsafe or malformed tokens fail before output replacement.
The same inputs and environment follow the same rules; byte-for-byte reproducibility
across platforms or renderer/font upgrades is not promised, and a web page is not
reproducible at all. This pins the renderer, not its transitive dependencies, the
installed browser, or system fonts.

The JSON `typography.family` accepts only `sans-serif`, `serif`, or `monospace`.
For actual brand fonts, retain or add source CSS or a linked local stylesheet with
`@font-face` and the appropriate `font-family`. Stage existing font assets you are
permitted to use under the input's resolved parent directory, alongside any
required local stylesheets; remote font URLs are blocked. Disclose missing fonts
and any fallback used instead of claiming brand typography fidelity. Text, code and
image inputs carry a small stylesheet of their own — monospace for text, a one-page
cap for an image — which the theme does not override.

Source author CSS has normal precedence over the skill's user-origin defaults.
Use an inline style or a linked local stylesheet for custom CSS; there is no separate
CSS flag. Headings provide bookmarks, `thead` repeats across table pages, and rows
prefer to stay together. Long rows, wide tables, fixed positioning and fixed-height
containers can still overflow: inspect the resulting pages. No content is rewritten
or deliberately hidden by the converter, but source CSS can hide content and only
static print-visible content appears. For local inputs, scripts, videos and
interactive widgets are not supported; a web page runs them. Font availability
affects rendering and glyph coverage.

## Resources and trust boundary

For local inputs, files resolve relative to the real input file (and linked stylesheets
relative to themselves).
For a symlinked input, assets belong beside its target, not beside the symlink.
Only regular files inside the resolved parent directory and embedded `data:`
resources are allowed; network/remote-file resources and escaping symlinks fail.
Move shared assets into that source tree instead of broadening permissions. Fetch
failures and renderer errors fail the conversion, including missing images/CSS;
unsupported CSS warnings are reported without aborting. This covers resources the
renderer actually requests, not an audit of unused CSS URLs or ordinary hyperlinks.
Diagnostics are capped at six messages plus a count and bound resource identifiers and redact embedded data URIs.
None of this applies to a web page: Chrome enforces its own boundary, not this one.

This is **not a hostile-input sandbox**. Native libraries, system font discovery,
resource exhaustion, and concurrently changed input files remain outside these
checks. For untrusted documents and for any untrusted URL, use external
filesystem/network isolation and CPU/memory/time limits. Do not render mutually
untrusted tenants in the same process. The CLI stores no runtime state inside the
installed package.

## Update, rollback, remove

Save the current skill folder and external venv as a matched backup before updating.
Replace the skill folder with a reviewed release, create a new external venv from
its requirements, and run the example and tests before switching your invocation.
Rollback by restoring that folder and using its matching old venv. Remove the skill
folder to uninstall discovery, then remove its external venv if no longer needed;
project sources, themes and PDFs remain yours and are not deleted by the skill.

## Tests

Tests use stdlib unittest plus test-only PyMuPDF to inspect actual PDFs:

```sh
/path/to/venv/bin/pip install -r requirements-test.txt
PYTHONDONTWRITEBYTECODE=1 /path/to/venv/bin/python -m unittest discover -s tests -v
```

The suite checks content/pagination/bookmarks, theme geometry and validation,
Markdown/text/image inputs, local/nested/embedded resources, denied or broken assets,
warnings and output recovery. The web-page test serves a JavaScript page on localhost
and is skipped when no browser is installed. No agent API or outbound network
connection is required to render or test.
