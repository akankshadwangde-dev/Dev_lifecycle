"""Request context. Phase 1 reads user and role from headers; SSO (OIDC) replaces this in Phase 2."""

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from .db import get_session
from .models import AuditEntry
from .roles import ROLES, can


@dataclass
class Ctx:
    user: str
    role: str
    project_id: int
    model_id: int | None


def get_ctx(
    x_studio_user: str = Header("demo.user"),
    x_studio_role: str = Header("developer"),
    x_studio_project: int = Header(1),
    x_studio_model: str | None = Header(None),
) -> Ctx:
    if x_studio_role not in ROLES:
        raise HTTPException(400, f"Unknown role '{x_studio_role}'")
    model_id = int(x_studio_model) if x_studio_model and x_studio_model.isdigit() else None
    return Ctx(x_studio_user, x_studio_role, x_studio_project, model_id)


def require(capability: str):
    """Use as a parameter default: `ctx: Ctx = require("manage_models")`."""

    def check(ctx: Ctx = Depends(get_ctx)) -> Ctx:
        if not can(ctx.role, capability):
            raise HTTPException(403, f"{ROLES[ctx.role]['label']} cannot do this")
        return ctx

    return Depends(check)


def audit(session: Session, ctx: Ctx, action: str, item_key: str = "", detail: str = "", model: str = "") -> None:
    session.add(AuditEntry(project_id=ctx.project_id, user=ctx.user, role=ctx.role, action=action,
                           item_key=item_key, detail=detail, model=model))
    session.commit()


SessionDep = Depends(get_session)
CtxDep = Depends(get_ctx)
