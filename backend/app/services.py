"""Everything an agent needs for one project: model gateway, connectors and the knowledge index.

A configured connection always wins. Without one, a project with sample data switched on falls
back to sample connectors; otherwise that capability is simply unavailable (None).
"""

from sqlmodel import Session, select

from .connectors.confluence import ConfluenceConnector
from .connectors.jira import JiraConnector
from .connectors.sap_adt import AdtConnector
from .connectors.sap_rfc import RfcConnector
from .connectors.sap_profiles import detect, syntax_level
from .db import engine
from .demo.connectors import DemoConfluence, DemoIssues, DemoSap
from .knowledge import get_index
from .llm.gateway import Gateway
from .models import Connection, ModelConfig, Project

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
            self.project = session.get(Project, project_id) or Project(name="")
            models = session.exec(select(ModelConfig).where(ModelConfig.project_id == project_id)).all()
            conns = session.exec(
                select(Connection).where(Connection.project_id == project_id, Connection.enabled == True)  # noqa: E712
            ).all()
        sample = bool(self.project.sample_data)
        self.gateway = Gateway(list(models))
        self.issues = self._pick(conns, ("jira",), DemoIssues, sample)
        self.confluence = self._pick(conns, ("confluence",), DemoConfluence, sample)
        self.sap = self._pick(conns, ("sap_adt", "sap_rfc"), DemoSap, sample)
        self.knowledge = get_index()

    @staticmethod
    def _pick(conns, kinds, demo_cls, sample: bool):
        for conn in conns:
            if conn.kind in kinds:
                return build_connector(conn)
        return demo_cls() if sample else None

    def sap_target(self) -> dict:
        """Release, profile and syntax level of the connected SAP system."""
        if self.sap is None:
            # No system connected: use the release set under Settings > General, if any.
            release, cloud = self.project.sap_release, bool(self.project.sap_cloud)
        else:
            info = self.sap.system_info()
            release, cloud = info.get("basis_release"), info.get("cloud", False)
        return {"basis_release": release, "cloud": cloud,
                "profile": detect(release, cloud).as_dict(), "syntax": syntax_level(release, cloud)}
