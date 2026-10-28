"""Confluence Cloud and Confluence Data Center.

Base URL: Cloud https://<site>.atlassian.net/wiki, Data Center https://confluence.example.com
Options: spaces (list of space keys to read), publish_space (key the studio may write to),
publish_parent_id (optional parent page), deployment ("cloud" | "datacenter").
"""

from html import escape
from typing import Iterable

import httpx

from .. import vault
from ..textutil import html_to_text


class ConfluenceConnector:
    def __init__(self, base_url: str, auth: str, username: str, secret_ref: str, options: dict):
        self.base_url = base_url.rstrip("/")
        self.cloud = options.get("deployment", "cloud") == "cloud"
        self.spaces: list[str] = options.get("spaces", [])
        self.publish_space: str = options.get("publish_space", "")
        self.publish_parent_id: str = options.get("publish_parent_id", "")
        token = vault.resolve(secret_ref)
        headers = {"Accept": "application/json"}
        basic = None
        if auth == "bearer":
            headers["Authorization"] = f"Bearer {token}"
        else:
            basic = (username, token)
        self.client = httpx.Client(base_url=self.base_url, headers=headers, auth=basic, timeout=30)

    @property
    def can_publish(self) -> bool:
        return bool(self.publish_space)

    def _space_filter(self) -> str:
        if not self.spaces:
            return ""
        return " and space in (" + ",".join(f'"{s}"' for s in self.spaces) + ")"

    def search(self, query: str, limit: int = 5) -> list[dict]:
        terms = " ".join(query.replace('"', " ").split()[:12])
        cql = f'type = page and text ~ "{terms}"{self._space_filter()}'
        r = self.client.get("/rest/api/search", params={"cql": cql, "limit": limit})
        r.raise_for_status()
        hits = []
        for res in r.json().get("results", []):
            content = res.get("content") or {}
            hits.append({
                "ref": f"CONF-{content.get('id', '')}",
                "title": content.get("title") or res.get("title", ""),
                "excerpt": html_to_text(res.get("excerpt", "")),
                "url": self.base_url + (res.get("url") or ""),
                "updated": res.get("lastModified", ""),
            })
        return hits

    def pages(self) -> Iterable[dict]:
        for space in self.spaces:
            start = 0
            while True:
                r = self.client.get("/rest/api/content", params={
                    "spaceKey": space, "type": "page", "expand": "body.storage,version",
                    "limit": 50, "start": start,
                })
                r.raise_for_status()
                data = r.json()
                for page in data.get("results", []):
                    yield {
                        "ref": f"CONF-{page['id']}",
                        "title": page.get("title", ""),
                        "body": html_to_text(page.get("body", {}).get("storage", {}).get("value", "")),
                        "url": self.base_url + page.get("_links", {}).get("webui", ""),
                        "updated": page.get("version", {}).get("when", ""),
                        "space": space,
                    }
                if data.get("size", 0) < 50:
                    break
                start += 50

    @staticmethod
    def to_storage(page: dict) -> str:
        """Render a drafted page (sections of heading + body text/list) as Confluence storage format."""
        parts = []
        for section in page.get("sections", []):
            parts.append(f"<h2>{escape(section.get('heading', ''))}</h2>")
            body = section.get("body", "")
            if isinstance(body, list):
                parts.append("<ul>" + "".join(f"<li>{escape(str(x))}</li>" for x in body) + "</ul>")
            else:
                parts.extend(f"<p>{escape(p)}</p>" for p in str(body).split("\n\n") if p.strip())
        return "".join(parts)

    def _find(self, title: str) -> dict | None:
        r = self.client.get("/rest/api/content", params={
            "spaceKey": self.publish_space, "title": title, "expand": "body.storage,version"})
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None

    def publish(self, page: dict) -> dict:
        if not self.can_publish:
            raise PermissionError("No publish space is configured for this Confluence connection")
        existing = self._find(page["title"]) if page.get("mode") == "update" else None
        if existing:
            # Append the new sections to the existing page as a new version.
            value = existing["body"]["storage"]["value"] + self.to_storage(page)
            r = self.client.put(f"/rest/api/content/{existing['id']}", json={
                "type": "page", "title": existing["title"],
                "version": {"number": existing["version"]["number"] + 1},
                "body": {"storage": {"value": value, "representation": "storage"}},
            })
            r.raise_for_status()
            return {"ref": f"CONF-{existing['id']}",
                    "url": self.base_url + existing.get("_links", {}).get("webui", ""), "updated": True}
        body = {
            "type": "page",
            "title": page["title"],
            "space": {"key": self.publish_space},
            "body": {"storage": {"value": self.to_storage(page), "representation": "storage"}},
        }
        if self.publish_parent_id:
            body["ancestors"] = [{"id": self.publish_parent_id}]
        r = self.client.post("/rest/api/content", json=body)
        r.raise_for_status()
        data = r.json()
        labels = [{"prefix": "global", "name": label} for label in page.get("labels", [])]
        if labels:
            self.client.post(f"/rest/api/content/{data['id']}/label", json=labels)
        return {"ref": f"CONF-{data['id']}", "url": self.base_url + data.get("_links", {}).get("webui", "")}

    def test(self) -> str:
        r = self.client.get("/rest/api/space", params={"limit": 1})
        r.raise_for_status()
        return "Connected" + (f", reading {len(self.spaces)} space(s)" if self.spaces else "")
