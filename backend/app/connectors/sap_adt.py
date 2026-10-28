"""SAP access through ADT REST services (/sap/bc/adt): NetWeaver 7.40+, S/4HANA and ABAP Cloud.

Phase 1 is read-only: system info, source, where-used. Writing, ATC, ABAP Unit and transports
come in Phase 2.
"""

import re
import xml.etree.ElementTree as ET

import httpx

from .. import vault

ADT_NS = {"atom": "http://www.w3.org/2005/Atom", "adtcore": "http://www.sap.com/adt/core"}

SOURCE_PATHS = [
    "/sap/bc/adt/oo/classes/{n}/source/main",
    "/sap/bc/adt/oo/interfaces/{n}/source/main",
    "/sap/bc/adt/programs/programs/{n}/source/main",
    "/sap/bc/adt/programs/includes/{n}/source/main",
]
OBJECT_URIS = {
    "CL": "/sap/bc/adt/oo/classes/{n}",
    "IF": "/sap/bc/adt/oo/interfaces/{n}",
}


class AdtConnector:
    def __init__(self, base_url: str, auth: str, username: str, secret_ref: str, options: dict):
        self.cloud = bool(options.get("cloud", False))
        params = {"sap-client": options["client"]} if options.get("client") else {}
        token = vault.resolve(secret_ref)
        headers = {}
        basic = None
        if auth == "bearer":
            headers["Authorization"] = f"Bearer {token}"
        else:
            basic = (username, token)
        self.client = httpx.Client(base_url=base_url.rstrip("/"), params=params, headers=headers,
                                   auth=basic, timeout=60, verify=options.get("verify_tls", True))
        self._csrf: str | None = None

    def _token(self) -> str:
        if self._csrf is None:
            r = self.client.get("/sap/bc/adt/discovery", headers={"x-csrf-token": "fetch"})
            r.raise_for_status()
            self._csrf = r.headers.get("x-csrf-token", "")
        return self._csrf

    def system_info(self) -> dict:
        r = self.client.get("/sap/bc/adt/system/components", headers={"Accept": "application/atom+xml;type=feed"})
        r.raise_for_status()
        components = {}
        root = ET.fromstring(r.content)
        for entry in root.findall("atom:entry", ADT_NS):
            name = (entry.findtext("atom:id", default="", namespaces=ADT_NS) or "").strip()
            title = entry.findtext("atom:title", default="", namespaces=ADT_NS) or ""
            release = re.search(r"\b(\d{3,4})\b", title)
            if name:
                components[name] = release.group(1) if release else title
        basis = components.get("SAP_BASIS")
        return {"basis_release": int(basis) if basis and basis.isdigit() else None,
                "cloud": self.cloud, "components": components}

    def read_source(self, name: str) -> str | None:
        n = name.lower()
        for path in SOURCE_PATHS:
            r = self.client.get(path.format(n=n), headers={"Accept": "text/plain"})
            if r.status_code == 200:
                return r.text
        return None

    def where_used(self, name: str) -> list[dict]:
        prefix = name[1:3].upper()
        uri = OBJECT_URIS.get(prefix, "/sap/bc/adt/programs/programs/{n}").format(n=name.lower())
        body = ('<?xml version="1.0" encoding="UTF-8"?>'
                '<usagereferences:usageReferenceRequest '
                'xmlns:usagereferences="http://www.sap.com/adt/ris/usageReferences">'
                '<usagereferences:affectedObjects/></usagereferences:usageReferenceRequest>')
        r = self.client.post("/sap/bc/adt/repository/informationsystem/usageReferences",
                             params={"uri": uri}, content=body,
                             headers={"x-csrf-token": self._token(), "Content-Type": "application/*"})
        if r.status_code != 200:
            return []
        callers = []
        root = ET.fromstring(r.content)
        for el in root.iter():
            if el.tag.endswith("adtObject"):
                callers.append({
                    "name": el.get(f"{{{ADT_NS['adtcore']}}}name", ""),
                    "type": el.get(f"{{{ADT_NS['adtcore']}}}type", ""),
                    "description": el.get(f"{{{ADT_NS['adtcore']}}}description", ""),
                })
        return [c for c in callers if c["name"] and c["name"].upper() != name.upper()]

    def open_transports(self, name: str) -> list[dict]:
        return []  # Phase 2

    def unit_tests(self, name: str) -> list[str]:
        source = self.read_source(name) or ""
        return re.findall(r"METHODS\s+(\w+)\s+FOR TESTING", source, flags=re.I)

    def test(self) -> str:
        self._token()
        info = self.system_info()
        return f"Connected, SAP_BASIS {info['basis_release'] or 'unknown'}"
