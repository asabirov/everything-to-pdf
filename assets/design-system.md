# Geist print fallback

A neutral fallback when no user theme or relevant project design system applies.
Use semantic headings, clear units and sparse tables; keep meaning in text as well
as color. Only the JSON controls the renderer; prose guides authoring.

## Source and print choices

Colors come from the official [Vercel Geist colors](https://vercel.com/geist/colors)
page's [stylesheet](https://vercel.com/vc-ap-b3331f/_next/static/immutable/chunks/328y7_b581oob.css),
checked 2026-09-08. The light selector `:root,:host,.dark .invert-theme,.dark-theme
.invert-theme` defines the following `--ds-gray-*-value` sRGB HSL triplets, consumed
by `hsla(var(...), 1)`. Hex values below round channels to the nearest 8-bit value;
these are the sRGB definitions, not the site's wide-gamut overrides.

| Theme role | Geist token | Official HSL | Hex |
| --- | --- | --- | --- |
| text | gray-1000 | 0, 0%, 9% | #171717 |
| muted | gray-900 | 0, 0%, 30% | #4D4D4D |
| accent | gray-1000 | 0, 0%, 9% | #171717 |
| surface | gray-100 | 0, 0%, 95% | #F2F2F2 |
| border | gray-400 | 0, 0%, 92% | #EBEBEB |

Print adaptations owned by this skill: monochrome headings/links use gray-1000 as
an accent, paper stays white, and surfaces/rules use the light palette. Generic
installed sans-serif (not a bundled Geist font), 10 pt type, 1.45 line height,
A4 paper, 18 mm margins and the spacing below are local print choices, not official
Geist typography or layout tokens. No fonts or stylesheets are fetched at render time.

```json
{
  "colors": {
    "text": "#171717",
    "muted": "#4D4D4D",
    "accent": "#171717",
    "surface": "#F2F2F2",
    "border": "#EBEBEB"
  },
  "typography": {"family": "sans-serif", "size_pt": 10, "line_height": 1.45},
  "spacing": {"block_mm": 3, "cell_mm": 2.5},
  "page": {"size": "A4", "margin_mm": 18}
}
```

Copy this file outside the installed skill, edit it, and pass `--theme PATH`.
Exactly one column-zero `json` fence is required. All keys are required; unknown
or duplicate keys and malformed JSON fail. Colors are six-digit hex strings.
Family is `sans-serif`, `serif`, or `monospace`; installed fonts determine glyphs.
Size is 8–18 pt, line height 1.1–2, block spacing 1–12 mm, cell padding 1–6 mm.
Page size is `A4` or `Letter`; margin is a uniform 10–35 mm. Numbers are JSON
numbers, without units. These constrained values cannot inject CSS or URLs.
Source author CSS can override these user-origin defaults through the CSS cascade.

Validated colors are exported on `:root` as `--color-text`, `--color-muted`,
`--color-accent`, `--color-surface`, and `--color-border`. Use `var(--color-surface)`
for custom component backgrounds and `var(--color-border)` for rules, as the
bundled example does. Author CSS can override these properties or component styles.
