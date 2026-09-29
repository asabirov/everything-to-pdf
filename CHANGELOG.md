# Changelog

## 0.1.0 — Unreleased

Html-to-pdf helps agents convert local static HTML into a themed, paginated PDF for reports and documents.

### Added

- **Local HTML to PDF.** You convert local static HTML into a paginated PDF with WeasyPrint, without an LLM rendering loop or JavaScript engine. Your content and structure stay intact. This gives you a deterministic, repeatable render for reports and documents.

- **Theme selection order.** You get an explicit theme, a relevant project design system, or the bundled Geist print fallback, checked in that order. The skill reports a missing requested theme instead of silently substituting one. This keeps rendered documents on-brand without guessing your intent.

- **Reusable design-system theme file.** You copy `assets/design-system.md` and map your project's tokens into its JSON schema once, then reuse the file with `--theme` on later renders. This keeps a consistent print theme across documents without redoing the mapping each time.

- **Bounded resource resolution.** Your images and stylesheets must sit inside the input HTML's resolved parent directory as local files or embedded data URIs; the skill blocks network fetches and symlink escapes. This keeps conversions offline and prevents unexpected external access.

- **Render verification.** You get a page count, compact warnings, and bookmarks generated from headings, and are asked to inspect rendered pages for clipping when layout matters. This helps you catch pagination or rendering problems before delivery.
