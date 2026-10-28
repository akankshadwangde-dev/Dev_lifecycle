"""First-run setup: default project, and in demo mode a demo model, sample work items and knowledge."""

from sqlmodel import Session, select

from .config import settings
from .db import engine
from .demo.connectors import DemoConfluence, DemoIssues
from .knowledge import reindex
from .llm.providers import STAGES
from .models import ModelConfig, Project, WorkItem


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


def seed() -> None:
    with Session(engine) as session:
        project = session.exec(select(Project)).first()
        if project is None:
            project = Project(name=settings.default_project)
            session.add(project)
            session.commit()
            session.refresh(project)
        if not settings.demo_mode:
            return
        has_models = session.exec(select(ModelConfig).where(ModelConfig.project_id == project.id)).first()
        if not has_models:
            session.add(ModelConfig(project_id=project.id, name="Demo model", provider="demo", model="demo",
                                    data_level="production", stages=list(STAGES), priority=900))
            session.commit()
        has_items = session.exec(select(WorkItem).where(WorkItem.project_id == project.id)).first()
        if not has_items:
            upsert_items(session, project.id, DemoIssues().fetch_items())
            reindex(project.id, DemoIssues(), DemoConfluence())
