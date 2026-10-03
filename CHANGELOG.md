# Changelog

## 0.3.0 — Unreleased

### Changed

- **The bundled print theme moved to `assets/print-theme.md`.** It was previously `assets/design-system.md`, which conflicted with the design system a project keeps at `docs/design-system.md`. Pass the renamed file, or your copy of it, with `--theme`.

- **The skill reads a project's design system from `docs/design-system.md`.** It no longer looks for a design file at the repository root.

- **Brand design skills are no longer named.** The skill still checks the skill catalog for a design skill matching the project's brand, but no longer lists specific private ones.

### Added

- **MIT licence.**

## 0.2.0 — 2026-10-01

The skill is now `everything-to-pdf`: it converts Markdown, plain text or code, an image, local static HTML, or a web page.

### Added

- **Markdown input.** Point the skill at a `.md` file and it renders on the same themed path as HTML, with tables, fenced code blocks, bookmarks from headings, and images that sit beside the Markdown. This replaces hand-writing HTML first, and costs one pure-Python dependency.

- **Plain text and code input.** A `.txt`, `.text` or `.log` file, or any file with `--as text`, is escaped rather than interpreted, set in monospace, and wrapped so long lines stay on the page. This turns logs and source files into readable documents without markup.

- **Image input.** A `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg` or `.webp` file becomes a one-page PDF, scaled to fit the page even when the image is very tall.

- **Web pages, through a browser.** Give the skill an `http`/`https` URL and headless Chrome loads the page, runs its JavaScript and prints it, keeping bookmarks from headings. You lose the theme, the page-number footer, the theme's paper size and margins, the offline guarantee, and the confinement of resources to one directory; the skill says so on every run, and `--theme` with a URL fails rather than being ignored. Chrome prints whatever it is shown and reports success either way, so the URL is checked first: an unreachable page, or one that answers an error, fails without touching your previous output. A login screen or a bot check can still arrive as a successful render of the wrong page, so read page 1 — the skill warns you when the check came back inconclusive. A URL carrying credentials is refused rather than fetched: save a page that needs a login and render the saved file.

- **`--as` for unnamed kinds.** `--as html|markdown|text|image|webpage` names the input kind when the extension does not. An unrecognized extension fails and asks for `--as` instead of guessing.

### Changed

- **Renamed from `html-to-pdf` to `everything-to-pdf`,** including the skill name, the recommended venv path (`~/.local/share/everything-to-pdf/venv`) and the temporary file prefix (`.everything-to-pdf-*.pdf`). GitHub redirects keep old clone URLs working. Installed copies of the old skill folder keep working but will not be updated; reinstall under the new name.

## 0.1.0 — 2026-09-29

Html-to-pdf helps agents convert local static HTML into a themed, paginated PDF for reports and documents.

### Added

- **Local HTML to PDF.** The skill converts your local static HTML into a paginated PDF with WeasyPrint, without an LLM rendering loop or JavaScript engine. Your content and structure stay intact. This gives you a deterministic, repeatable render for reports and documents.

- **Theme selection order.** The skill picks the theme in this order: the one you name, then your project's design system, then the bundled Geist print theme. It reports a missing theme instead of silently substituting one. This keeps documents on-brand without guessing your intent.

- **Reusable project theme.** The skill turns your project's design system into one theme file in your project and reuses it on later renders. This keeps documents on one print theme without redoing the mapping.

- **Bounded resource resolution.** Your images and stylesheets must sit inside the input HTML's resolved parent directory as local files or embedded data URIs; the skill blocks network fetches and symlink escapes. This keeps conversions offline and prevents unexpected external access.

- **Render verification.** You get a page count, compact warnings, and bookmarks generated from headings, and the skill inspects rendered pages for clipping when layout matters. This helps you catch pagination or rendering problems before delivery.
