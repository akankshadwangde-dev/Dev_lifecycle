"""Roles, their capabilities, and who may decide at each approval gate."""

ROLES: dict[str, dict] = {
    "developer": {
        "label": "Developer",
        "can": {"view_code", "edit_code", "accept_recommendation", "request_plan", "submit_pages"},
    },
    "ams": {
        "label": "AMS consultant",
        "can": {"view_code", "view_prod", "accept_recommendation", "resolve_no_code", "submit_pages"},
    },
    "lead": {
        "label": "Tech lead",
        "can": {
            "view_code", "edit_code", "accept_recommendation", "resolve_no_code",
            "approve_plan", "publish_pages", "approve_models",
        },
    },
    "architect": {
        "label": "Solution architect",
        "can": {"view_code", "accept_recommendation", "approve_design"},
    },
    "functional": {"label": "Functional consultant", "can": set()},
    "pm": {"label": "Project manager", "can": set()},
    "admin": {
        "label": "Admin",
        "can": {"manage_models", "manage_connections", "manage_knowledge"},
    },
}

# gate -> action -> capabilities, any one of which allows the action
GATES: dict[str, dict[str, set[str]]] = {
    "recommendation": {
        "approve": {"accept_recommendation"},
        "no_code": {"resolve_no_code"},
        "revise": {"accept_recommendation"},
    },
    "plan": {
        "approve": {"approve_plan", "approve_design"},
        "revise": {"approve_plan", "approve_design", "request_plan"},
    },
    "change": {
        "approve": {"edit_code"},
        "revise": {"edit_code"},
    },
    "pages": {
        "approve": {"publish_pages"},
        "revise": {"publish_pages", "submit_pages"},
    },
}


def can(role: str, capability: str) -> bool:
    return capability in ROLES.get(role, {}).get("can", set())


def may_decide(role: str, gate: str, action: str) -> bool:
    needed = GATES.get(gate, {}).get(action)
    return bool(needed) and any(can(role, c) for c in needed)


def gate_actions(role: str, gate: str) -> list[dict]:
    return [{"action": a, "allowed": may_decide(role, gate, a)} for a in GATES.get(gate, {})]


def deciders(gate: str, action: str = "approve") -> list[str]:
    """Labels of the roles that may take an action, for 'waiting for ...' messages."""
    return [r["label"] for key, r in ROLES.items() if may_decide(key, gate, action)]
