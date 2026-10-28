"""Everything an agent needs for one project: model gateway, connectors and the knowledge index.

A configured connection always wins. Without one, demo mode falls back to sample connectors;
otherwise that capability is simply unavailable (None).
"""

from sqlmodel import Session, select

from .config import settings
from .connectors.confluence import ConfluenceConnector
from .connectors.jira import JiraConnector
from .connectors.sap_adt import AdtConnector
from .connectors.sap_rfc import RfcConnector
from .connectors.sap_profiles import detect, syntax_level
from .db import engine
from .demo.connectors import DemoConfluence, DemoIssues, DemoSap
from .knowledge import get_index
from .llm.gateway import Gateway
from .models import Connection, ModelConfig

CONNECTOR_CLASSES = {
    "jira": JiraConnector,
    "confluence": ConfluenceConnector,
    "sap_adt": AdtConnector,
    "sap_rfc": RfcConnector,
}

CONNECTION_KINDS = {
    "jira": "Jira / Jira Service Management",
    "confluence": "Confluence",
    "sap_adt": "SAP system (ADT, NW 7.40+ and ABAP Cloud)",
    "sap_rfc": "SAP system (RFC, older releases)",
}


def build_connector(conn: Connection):
    cls = CONNECTOR_CLASSES[conn.kind]
    return cls(conn.base_url, conn.auth, conn.username, conn.secret_ref, conn.options or {})


class Services:
    def __init__(self, project_id: int):
        self.project_id = project_id
        with Session(engine) as session:
            models = session.exec(select(ModelConfig).where(ModelConfig.project_id == project_id)).all()
            conns = session.exec(
                select(Connection).where(Connection.project_id == project_id, Connection.enabled == True)  # noqa: E712
            ).all()
        self.gateway = Gateway(list(models))
        self.issues = self._pick(conns, ("jira",), DemoIssues)
        self.confluence = self._pick(conns, ("confluence",), DemoConfluence)
        self.sap = self._pick(conns, ("sap_adt", "sap_rfc"), DemoSap)
        self.knowledge = get_index()

    @staticmethod
    def _pick(conns, kinds, demo_cls):
        for conn in conns:
            if conn.kind in kinds:
                return build_connector(conn)
        return demo_cls() if settings.demo_mode else None

    def sap_target(self) -> dict:
        """Release, profile and syntax level of the connected SAP system."""
        if self.sap is None:
            return {"basis_release": None, "profile": detect(None).as_dict(), "syntax": syntax_level(None)}
        info = self.sap.system_info()
        release, cloud = info.get("basis_release"), info.get("cloud", False)
        return {"basis_release": release, "cloud": cloud,
                "profile": detect(release, cloud).as_dict(), "syntax": syntax_level(release, cloud)}
