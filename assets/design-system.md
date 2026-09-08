# Sand

Quiet editorial reports: generous white space, warm gray surfaces, dark ink and
one restrained olive accent. Use semantic headings, short introductions, clear
units and sparse tables. Keep important meaning in text, not color alone.
The prose guides document authors; only the JSON below affects the renderer.

```json
{
  "colors": {
    "text": "#292B28",
    "muted": "#66675F",
    "accent": "#586348",
    "surface": "#F3F1EA",
    "border": "#DCDCD2"
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
