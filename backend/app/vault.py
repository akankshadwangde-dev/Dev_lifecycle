"""Resolves secret references. Secrets are never stored in the database, only references to them."""

import os


class SecretNotFound(Exception):
    pass


def resolve(ref: str) -> str:
    """Resolve a reference such as ``env:JIRA_TOKEN``. An empty reference resolves to ""."""
    if not ref:
        return ""
    scheme, _, name = ref.partition(":")
    if scheme == "env" and name:
        value = os.environ.get(name)
        if value is None:
            raise SecretNotFound(f"Environment variable {name} is not set")
        return value
    raise SecretNotFound(f"Unsupported secret reference '{ref}'. Use env:NAME.")
