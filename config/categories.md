# Categories Guide

Purpose and maintenance notes for `config/categories.yaml`.

## Structure

- Primary categories sit at the top with `type: primary`. They represent broad buckets used in the UI treemap overlays and downstream aggregation.
- Secondary categories follow and omit `type`. They are finer-grained tags mapped under the primaries during curation.
- Tags are lowercase hashtags without spaces; use underscores for readability. `label` holds the display text.
- Current seed: 40 primary categories and 202 secondary categories (grouped under comment headers for quick scanning).

## Editing workflow

- Update `config/categories.yaml` directly; keep primaries grouped first. Additions should follow the existing tag and label style.
- When adding a new primary, add at least a handful of secondary tags beneath it so drill-down data stays interesting.
- If you need to retire a tag, prefer soft-deprecating (comment it out) until data pipelines and manual mappings are cleaned up.
- Run domain classification tools with the updated taxonomy to catch missing labels or overlap. When in doubt, search `data/domains.txt` to see real-world domains that may need coverage.

## Mapping guidelines

- Prefer one primary tag per domain; apply multiple secondary tags as needed for nuance.
- Use product intent over company name. Example: `mail.google.com` → `#email_calendar` + `#webmail`; `maps.google.com` → `#transportation_mobility` + `#navigation`.
- For gray areas, bias toward the user-facing purpose (e.g., a dev blog under a cloud provider should go to `#software_dev` + `#web_dev` rather than `#commerce_shopping`).
- Keep security/privacy tools explicitly tagged with `#security_privacy` to support opt-in filtering.
