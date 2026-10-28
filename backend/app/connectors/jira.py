"""Jira Cloud and Jira Data Center / Server (also Jira Service Management, which uses the same API)."""

import httpx

from .. import vault
from ..textutil import adf_to_text, find_objects

INCIDENT_TYPES = {"incident", "bug", "problem", "defect"}
CHANGE_TYPES = {"change", "change request", "improvement"}


class JiraConnector:
    def __init__(self, base_url: str, auth: str, username: str, secret_ref: str, options: dict):
        self.base_url = base_url.rstrip("/")
        self.cloud = options.get("deployment", "cloud") == "cloud"
        self.jql = options.get("jql") or "statusCategory != Done ORDER BY updated DESC"
        self.resolved_jql = options.get("resolved_jql") or "statusCategory = Done ORDER BY updated DESC"
        token = vault.resolve(secret_ref)
        headers = {"Accept": "application/json"}
        if auth == "bearer":
            headers["Authorization"] = f"Bearer {token}"
            basic = None
        else:
            basic = (username, token)
        self.client = httpx.Client(base_url=self.base_url, headers=headers, auth=basic, timeout=30)

    # Jira Cloud moved JQL search to /search/jql; Data Center keeps /search on API v2.
    def _search(self, jql: str, max_results: int = 50) -> list[dict]:
        fields = "summary,description,issuetype,priority,assignee,labels,resolution,comment"
        if self.cloud:
            r = self.client.get("/rest/api/3/search/jql",
                                params={"jql": jql, "maxResults": max_results, "fields": fields})
        else:
            r = self.client.get("/rest/api/2/search",
                                params={"jql": jql, "maxResults": max_results, "fields": fields})
        r.raise_for_status()
        return r.json().get("issues", [])

    def _map(self, issue: dict) -> dict:
        f = issue.get("fields", {})
        description = f.get("description")
        text = adf_to_text(description) if isinstance(description, dict) else (description or "")
        issue_type = ((f.get("issuetype") or {}).get("name") or "").lower()
        labels = {label.lower() for label in f.get("labels") or []}
        if issue_type in INCIDENT_TYPES or "incident" in labels:
            kind = "incident"
        elif issue_type in CHANGE_TYPES or "change" in labels:
            kind = "change"
        else:
            kind = "new"
        title = f.get("summary", "")
        return {
            "key": issue["key"],
            "title": title,
            "description": text.strip(),
            "kind": kind,
            "priority": (f.get("priority") or {}).get("name", ""),
            "assignee": (f.get("assignee") or {}).get("displayName", ""),
            "source": "jira",
            "objects": find_objects(f"{title}\n{text}"),
        }

    def fetch_items(self) -> list[dict]:
        return [self._map(i) for i in self._search(self.jql)]

    def resolved_items(self) -> list[dict]:
        items = []
        for issue in self._search(self.resolved_jql, max_results=100):
            mapped = self._map(issue)
            comments = ((issue.get("fields") or {}).get("comment") or {}).get("comments", [])
            notes = [adf_to_text(c.get("body")) if isinstance(c.get("body"), dict) else c.get("body", "")
                     for c in comments[-3:]]
            mapped["resolution"] = "\n".join(n for n in notes if n)
            mapped["url"] = f"{self.base_url}/browse/{issue['key']}"
            items.append(mapped)
        return items

    def test(self) -> str:
        r = self.client.get("/rest/api/3/myself" if self.cloud else "/rest/api/2/myself")
        r.raise_for_status()
        return f"Connected as {r.json().get('displayName', 'unknown user')}"
