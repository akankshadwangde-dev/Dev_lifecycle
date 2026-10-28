"""Interfaces every connector implements. Real and demo connectors are interchangeable."""

from typing import Iterable, Protocol


class IssueSource(Protocol):
    """Jira, Jira Service Management, ServiceNow ..."""

    def fetch_items(self) -> list[dict]:
        """Open items as dicts: key, title, description, kind, priority, assignee, source."""

    def resolved_items(self) -> list[dict]:
        """Resolved items with their resolution notes, for the knowledge base."""

    def test(self) -> str:
        """Raise on failure, return a short success message."""


class KnowledgeSource(Protocol):
    """Confluence (Cloud or Data Center)."""

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Hits as dicts: ref, title, excerpt, url, updated."""

    def pages(self) -> Iterable[dict]:
        """Every page in the configured spaces: ref, title, body (plain text), url, updated."""

    def publish(self, page: dict) -> dict:
        """Create or update a page. Returns {ref, url}."""

    def test(self) -> str: ...


class SapSystem(Protocol):
    def system_info(self) -> dict:
        """{basis_release: int | None, cloud: bool, components: {name: release}}"""

    def read_source(self, name: str) -> str | None:
        """Active source of a class, interface or program, or None if not found."""

    def where_used(self, name: str) -> list[dict]:
        """Callers as dicts: name, type, description."""

    def open_transports(self, name: str) -> list[dict]:
        """Unreleased transports containing the object: id, owner, text."""

    def unit_tests(self, name: str) -> list[str]:
        """Names of existing ABAP Unit test methods for the object."""

    def test(self) -> str: ...
