# Changelog

## 0.1.0 — 2026-09-29

Html-to-pdf helps agents convert local static HTML into a themed, paginated PDF for reports and documents.

### Added

- **Local HTML to PDF.** The skill converts your local static HTML into a paginated PDF with WeasyPrint, without an LLM rendering loop or JavaScript engine. Your content and structure stay intact. This gives you a deterministic, repeatable render for reports and documents.

- **Theme selection order.** The skill picks the theme in this order: the one you name, then your project's design system, then the bundled Geist print theme. It reports a missing theme instead of silently substituting one. This keeps documents on-brand without guessing your intent.

- **Reusable project theme.** The skill turns your project's design system into one theme file in your project and reuses it on later renders. This keeps documents on one print theme without redoing the mapping.

- **Bounded resource resolution.** Your images and stylesheets must sit inside the input HTML's resolved parent directory as local files or embedded data URIs; the skill blocks network fetches and symlink escapes. This keeps conversions offline and prevents unexpected external access.

- **Render verification.** You get a page count, compact warnings, and bookmarks generated from headings, and the skill inspects rendered pages for clipping when layout matters. This helps you catch pagination or rendering problems before delivery.
