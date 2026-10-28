"""Start, inspect and advance the lifecycle flow of a work item."""

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from sqlmodel import Session

from ..config import settings
from ..models import WorkItem, utcnow
from ..roles import deciders, gate_actions
from .graph import build_graph


class FlowError(Exception):
    pass


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        conn = sqlite3.connect(settings.checkpoint_path, check_same_thread=False)
        _graph = build_graph(SqliteSaver(conn))
    return _graph


def set_graph(graph) -> None:
    """Swap the compiled graph (tests use an in-memory checkpointer)."""
    global _graph
    _graph = graph


def _config(item: WorkItem) -> dict:
    return {"configurable": {"thread_id": f"{item.project_id}:{item.key}"}}


def _item_dict(item: WorkItem) -> dict:
    return {"key": item.key, "title": item.title, "description": item.description, "kind": item.kind,
            "priority": item.priority, "source": item.source, "objects": item.objects or []}


def _pending_gate(snapshot) -> str | None:
    for task in snapshot.tasks:
        for intr in task.interrupts:
            return intr.value.get("gate")
    return None


def _run(session: Session, item: WorkItem, payload) -> None:
    graph = get_graph()
    try:
        graph.invoke(payload, _config(item))
        item.error = ""
    except Exception as exc:
        item.error = str(exc)
    snapshot = graph.get_state(_config(item))
    values = snapshot.values or {}
    gate = _pending_gate(snapshot)
    item.stage = values.get("stage", item.stage)
    item.gate = gate or ""
    if item.error:
        item.status = "error"
    elif gate:
        item.status = "waiting"
    elif not snapshot.next:
        item.status = "done"
    else:
        item.status = "in_progress"
    item.updated = utcnow()
    session.add(item)
    session.commit()
    if item.error:
        raise FlowError(item.error)


def start(session: Session, item: WorkItem, preferred_model_id: int | None) -> None:
    state = {"project_id": item.project_id, "item": _item_dict(item), "preferred_model_id": preferred_model_id,
             "outputs": {}, "feedback": {}, "history": []}
    _run(session, item, state)


def decide(session: Session, item: WorkItem, decision: dict) -> None:
    _run(session, item, Command(resume=decision))


def retry(session: Session, item: WorkItem) -> None:
    """Re-run the step that failed, from the last saved checkpoint."""
    _run(session, item, None)


def delete_flow(item: WorkItem) -> None:
    """Forget a work item's saved flow (used when sample data is removed)."""
    try:
        get_graph().checkpointer.delete_thread(_config(item)["configurable"]["thread_id"])
    except Exception:
        pass  # nothing saved for this item


def view(item: WorkItem, role: str) -> dict:
    snapshot = get_graph().get_state(_config(item))
    values = snapshot.values or {}
    if not values:
        return {"started": False}
    gate = _pending_gate(snapshot)
    return {
        "started": True,
        "stage": values.get("stage", ""),
        "resolution": values.get("resolution", ""),
        "outputs": values.get("outputs", {}),
        "history": values.get("history", []),
        "gate": {"name": gate, "actions": gate_actions(role, gate), "waiting_for": deciders(gate)} if gate else None,
        "done": not snapshot.next and not item.error,
        "error": item.error or None,
    }
