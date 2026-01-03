"""Shared helpers for the history-view data tooling."""

DEFAULT_CATEGORY_FILENAME = "config/categories.yaml"
DEFAULT_DOMAIN_MAP_FILENAME = "config/domain-category-map.yaml"
DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"


__all__ = [
    "DEFAULT_MODEL",
    "OPENAI_ENDPOINT",
    "DEFAULT_CATEGORY_FILENAME",
    "DEFAULT_DOMAIN_MAP_FILENAME",
]
