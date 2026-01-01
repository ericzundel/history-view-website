I want to perform some filtering on the domains database.

I want you to dump all of the domains found in the `history.db` file using `sqlite3 history.db 'select domain from domains;' >data/domains.txt`

Go go through the data/domains.txt file and search for domains that might
violate personal privacy:

- Finance: Personal Financial information (banks, brokerages, investments). General news sites on investing are OK, but avoid those related to specific investments (commodities, forex, crypto currency, etc.)
- Health: Medical conditions including chronic conditions, reproductive health and mental health
- Legal: information and services related to family law, personal injury, or criminal law
- Other: Sexuality, Gender, obscenity

When you find such a domain, add it to the `config/domain-blocklist.yml` file. The format is explained in `config/README.md` Preserve any existing entries and when you are done, sort and dedup the list of blocked domains.
