---
name: everything-to-pdf
description: Use when converting Markdown, plain text or code, an image, local static HTML, or a web page into a PDF. Local inputs get a themed, paginated WeasyPrint render; a web page is printed by headless Chrome and loses the theme. Excludes office documents and editing existing PDFs.
metadata:
  version: "0.2.0"
---

Convert the user's input without rewriting or summarizing its content. Run the
deterministic converter once; there is no LLM rendering loop. The input decides
which of two engines runs, and that choice decides what the user gets:

| Input | Recognized by | Engine | Theme |
| --- | --- | --- | --- |
| Local static HTML | `.html`, `.htm` | WeasyPrint | applies |
| Markdown | `.md`, `.markdown` | WeasyPrint | applies |
| Plain text, code | `.txt`, `.text`, `.log`, `--as text` | WeasyPrint | applies |
| Image | `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp` | WeasyPrint | applies |
| Web page | an `http`/`https` URL | headless Chrome | does not apply |

Markdown, text and images become local HTML on the WeasyPrint path, so they keep
everything local HTML has: no JavaScript, no network, assets confined to the input's
own directory, and the theme governing the output. Markdown supports tables and
fenced code blocks, and its headings still supply bookmarks. Text and code are
escaped rather than interpreted, and set in monospace. A tall image is scaled to one
page. Pass `--as` when the extension does not name the kind, as with a code file.
For new documents, use semantic headings, paragraphs, tables with `thead`, and
local images. Headings supply PDF bookmarks; print CSS helps pagination.

**A web page is the exception, and you must say so.** Chrome loads the URL, runs its
JavaScript and prints it, so that PDF has no theme, no page-number footer, no offline
guarantee, and no asset confinement: Chrome fetches whatever the page asks for. The
paper is whatever the page's own print CSS says, or Chrome's Letter default when it
says nothing, so you cannot promise a paper size either. Headings still become
bookmarks. `--theme` with a URL fails instead of being silently ignored. Report those
losses rather than calling the result themed, and name the live URL and the time you
fetched it, since the page can change under you. For an untrusted URL, use external
process/filesystem/network isolation; this is not a hostile-input sandbox.

**Read page 1 of a web-page PDF before you deliver it.** Chrome prints whatever it is
shown and still exits 0, so the CLI probes the URL first and fails on a name that
does not resolve, a refused connection, or a page that answers an error. That probe
cannot catch everything: a redirect to a login screen answers 200, and a bot check or
a block aimed at the probe itself answers a status only the browser can settle, so
either can arrive as a successful render of the wrong page. When the probe got such a
status the CLI warns and names it; check the text regardless.

For local inputs, choose the theme before rendering: **explicit user theme > relevant
project design system > bundled Geist print fallback**. At authoring time, check project
instructions and their referenced design/token files. Also inspect obvious project-local
sources even if unreferenced: root `DESIGN.md`, `design-system.md`, token files, and files
directly inside a known styles folder. Keep this a bounded check, not a recursive
search. Then check the available skill catalog for a matching brand. Read only the
relevant skill and its linked color, type and print references; do not crawl the
filesystem or load unrelated skills. Optional matches
include `internal-tool-design` (also `internal-tool:design` / internal-tool plugin `design`) and
`private-org-design`; check the actual name and project/brand before using either.
Prefer the system's print/light guidance over a dark web default. If an explicitly
requested theme/system is unavailable or ambiguous, report that and ask for the
missing source or choice; do not silently substitute Geist. If no relevant project
system is found, use the fallback and say so.

Adapt a selected design system once into a theme file in the user's project: copy
[assets/design-system.md](assets/design-system.md), map the project's tokens into
its complete JSON schema, retain suitable print defaults for unspecified values,
and record the source and print adaptations in the prose. Pass that file with
`--theme`; reuse it on subsequent renders. A requested theme already in this schema
can be passed directly. Discovery and adaptation are agent authoring work: the CLI
only reads the supplied theme or bundled fallback, offline, without skill imports,
font downloads or additional dependencies. Preserve existing source CSS.

Use an existing external Python environment with [requirements.txt](requirements.txt)
installed. First-run system dependencies and venv setup are in [README.md](README.md).
Use the README's default venv below, or substitute an existing compatible environment.
Web pages additionally need Chrome or Chromium on `PATH`, or `--browser PATH`.
From the skill directory:

```sh
~/.local/share/everything-to-pdf/venv/bin/python scripts/render.py NOTES.md OUT.pdf
~/.local/share/everything-to-pdf/venv/bin/python scripts/render.py IN.html OUT.pdf --theme /path/to/design-system.md
~/.local/share/everything-to-pdf/venv/bin/python scripts/render.py helper.py OUT.pdf --as text
~/.local/share/everything-to-pdf/venv/bin/python scripts/render.py https://example.com/page OUT.pdf
```

The output directory must exist. Store inputs, output, themes, venvs and inspection
images outside the installed package. Read [assets/design-system.md](assets/design-system.md)
when designing or changing the theme: prose guides authoring, its one strict JSON
block controls the print defaults. Author HTML/CSS retains normal cascade precedence.
Keep custom document CSS in the source or a linked local stylesheet.

For a local input, resources must be embedded data URIs or files inside the input's
resolved parent directory, including nested folders. For a symlinked input, assets
belong beside the real file, not beside the symlink. Copy required assets there;
network fetches, parent traversal and symlinks escaping that root fail. Normal
external hyperlinks remain links and are not fetched. On failure, fix the reported
resource/theme/input/output problem and rerun; an existing output survives.
Warnings may indicate unsupported CSS.

Verify the delivered PDF's text and page count and inspect rendered pages for clipping
when layout matters. Report warnings and any inspection gaps. Static print layout is
not arbitrary browser-perfect CSS; oversized tables/blocks and missing font glyphs
need author attention. This is not a hostile-input sandbox or a PDF/UA guarantee.
For untrusted workloads use external process/filesystem/network isolation and limits.

[examples/monthly-finops.html](examples/monthly-finops.html) is a synthetic authoring
example, not a fixed-page-count template.
