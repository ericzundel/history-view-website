# Categories Guide

Purpose and maintenance notes for `config/categories.yaml`.

## Structure

- Primary categories sit at the top with `type: primary`. They represent broad buckets used in the UI treemap overlays and downstream aggregation.
- Secondary categories follow and omit `type`. They are finer-grained tags mapped under the primaries during curation.
- Tags are lowercase hashtags without spaces (or the `#` character); concatenate words instead of using underscores. `label` holds the display text.
- primary categories and secondary categories are grouped under comment headers for quick scanning.

## Editing workflow

- Update `config/categories.yaml` directly; keep primaries grouped first. Additions should follow the existing tag and label style.
- When adding a new primary, add at least a handful of secondary tags beneath it so drill-down data stays interesting.
- If you need to retire a tag, prefer soft-deprecating (comment it out) until data pipelines and manual mappings are cleaned up.
- Run domain classification tools with the updated taxonomy to catch missing labels or overlap. When in doubt, search `data/domains.txt` to see real-world domains that may need coverage.

## Mapping guidelines

- Prefer one primary tag per domain; apply multiple secondary tags as needed for nuance.
- Use product intent over company name. Example: `mail.google.com` → `emailcalendar` + `webmail`; `maps.google.com` → `transportationmobility` + `navigation`.
- For gray areas, bias toward the user-facing purpose (e.g., a dev blog under a cloud provider should go to `softwaredev` + `webdev` rather than `commerceshopping`).
- Keep security/privacy tools explicitly tagged with `securityprivacy` to support opt-in filtering.

## 'other' tag

- If a domain name violates a privacy issue (see @make_category_map.prompt.md ) tag it with `securityprivacy`
- If a domain name can't be easily classified, mark it with `other`. This should be rare.
- If you are running into many other tags (>10%) ask for clarification and update this section of this doc with more guidelines.
