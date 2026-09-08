---
name: html-to-pdf
description: Use when converting local static HTML into a themed, paginated PDF with WeasyPrint. Supports reports and documents; excludes JavaScript-driven pages, browser screenshot capture, and editing existing PDFs.
---

Convert the user's HTML without rewriting or summarizing its content. Run the
deterministic converter once; there is no LLM rendering loop or JavaScript engine.
For new documents, use semantic headings, paragraphs, tables with `thead`, and
local images. Headings supply PDF bookmarks; print CSS helps pagination.

Choose the theme before rendering: **explicit user theme > relevant project design
system > bundled Geist print fallback**. At authoring time, check project instructions
and their referenced design/token files. Also inspect obvious project-local sources
even if unreferenced: root `DESIGN.md`, `design-system.md`, token files, and files
directly inside a known styles folder. Keep this a bounded check, not a recursive
search. Then check the available skill catalog for a matching brand. Read only the
relevant skill and its linked color, type and print references; do not crawl the
filesystem or load unrelated skills. Optional matches
include `lessly-design` (also `lessly:design` / Lessly plugin `design`) and
`apliteni-design`; check the actual name and project/brand before using either.
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
Use the README’s default venv below, or substitute an existing compatible environment.
From the skill directory:

```sh
~/.local/share/html-to-pdf/venv/bin/python scripts/render.py INPUT.html OUTPUT.pdf
~/.local/share/html-to-pdf/venv/bin/python scripts/render.py INPUT.html OUTPUT.pdf --theme /path/to/design-system.md
```

The output directory must exist. Store inputs, output, themes, venvs and inspection
images outside the installed package. Read [assets/design-system.md](assets/design-system.md)
when designing or changing the theme: prose guides authoring, its one strict JSON
block controls the print defaults. Author HTML/CSS retains normal cascade precedence.
Keep custom document CSS in the source or a linked local stylesheet.

Resources must be embedded data URIs or files inside the input's resolved parent
directory, including nested folders. For a symlinked input, assets belong beside
the real HTML file, not beside the symlink. Copy required assets there; network fetches,
parent traversal and symlinks escaping that root fail. Normal external hyperlinks
remain links and are not fetched. On failure, fix the reported resource/theme/input/output
problem and rerun; an existing output survives. Warnings may indicate unsupported CSS.

Verify the delivered PDF's text and page count and inspect rendered pages for clipping
when layout matters. Report warnings and any inspection gaps. Static print layout is
not arbitrary browser-perfect CSS; oversized tables/blocks and missing font glyphs
need author attention. This is not a hostile-input sandbox or a PDF/UA guarantee.
For untrusted workloads use external process/filesystem/network isolation and limits.

[examples/monthly-finops.html](examples/monthly-finops.html) is a synthetic authoring
example, not a fixed-page-count template.
