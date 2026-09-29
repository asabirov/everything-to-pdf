# html-to-pdf

A small agent skill and deterministic CLI for local static HTML → PDF, using
WeasyPrint 69.0 and a minimalist, themeable print stylesheet. It keeps the supplied
HTML intact; it does not summarize content, run JavaScript, capture browser pages,
edit existing PDFs, or operate an LLM rendering loop. It does not promise arbitrary
browser CSS fidelity or PDF/UA conformance.

The skill version lives in `metadata.version` in `SKILL.md`.

## Install and run

Use Python 3.10+ and the native Pango/font dependencies from the
[WeasyPrint installation guide](https://doc.courtbouillon.org/weasyprint/v69.0/first_steps.html#installation).
On Debian/Ubuntu, a typical prerequisite setup is:

```sh
sudo apt-get install python3-venv libpango-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core
```

Copy this folder, named `html-to-pdf`, into your agent's skills directory (for Codex,
`${CODEX_HOME:-$HOME/.codex}/skills/html-to-pdf`). No installer runs automatically.
Keep the virtual environment outside the package:

```sh
python3 -m venv ~/.local/share/html-to-pdf/venv
~/.local/share/html-to-pdf/venv/bin/pip install -r /path/to/html-to-pdf/requirements.txt
mkdir -p /path/to/output
~/.local/share/html-to-pdf/venv/bin/python /path/to/html-to-pdf/scripts/render.py \
  /path/to/source/report.html /path/to/output/report.pdf
```

Run the synthetic example using `examples/monthly-finops.html` as input. The CLI
prints the page count and complete JSON-escaped output path, compact warnings to
stderr, and exits 0 on success or 1 on render/validation failure (2 for CLI syntax).
The output directory must already
exist. Output is replaced atomically from a temporary file in the same directory;
failed renders leave any prior PDF intact. Temporary files are removed on ordinary
failure; a killed process may leave a `.html-to-pdf-*.pdf` file that can be deleted.

## Theme and layout

Theme selection is authoring-time guidance in [SKILL.md](SKILL.md): explicit user
theme first, then the relevant project's design system, then the bundled Geist
print fallback. Discovery is bounded to project instructions/referenced files,
obvious local sources (root design/token files and a known styles folder), and the
available skill catalog; it does not recursively crawl the project. Optional design skills such as `internal-tool-design`
(`internal-tool:design` / internal-tool plugin `design`) and `private-org-design` apply only to their
matching project/brand; none is required. Use relevant print/light guidance and
report missing explicitly requested sources instead of silently falling back.

Copy [assets/design-system.md](assets/design-system.md) into the user's project,
adapt the design tokens once into its complete JSON schema, record the source and
print choices in its prose, then reuse it with `--theme /path/to/design-system.md`.
An explicit compatible theme can be used directly. The default file cites official
Vercel Geist light sRGB colors and separates them from this skill's print adaptations;
it is not a full Geist component or typography implementation. The CLI performs no
design-system discovery, network lookup, or font download. Without `--theme` it
always uses the bundled fallback. Markdown prose is author guidance, not rendered
content; no Markdown/YAML parser or new runtime dependency is needed.
Unknown, duplicate, unsafe or malformed tokens fail before output replacement.
The same inputs and environment follow the same rules; byte-for-byte reproducibility
across platforms or renderer/font upgrades is not promised. This pins the renderer,
not its transitive dependencies or system fonts.

The JSON `typography.family` accepts only `sans-serif`, `serif`, or `monospace`.
For actual brand fonts, retain or add source CSS or a linked local stylesheet with
`@font-face` and the appropriate `font-family`. Stage existing font assets you are
permitted to use under the input HTML's resolved parent directory, alongside any
required local stylesheets; remote font URLs are blocked. Disclose missing fonts
and any fallback used instead of claiming brand typography fidelity.

Source author CSS has normal precedence over the skill's user-origin defaults.
Use an inline style or a linked local stylesheet for custom CSS; there is no separate
CSS flag. Headings provide bookmarks, `thead` repeats across table pages, and rows
prefer to stay together. Long rows, wide tables, fixed positioning and fixed-height
containers can still overflow: inspect the resulting pages. No content is rewritten
or deliberately hidden by the converter, but source CSS can hide content and only
static print-visible content appears. Scripts, videos and interactive widgets are
not supported. Font availability affects rendering and glyph coverage.

## Resources and trust boundary

Files resolve relative to the real HTML file (and linked stylesheets relative to themselves).
For a symlinked input, assets belong beside its target, not beside the symlink.
Only regular files inside the resolved HTML parent directory and embedded `data:`
resources are allowed; network/remote-file resources and escaping symlinks fail.
Move shared assets into that source tree instead of broadening permissions. Fetch
failures and renderer errors fail the conversion, including missing images/CSS;
unsupported CSS warnings are reported without aborting. This covers resources the
renderer actually requests, not an audit of unused CSS URLs or ordinary hyperlinks.
Diagnostics are capped at six messages plus a count and bound resource identifiers and redact embedded data URIs.

This is **not a hostile-input sandbox**. Native libraries, system font discovery,
resource exhaustion, and concurrently changed input files remain outside these
checks. For untrusted documents use external filesystem/network isolation and
CPU/memory/time limits. Do not render mutually untrusted tenants in the same process.
The CLI stores no runtime state inside the installed package.

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
local/nested/embedded resources, denied or broken assets, warnings and output recovery.
No agent API or network connection is required to render or test.
