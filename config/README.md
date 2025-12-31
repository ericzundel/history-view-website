# Configuration: Categories and Domain Blocklist

The category system classifies domains and visit data for drill-down views:

- Primary categories: high-level buckets (e.g., `#news`, `#social`, `#softwaredev`).
- Secondary categories: more specific tags mapped under the primaries (e.g., `#python`, `#spreadsheets`, `#worldnews`).

Domain-to-category mapping:

- Use `config/domain-category-map.yaml` to pin domains to one primary tag plus zero or more secondary tags, using the same tag names defined in `categories.yaml`.
- Example entry:

```yaml
domains:
  - domain: example.com
    primary: '#news'
    secondary:
      - '#technews'
      - '#worldnews'
```

Workflow:

1. Edit `categories.yaml` to add or adjust categories. Keep primary categories grouped at the top with `type: primary`; omit `type` for secondary tags.
2. Keep tags as lowercase hashtags without spaces or underscores; concatenate words (e.g., `#softwaredev`, `#technews`). Use `label` for display text.
3. Downstream scripts read this file to map domains to categories and to populate overlay data sets.

Domain blocklist:

- Create `domain-blocklist.yml` to list domains the loaders/favicons should skip.
- File is gitignored by default (`config/domain-blocklist.yml`).
- Use a flat YAML list of domains, e.g.:

```yaml
- example.com
- internal.lan
- 10.0.0.5
```

Future work (per spec):

- Seed ~40 primary categories and ~200 secondary categories.
- Document mapping rules and any manual overrides used during classification.
