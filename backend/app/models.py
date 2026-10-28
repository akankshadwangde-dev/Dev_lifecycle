"""Database tables."""

from datetime import datetime, timezone

from sqlmodel import JSON, Column, Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    # Sample tickets, pages, SAP code and a sample model, for demos. Off unless an admin turns it on.
    sample_data: bool = False
    # Target release for generated code while no SAP system is connected (SAP_BASIS, e.g. 758).
    sap_release: int | None = None
    sap_cloud: bool = False


class ModelConfig(SQLModel, table=True):
    """A model registered by an admin. See app.llm.providers for provider keys."""

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    name: str
    provider: str
    model: str
    api_base: str = ""
    secret_ref: str = ""  # e.g. env:ANTHROPIC_API_KEY
    data_level: str = "code"  # highest data level this model may receive
    stages: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    enabled: bool = True
    priority: int = 100  # lower is tried first


class Connection(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    kind: str  # jira | confluence | sap_adt | sap_rfc
    name: str
    base_url: str = ""
    auth: str = "basic"  # basic | bearer
    username: str = ""
    secret_ref: str = ""
    options: dict = Field(default_factory=dict, sa_column=Column(JSON))
    enabled: bool = True
    status: str = "untested"  # untested | ok | error
    detail: str = ""


class WorkItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    key: str = Field(index=True)
    title: str
    description: str = ""
    kind: str = "new"  # new | change | incident
    priority: str = ""
    source: str = "jira"
    assignee: str = ""
    objects: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    # Flow progress, kept in sync by app.orchestrator.flows
    stage: str = ""  # last stage reached; empty until the flow starts
    gate: str = ""  # gate waiting for a decision, if any
    status: str = "open"  # open | in_progress | waiting | done | error
    error: str = ""
    updated: datetime = Field(default_factory=utcnow)


class AuditEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    ts: datetime = Field(default_factory=utcnow)
    user: str
    role: str
    action: str
    item_key: str = ""
    detail: str = ""
    model: str = ""
