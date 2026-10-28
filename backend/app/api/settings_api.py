"""Models, connections, knowledge sources, audit log and role definitions."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..deps import Ctx, CtxDep, SessionDep, audit, require
from ..knowledge import get_index, reindex
from ..llm.gateway import call_model
from ..llm.providers import DATA_LEVELS, PROVIDERS, STAGES
from ..models import AuditEntry, Connection, ModelConfig
from ..roles import GATES, ROLES
from ..services import CONNECTION_KINDS, Services, build_connector
from ..connectors.sap_profiles import detect

router = APIRouter(prefix="/api", tags=["settings"])


# ---------- roles ----------

@router.get("/roles")
def roles() -> dict:
    return {"roles": {k: {"label": v["label"], "can": sorted(v["can"])} for k, v in ROLES.items()},
            "gates": {g: {a: sorted(c) for a, c in actions.items()} for g, actions in GATES.items()}}


# ---------- models ----------

class ModelIn(BaseModel):
    name: str
    provider: str
    model: str
    api_base: str = ""
    secret_ref: str = ""
    data_level: str = "code"
    stages: list[str] = []
    enabled: bool = True
    priority: int = 100


def _check_model(body: ModelIn) -> None:
    if body.provider not in PROVIDERS:
        raise HTTPException(400, f"Unknown provider '{body.provider}'")
    if body.data_level not in DATA_LEVELS:
        raise HTTPException(400, f"Data level must be one of {DATA_LEVELS}")
    if PROVIDERS[body.provider]["needs_base"] and not body.api_base:
        raise HTTPException(400, "This provider needs an endpoint URL")


@router.get("/models/providers")
def providers() -> dict:
    return {"providers": PROVIDERS, "data_levels": DATA_LEVELS, "stages": STAGES}


@router.get("/models")
def list_models(ctx: Ctx = CtxDep, session: Session = SessionDep) -> list[ModelConfig]:
    return list(session.exec(select(ModelConfig).where(ModelConfig.project_id == ctx.project_id)
                             .order_by(ModelConfig.priority)).all())


@router.post("/models")
def add_model(body: ModelIn, ctx: Ctx = require("manage_models"), session: Session = SessionDep) -> ModelConfig:
    _check_model(body)
    model = ModelConfig(project_id=ctx.project_id, **body.model_dump())
    session.add(model)
    session.commit()
    audit(session, ctx, "Added model", detail=f"{model.name} ({model.provider})")
    session.refresh(model)
    return model


@router.put("/models/{model_id}")
def update_model(model_id: int, body: ModelIn, ctx: Ctx = require("manage_models"),
                 session: Session = SessionDep) -> ModelConfig:
    _check_model(body)
    model = session.get(ModelConfig, model_id)
    if model is None or model.project_id != ctx.project_id:
        raise HTTPException(404, "Model not found")
    for k, v in body.model_dump().items():
        setattr(model, k, v)
    session.add(model)
    session.commit()
    audit(session, ctx, "Changed model", detail=model.name)
    session.refresh(model)
    return model


@router.delete("/models/{model_id}")
def delete_model(model_id: int, ctx: Ctx = require("manage_models"), session: Session = SessionDep) -> dict:
    model = session.get(ModelConfig, model_id)
    if model is None or model.project_id != ctx.project_id:
        raise HTTPException(404, "Model not found")
    session.delete(model)
    session.commit()
    audit(session, ctx, "Removed model", detail=model.name)
    return {"ok": True}


@router.post("/models/{model_id}/test")
def test_model(model_id: int, ctx: Ctx = CtxDep, session: Session = SessionDep) -> dict:
    model = session.get(ModelConfig, model_id)
    if model is None or model.project_id != ctx.project_id:
        raise HTTPException(404, "Model not found")
    try:
        reply = call_model(model, "Reply with the single word OK.", "Connection test", "test")
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:500]}
    return {"ok": True, "message": reply.strip()[:200] or "Answered"}


# ---------- connections ----------

class ConnectionIn(BaseModel):
    kind: str
    name: str
    base_url: str = ""
    auth: str = "basic"
    username: str = ""
    secret_ref: str = ""
    options: dict = {}
    enabled: bool = True


@router.get("/connections/kinds")
def connection_kinds() -> dict:
    return CONNECTION_KINDS


@router.get("/connections")
def list_connections(ctx: Ctx = CtxDep, session: Session = SessionDep) -> list[Connection]:
    return list(session.exec(select(Connection).where(Connection.project_id == ctx.project_id)).all())


@router.post("/connections")
def add_connection(body: ConnectionIn, ctx: Ctx = require("manage_connections"),
                   session: Session = SessionDep) -> Connection:
    if body.kind not in CONNECTION_KINDS:
        raise HTTPException(400, f"Unknown connection type '{body.kind}'")
    conn = Connection(project_id=ctx.project_id, **body.model_dump())
    session.add(conn)
    session.commit()
    audit(session, ctx, "Added connection", detail=f"{conn.name} ({conn.kind})")
    session.refresh(conn)
    return conn


@router.delete("/connections/{conn_id}")
def delete_connection(conn_id: int, ctx: Ctx = require("manage_connections"),
                      session: Session = SessionDep) -> dict:
    conn = session.get(Connection, conn_id)
    if conn is None or conn.project_id != ctx.project_id:
        raise HTTPException(404, "Connection not found")
    session.delete(conn)
    session.commit()
    audit(session, ctx, "Removed connection", detail=conn.name)
    return {"ok": True}


@router.post("/connections/{conn_id}/test")
def test_connection(conn_id: int, ctx: Ctx = CtxDep, session: Session = SessionDep) -> Connection:
    conn = session.get(Connection, conn_id)
    if conn is None or conn.project_id != ctx.project_id:
        raise HTTPException(404, "Connection not found")
    try:
        connector = build_connector(conn)
        conn.detail = connector.test()
        if conn.kind.startswith("sap_"):
            info = connector.system_info()
            profile = detect(info.get("basis_release"), info.get("cloud", False))
            conn.options = {**(conn.options or {}), "basis_release": info.get("basis_release"),
                            "profile": profile.key}
            conn.detail += f" · {profile.label} profile"
        conn.status = "ok"
    except Exception as exc:
        conn.status, conn.detail = "error", str(exc)[:500]
    session.add(conn)
    session.commit()
    session.refresh(conn)
    return conn


# ---------- knowledge ----------

@router.get("/knowledge/search")
def search(q: str, ctx: Ctx = CtxDep) -> list[dict]:
    hits = get_index().search(ctx.project_id, q, limit=10)
    for h in hits:
        h.pop("body", None)
    return hits


@router.get("/knowledge/sources")
def sources(ctx: Ctx = CtxDep) -> dict:
    return get_index().counts(ctx.project_id)


@router.post("/knowledge/reindex")
def run_reindex(ctx: Ctx = require("manage_knowledge"), session: Session = SessionDep) -> dict:
    svc = Services(ctx.project_id)
    try:
        counts = reindex(ctx.project_id, svc.issues, svc.confluence)
    except Exception as exc:
        raise HTTPException(502, f"Refresh failed: {exc}") from exc
    audit(session, ctx, "Refreshed knowledge", detail=", ".join(f"{v} {k}" for k, v in counts.items()))
    return counts


# ---------- audit ----------

@router.get("/audit")
def audit_log(limit: int = 200, ctx: Ctx = CtxDep, session: Session = SessionDep) -> list[AuditEntry]:
    return list(session.exec(select(AuditEntry).where(AuditEntry.project_id == ctx.project_id)
                             .order_by(AuditEntry.ts.desc()).limit(limit)).all())
