"""Demo connectors backed by app.demo.data. Same interfaces as the real connectors."""

import itertools

from ..textutil import find_objects
from . import data


class DemoIssues:
    def fetch_items(self) -> list[dict]:
        return [{**i, "objects": find_objects(f"{i['title']}\n{i['description']}")} for i in data.ISSUES]

    def resolved_items(self) -> list[dict]:
        return list(data.RESOLVED)

    def test(self) -> str:
        return "Sample data"


class DemoConfluence:
    can_publish = True
    _ids = itertools.count(9001)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        return []  # the local knowledge index already holds the demo pages

    def pages(self):
        return [dict(p) for p in data.CONFLUENCE_PAGES]

    def publish(self, page: dict) -> dict:
        return {"ref": f"CONF-{next(self._ids)}", "url": "", "simulated": True}

    def test(self) -> str:
        return "Sample data"


class DemoSap:
    def system_info(self) -> dict:
        return {"basis_release": 758, "cloud": False, "components": {"SAP_BASIS": "758", "S4CORE": "108"}}

    def read_source(self, name: str) -> str | None:
        return data.SAP_SOURCES.get(name.upper())

    def where_used(self, name: str) -> list[dict]:
        return data.WHERE_USED.get(name.upper(), [])

    def open_transports(self, name: str) -> list[dict]:
        return data.OPEN_TRANSPORTS.get(name.upper(), [])

    def unit_tests(self, name: str) -> list[str]:
        return data.UNIT_TESTS.get(name.upper(), [])

    def test(self) -> str:
        return "Sample data, SAP_BASIS 758"
