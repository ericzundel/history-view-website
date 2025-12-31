# Category Taxonomy

The category system classifies domains and visit data for drill-down views:

- Primary categories: high-level buckets (e.g., `#news`, `#social`, `#software_dev`).
- Secondary categories: more specific tags mapped under the primaries (e.g., `#python`, `#spreadsheets`, `#worldnews`).

Workflow:

1. Edit `categories.yaml` to add or adjust categories. Keep primary categories grouped at the top with `type: primary`; omit `type` for secondary tags.
2. Keep tags as lowercase hashtags without spaces; use `label` for display text.
3. Downstream scripts read this file to map domains to categories and to populate overlay data sets.

Future work (per spec):

- Seed ~40 primary categories and ~200 secondary categories.
- Document mapping rules and any manual overrides used during classification.
