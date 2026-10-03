# everything-to-pdf

Convert Markdown, text or code, images, local HTML or a web page to PDF.

It is an agent skill for Claude Code and Codex. You ask your agent for a PDF; it
picks a print theme and runs one Python script, which lays out your content
as it is, without rewriting or summarizing it.

![Page 1 of the bundled example, rendered with the default theme](docs/example-page-1.png)

*Page 1 of [examples/monthly-finops.html](examples/monthly-finops.html) as the skill
renders it. The company and figures are made up.*

## Install

```sh
DO_NOT_TRACK=1 npx skills add https://github.com/asabirov/everything-to-pdf/tree/v0.2.0 --skill everything-to-pdf --agent claude-code codex --global
```

The [skills CLI](https://github.com/vercel-labs/skills) needs Node.js, npm and Git.
`DO_NOT_TRACK=1` turns off its telemetry. To update or roll back, run the same
command with the release you want from
[Releases](https://github.com/asabirov/everything-to-pdf/releases).

Then give the renderer its Python environment, outside the skill folder:

```sh
python3 -m venv ~/.local/share/everything-to-pdf/venv
~/.local/share/everything-to-pdf/venv/bin/pip install -r ~/.agents/skills/everything-to-pdf/requirements.txt
```

## Dependencies

| Dependency | What it is for |
| --- | --- |
| Python 3.10 or later | Runs the renderer. |
| [WeasyPrint](https://doc.courtbouillon.org/weasyprint/v69.0/first_steps.html#installation) 69.0 and its Pango and font libraries | Lays out every local input as print pages. pip installs WeasyPrint; the libraries come from your system (below). |
| Markdown 3.11 (Python package) | Turns Markdown into HTML before layout. pip installs it. |
| [Google Chrome](https://www.google.com/chrome/) or Chromium | Prints web pages. Only needed for URLs. |

System libraries for WeasyPrint:

```sh
brew install pango                     # macOS
sudo apt-get install python3-venv libpango-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core   # Debian, Ubuntu
```

## Ask your agent

> Make a PDF of NOTES.md using our design system.

> Save https://example.com/pricing as a PDF.

The agent tells you which theme it used, the page count, and any warnings.

## What to know before you use it

- **Local files and web pages print differently.** Markdown, text, code, images
  and HTML files get the print theme and page numbers, and are rendered offline.
  A web page is printed by Chrome as the site's own print layout: no theme, no
  page numbers, and Chrome loads whatever the page asks for.
- **Check page 1 of a web-page PDF.** A login screen or a bot check can come
  back as a successful PDF of the wrong page. For a page behind a login, save it
  from your browser and ask for a PDF of the saved file.
- **Your brand's look.** Name a theme or design system in your request, or keep
  one at `docs/design-system.md` in your project. Otherwise you get the plain
  bundled theme. [SKILL.md](SKILL.md) has the full order.
- **Images and stylesheets must sit beside the input.** A local file can only
  use files in its own folder or below it. Move shared assets in rather than
  linking out.
- **Not a sandbox.** For documents or URLs you do not trust, run it inside your
  own filesystem and network isolation.

## Tests

The tests render real PDFs and read them back with PyMuPDF. From a clone:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-test.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

The web-page test is skipped when no Chrome or Chromium is installed. No CI runs
these tests, so run them before opening a pull request.

## License

[MIT](LICENSE)
