import json

SYSTEM = (
    "You are a senior SAP ABAP and SAP CRM consultant working inside ABAP Lifecycle Studio. "
    "Be precise and practical. Use only SAP objects, tables and fields that appear in the provided "
    "sources or exist in standard SAP; never invent custom objects. "
    "Reply with exactly one JSON object in the requested shape and nothing else."
)


def item_header(item: dict) -> str:
    return (
        f"ITEM_KEY: {item['key']}\n"
        f"TITLE: {item['title']}\n"
        f"TYPE: {item['kind']} (new = new requirement, change = change request, incident = AMS incident)\n"
        f"DESCRIPTION:\n{item.get('description', '')}\n"
    )


def feedback(state: dict, stage: str) -> str:
    note = (state.get("feedback") or {}).get(stage)
    if not note:
        return ""
    return f"\nREVIEWER FEEDBACK ON YOUR PREVIOUS ANSWER (address it):\n{note}\n"


def outputs(state: dict) -> dict:
    return state.get("outputs") or {}


def compact(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1)[:6000]
