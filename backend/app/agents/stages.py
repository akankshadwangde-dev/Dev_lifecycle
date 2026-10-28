"""One function per lifecycle stage. Each takes the project's Services and the flow state and returns
that stage's output. Model calls go through the gateway; everything the model saw is kept as sources."""

import difflib

from ..connectors.sap_profiles import SYNTAX_RULES
from ..textutil import base_object, find_objects, parse_json
from .common import SYSTEM, compact, feedback, item_header, outputs


def _ask(svc, state, stage: str, prompt: str) -> tuple[dict, str]:
    result = svc.gateway.complete(stage, SYSTEM, prompt, data_level="code",
                                  preferred_id=state.get("preferred_model_id"))
    return parse_json(result.text), result.model_name


def _objects(state: dict) -> list[str]:
    names = outputs(state).get("intake", {}).get("objects", [])
    return list(dict.fromkeys(base_object(n) for n in names))


def intake(svc, state) -> dict:
    item = state["item"]
    objects = item.get("objects") or find_objects(f"{item['title']}\n{item.get('description', '')}")
    return {"kind": item["kind"], "objects": objects, "priority": item.get("priority", ""),
            "source": item.get("source", "")}


def knowledge(svc, state) -> dict:
    item = state["item"]
    query = f"{item['title']} {item.get('description', '')}"
    sources = svc.knowledge.search(svc.project_id, query, limit=6)
    if svc.confluence is not None:
        try:
            known = {s["ref"] for s in sources}
            sources += [{**h, "source": "confluence", "body": h.get("excerpt", ""), "score": None}
                        for h in svc.confluence.search(item["title"], limit=4) if h["ref"] not in known]
        except Exception:
            pass  # the local index is enough to continue
    if svc.sap is not None:
        for name in _objects(state)[:3]:
            code = svc.sap.read_source(name)
            if code:
                sources.append({"source": "sap", "ref": name, "title": f"{name} (current code)",
                                "body": code[:5000], "excerpt": f"{len(code.splitlines())} lines",
                                "url": "", "updated": "", "score": None})

    listing = "\n\n".join(f"[{s['ref']}] {s['title']} ({s['source']})\n{s['body']}" for s in sources)
    prompt = (
        item_header(item)
        + f"\nSOURCES (Confluence pages, resolved tickets, current SAP code):\n{listing or 'none found'}\n"
        + feedback(state, "knowledge")
        + "\nFind the most likely cause (or, for a new requirement, the best approach) and recommend steps. "
          "Prefer solutions already proven in the sources. Return JSON: "
          '{"cause": str, "confidence": "high"|"medium"|"low", "needs_code": bool, "estimate": str, '
          '"steps": [str], "avoid": str, "sources_used": [source refs you relied on]}'
    )
    answer, model = _ask(svc, state, "knowledge", prompt)
    used = [r for r in answer.get("sources_used", []) if any(s["ref"] == r for s in sources)]
    for s in sources:
        s.pop("body", None)
        s["used"] = s["ref"] in used
    sources.sort(key=lambda s: not s["used"])
    return {
        "cause": answer.get("cause", ""),
        "confidence": answer.get("confidence", "low"),
        "needs_code": bool(answer.get("needs_code", True)),
        "estimate": answer.get("estimate", ""),
        "steps": answer.get("steps", []),
        "avoid": answer.get("avoid", ""),
        "sources": sources,
        "model": model,
    }


def impact(svc, state) -> dict:
    item = state["item"]
    objects = []
    for name in _objects(state)[:5]:
        objects.append({
            "name": name,
            "callers": svc.sap.where_used(name) if svc.sap else [],
            "transports": svc.sap.open_transports(name) if svc.sap else [],
            "tests": svc.sap.unit_tests(name) if svc.sap else [],
        })
    prompt = (
        item_header(item)
        + f"\nRECOMMENDATION:\n{compact(outputs(state).get('knowledge', {}))}\n"
        + f"\nAFFECTED OBJECTS (callers, open transports, existing unit tests):\n{compact(objects)}\n"
        + "\nAssess the regression risk of the recommended change. Return JSON: "
          '{"risk": "low"|"medium"|"high", "summary": str, "notes": [str]}'
    )
    answer, model = _ask(svc, state, "impact", prompt)
    return {"objects": objects, "risk": answer.get("risk", "medium"), "summary": answer.get("summary", ""),
            "notes": answer.get("notes", []), "model": model}


def plan(svc, state) -> dict:
    item = state["item"]
    kind_hint = ("List RICEFW objects (type R, I, C, E, F or W)." if item["kind"] == "new"
                 else "List the objects to change (type = SAP object type such as CLAS, PROG, FUGR).")
    prompt = (
        item_header(item)
        + f"\nRECOMMENDATION:\n{compact(outputs(state).get('knowledge', {}))}\n"
        + f"\nIMPACT:\n{compact(outputs(state).get('impact', {}))}\n"
        + feedback(state, "plan")
        + f"\n{kind_hint} Include documentation and configuration steps as their own items. Return JSON: "
          '{"items": [{"action": "modify"|"new"|"config"|"docs", "object": str, "type": str, '
          '"change": str, "basis": str, "estimate_h": number}]}'
    )
    answer, model = _ask(svc, state, "plan", prompt)
    items = answer.get("items", [])
    return {"items": items, "total_h": round(sum(float(i.get("estimate_h") or 0) for i in items), 1),
            "model": model}


def _diff(before: str, after: str) -> list[dict]:
    lines = []
    for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=3):
        if line.startswith(("---", "+++")):
            continue
        tag = line[:1] if line[:1] in "+-@" else " "
        lines.append({"t": tag, "text": line[1:] if tag != "@" else line})
    return lines


def build(svc, state) -> dict:
    item = state["item"]
    target = svc.sap_target()
    planned = [i for i in outputs(state).get("plan", {}).get("items", []) if i.get("action") in ("modify", "new")]
    names = list(dict.fromkeys(base_object(i["object"]) for i in planned))
    current = {n: (svc.sap.read_source(n) if svc.sap else None) or "" for n in names}
    prompt = (
        item_header(item)
        + f"\nTARGET SYSTEM: SAP_BASIS {target['basis_release']}, profile {target['profile']['label']}."
        + f"\nSYNTAX RULES: {SYNTAX_RULES[target['syntax']]}\n"
        + f"\nAPPROVED PLAN:\n{compact(planned)}\n"
        + f"\nRECOMMENDATION:\n{compact(outputs(state).get('knowledge', {}))}\n"
        + "\nCURRENT SOURCE (empty means the object is new):\n"
        + "\n\n".join(f"=== {n} ===\n{src}" for n, src in current.items())
        + feedback(state, "build")
        + "\nWrite the complete new source for each object. Change only what the plan requires and keep "
          "everything else exactly as it is. Return JSON: "
          '{"objects": [{"name": str, "new_source": str, "notes": [str]}]}'
    )
    answer, model = _ask(svc, state, "build", prompt)
    objects = []
    for obj in answer.get("objects", []):
        name = obj.get("name", "").upper()
        before, after = current.get(name, ""), obj.get("new_source", "")
        diff = _diff(before, after)
        objects.append({
            "name": name, "is_new": not before, "before": before, "after": after, "diff": diff,
            "added": sum(1 for d in diff if d["t"] == "+"), "removed": sum(1 for d in diff if d["t"] == "-"),
            "notes": obj.get("notes", []),
        })
    return {"objects": objects, "target": target, "model": model}


def document(svc, state) -> dict:
    item = state["item"]
    done = outputs(state)
    summary = {
        "resolution": state.get("resolution", "code"),
        "recommendation": {k: done.get("knowledge", {}).get(k) for k in ("cause", "steps", "avoid")},
        "plan": done.get("plan", {}).get("items", []),
        "changed_objects": [{"name": o["name"], "added": o["added"], "removed": o["removed"], "notes": o["notes"]}
                            for o in done.get("build", {}).get("objects", [])],
    }
    prompt = (
        item_header(item)
        + f"\nWHAT WAS DONE:\n{compact(summary)}\n"
        + feedback(state, "document")
        + "\nDraft Confluence pages so the next person with a similar problem finds the answer. For incidents "
          "use sections Symptom, Root cause, Solution (or Resolution), Objects and transports, How to spot "
          "this again. For new development write a design page. Use 'update' mode for an existing design "
          "page from the sources. Return JSON: "
          '{"pages": [{"mode": "create"|"update", "space": str, "parent": str, "title": str, '
          '"labels": [str], "sections": [{"heading": str, "body": str or [str]}]}]}'
    )
    answer, model = _ask(svc, state, "document", prompt)
    return {"pages": answer.get("pages", []), "model": model}


def publish(svc, state) -> dict:
    """Publish approved pages and feed them back into the knowledge index (the learning loop)."""
    item = state["item"]
    results = []
    for page in outputs(state).get("document", {}).get("pages", []):
        if svc.confluence is not None and getattr(svc.confluence, "can_publish", False):
            res = svc.confluence.publish(page)
        else:
            res = {"ref": f"DRAFT-{item['key']}", "url": "", "simulated": True}
        body = "\n".join(
            f"{s.get('heading', '')}: " + (" ".join(s["body"]) if isinstance(s.get("body"), list) else str(s.get("body", "")))
            for s in page.get("sections", [])
        )
        svc.knowledge.upsert(svc.project_id, "studio", res["ref"], page.get("title", ""), body, res.get("url", ""))
        results.append({"title": page.get("title", ""), "space": page.get("space", ""), **res})
    return {"pages": results}
