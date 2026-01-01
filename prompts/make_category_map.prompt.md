From the repo root, dump all domains and titles from the database:
`sqlite3 data/history.db "select domain, title from domains;" > data/domains-titles.txt`

Create a sub-agent to assign primary categories:

- Read `config/categories.md` to understand what a primary category means.
- Read `config/categories.yaml` and collect the tags marked `type: primary` (fast-fail if any referenced tag is missing).
- Treat subdomains independently (do not inherit from parent domains).
- For each domain in `data/domains-titles.txt`, choose exactly one primary category tag from `config/categories.yaml`. Use any existing knowledge plus the title from `data/history.db` (`sqlite3 data/history.db "select title from domains where domain = '<domain>';"`) to guide classification.
- Record each domain and its primary category in `config/domain-category-map.yaml`; if a domain already has a primary, keep it.

Create a sub-agent to assign secondary categories:

- Read `config/categories.md` to understand what a secondary category means.
- For each domain in `config/domain-category-map.yaml`, read its primary tag.
- Choose up to 5 secondary categories per domain (can be any tag—primary or secondary—from `config/categories.yaml`). If primary is `other`, still choose specific secondary tags.
- Record secondary tags under the domain’s `secondary:` list in `config/domain-category-map.yaml`.
- If secondary tags already exist, validate them and improve if needed; adding more is fine.

Validation sub-agent:

- Ensure `config/domain-category-map.yaml` includes every domain from `data/domains-titles.txt`.
- Ensure each domain has one primary category and a secondary list (can be empty only if time expires).
- Ensure no duplicate domain entries and that YAML is well-formed.
- Sort domain entries alphabetically by domain name.
- If there are domains with empty categories, report them.

Timebox: If work exceeds 5 minutes, stop and report progress.

See also: @make_category_map.prompt.md @SPEC_v1.md @analyze_domains_and_block.prompt.md

- If a domain truly has no clear secondary tags (e.g., only `securityprivacy` applies), you may leave `secondary: []`.
- If a domain cannot be classified due to missing categories or ambiguity, skip it and list it at the end of the run.
- If the title is missing, still classify based on the domain to the best of your ability.
