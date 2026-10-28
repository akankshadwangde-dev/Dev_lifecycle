from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..deps import Ctx, CtxDep, SessionDep, audit, require
from ..models import WorkItem
from ..orchestrator import flows
from ..roles import may_decide
from ..seed import create_item, upsert_items
from ..services import Services

router = APIRouter(prefix="/api/work-items", tags=["work items"])


class NewItem(BaseModel):
    kind: str = "new"  # new | change | incident
    title: str
    description: str = ""
    priority: str = ""
    key: str = ""


class Decision(BaseModel):
    action: str  # approve | revise | no_code
    comment: str = ""


def _get(session: Session, ctx: Ctx, key: str) -> WorkItem:
    item = session.exec(select(WorkItem).where(WorkItem.project_id == ctx.project_id, WorkItem.key == key)).first()
    if item is None:
        raise HTTPException(404, f"Work item {key} not found")
    return item


def _detail(session: Session, item: WorkItem, ctx: Ctx) -> dict:
    session.refresh(item)  # earlier commits (flow sync, audit) expire the loaded fields
    return {"item": item.model_dump(), "flow": flows.view(item, ctx.role)}


@router.get("")
def list_items(ctx: Ctx = CtxDep, session: Session = SessionDep) -> list[dict]:
    items = session.exec(
        select(WorkItem).where(WorkItem.project_id == ctx.project_id).order_by(WorkItem.updated.desc())
    ).all()
    return [{**i.model_dump(), "can_act": bool(i.gate) and may_decide(ctx.role, i.gate, "approve")} for i in items]


@router.post("")
def create(body: NewItem, ctx: Ctx = require("create_items"), session: Session = SessionDep) -> dict:
    if body.kind not in ("new", "change", "incident"):
        raise HTTPException(400, "Type must be new, change or incident")
    if not body.title.strip():
        raise HTTPException(400, "Give the item a title")
    key = body.key.strip().upper()
    if key and session.exec(select(WorkItem).where(WorkItem.project_id == ctx.project_id, WorkItem.key == key)).first():
        raise HTTPException(409, f"{key} already exists")
    item = create_item(session, ctx.project_id, body.kind, body.title.strip(), body.description.strip(),
                       body.priority, key, assignee=ctx.user)
    audit(session, ctx, "Added item", item.key)
    return _detail(session, item, ctx)


@router.post("/sync")
def sync(ctx: Ctx = CtxDep, session: Session = SessionDep) -> dict:
    svc = Services(ctx.project_id)
    if svc.issues is None:
        raise HTTPException(400, "No Jira connection is set up. Add one under Settings > Connections, or add items by hand.")
    try:
        added = upsert_items(session, ctx.project_id, svc.issues.fetch_items())
    except Exception as exc:
        raise HTTPException(502, f"Could not read from Jira: {exc}") from exc
    audit(session, ctx, "Synced work items", detail=f"{added} new")
    return {"added": added}


@router.get("/{key}")
def get_item(key: str, ctx: Ctx = CtxDep, session: Session = SessionDep) -> dict:
    return _detail(session, _get(session, ctx, key), ctx)


@router.post("/{key}/start")
def start(key: str, ctx: Ctx = CtxDep, session: Session = SessionDep) -> dict:
    item = _get(session, ctx, key)
    if item.stage:
        raise HTTPException(409, "This item has already started")
    try:
        flows.start(session, item, ctx.model_id)
    except flows.FlowError:
        pass  # the error is stored on the item and shown in the view
    audit(session, ctx, "Started analysis", key, model=_model(item, ctx))
    return _detail(session, item, ctx)


@router.post("/{key}/decide")
def decide(key: str, body: Decision, ctx: Ctx = CtxDep, session: Session = SessionDep) -> dict:
    item = _get(session, ctx, key)
    if not item.gate:
        raise HTTPException(409, "Nothing is waiting for a decision")
    if not may_decide(ctx.role, item.gate, body.action):
        raise HTTPException(403, "Your role cannot take this decision")
    if body.action == "revise" and not body.comment.strip():
        raise HTTPException(400, "Say what should change")
    gate = item.gate
    decision = {"action": body.action, "comment": body.comment, "user": ctx.user, "role": ctx.role,
                "model_id": ctx.model_id}
    try:
        flows.decide(session, item, decision)
    except flows.FlowError:
        pass
    audit(session, ctx, f"{gate}: {body.action}", key, body.comment)
    return _detail(session, item, ctx)


@router.post("/{key}/retry")
def retry(key: str, ctx: Ctx = CtxDep, session: Session = SessionDep) -> dict:
    item = _get(session, ctx, key)
    try:
        flows.retry(session, item)
    except flows.FlowError:
        pass
    audit(session, ctx, "Retried step", key)
    return _detail(session, item, ctx)


def _model(item: WorkItem, ctx: Ctx) -> str:
    view = flows.view(item, ctx.role)
    return (view.get("outputs") or {}).get("knowledge", {}).get("model", "")
