"""First-run setup, and switching sample data on and off for a project."""

from sqlmodel import Session, delete, select

from .config import settings
from .db import engine
from .demo import data as sample
from .demo.connectors import DemoConfluence, DemoIssues
from .knowledge import get_index
from .llm.providers import STAGES
from .models import AuditEntry, ModelConfig, Project, WorkItem
from .textutil import find_objects

SAMPLE_KEYS = [i["key"] for i in sample.ISSUES]


def upsert_items(session: Session, project_id: int, items: list[dict]) -> int:
    count = 0
    for data in items:
        existing = session.exec(
            select(WorkItem).where(WorkItem.project_id == project_id, WorkItem.key == data["key"])
        ).first()
        fields = {k: data.get(k, "") for k in ("title", "description", "kind", "priority", "source", "assignee")}
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            existing.objects = data.get("objects", [])
            session.add(existing)
        else:
            session.add(WorkItem(project_id=project_id, key=data["key"], objects=data.get("objects", []), **fields))
            count += 1
    session.commit()
    return count


def load_sample_data(session: Session, project: Project) -> None:
    if not session.exec(select(ModelConfig).where(ModelConfig.project_id == project.id,
                                                  ModelConfig.provider == "demo")).first():
        session.add(ModelConfig(project_id=project.id, name="Sample model", provider="demo", model="demo",
                                data_level="production", stages=list(STAGES), priority=900))
    upsert_items(session, project.id, DemoIssues().fetch_items())
    index = get_index()
    for page in DemoConfluence().pages():
        index.upsert(project.id, "confluence", page["ref"], page["title"], page["body"], page["url"], page["updated"])
    for t in DemoIssues().resolved_items():
        index.upsert(project.id, "ticket", t["key"], t["title"],
                     f"{t['description']}\nResolution: {t['resolution']}", t.get("url", ""))
    project.sample_data = True
    session.add(project)
    session.commit()


def remove_sample_data(session: Session, project: Project) -> None:
    """Remove every trace of the sample data: items, their flows and audit lines, sample model, sample pages."""
    from .orchestrator.flows import delete_flow

    for item in session.exec(select(WorkItem).where(WorkItem.project_id == project.id,
                                                    WorkItem.key.in_(SAMPLE_KEYS))).all():  # type: ignore[attr-defined]
        delete_flow(item)
        session.delete(item)
    session.exec(delete(AuditEntry).where(AuditEntry.project_id == project.id,
                                          AuditEntry.item_key.in_(SAMPLE_KEYS)))  # type: ignore[attr-defined]
    session.exec(delete(ModelConfig).where(ModelConfig.project_id == project.id, ModelConfig.provider == "demo"))
    refs = [p["ref"] for p in sample.CONFLUENCE_PAGES] + [t["key"] for t in sample.RESOLVED]
    get_index().delete_refs(project.id, refs, prefixes=("SAMPLE-",) + tuple(f"DRAFT-{k}" for k in SAMPLE_KEYS))
    project.sample_data = False
    session.add(project)
    session.commit()


def seed() -> None:
    with Session(engine) as session:
        project = session.exec(select(Project)).first()
        if project is None:
            project = Project(name=settings.default_project)
            session.add(project)
            session.commit()
            session.refresh(project)
            if settings.sample_data:
                load_sample_data(session, project)
        elif not project.sample_data:
            # Databases from before sample data became a switch may still hold it, and the sample name.
            remove_sample_data(session, project)
            if project.name == "O2C Rollout":
                project.name = settings.default_project
                session.add(project)
                session.commit()


def create_item(session: Session, project_id: int, kind: str, title: str, description: str,
                priority: str = "", key: str = "", assignee: str = "") -> WorkItem:
    if not key:
        keys = session.exec(select(WorkItem.key).where(WorkItem.project_id == project_id)).all()
        n = 1 + max((int(k[4:]) for k in keys if k.startswith("REQ-") and k[4:].isdigit()), default=0)
        key = f"REQ-{n}"
    item = WorkItem(project_id=project_id, key=key, title=title, description=description, kind=kind,
                    priority=priority, source="manual", assignee=assignee,
                    objects=find_objects(f"{title}\n{description}"))
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
