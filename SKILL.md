---
name: html-to-pdf
description: Use when converting local static HTML into a themed, paginated PDF with WeasyPrint. Supports reports and documents; excludes JavaScript-driven pages, browser screenshot capture, and editing existing PDFs.
---

Convert the user's HTML without rewriting or summarizing its content. Run the
deterministic converter once; there is no LLM rendering loop or JavaScript engine.
For new documents, use semantic headings, paragraphs, tables with `thead`, and
local images. Headings supply PDF bookmarks; print CSS helps pagination.

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
