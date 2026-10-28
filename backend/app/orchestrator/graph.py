"""The lifecycle as a LangGraph state graph.

intake -> knowledge -> [recommendation gate] -> impact -> plan -> [plan gate] -> build -> [change gate]
       -> document -> [pages gate] -> publish

The recommendation gate can skip straight to document ("no code needed"). Every gate can send its
stage back for revision with a comment. Gates pause the graph with interrupt(); the checkpointer keeps
the paused flow until someone decides, however long that takes.
"""

import operator
from typing import Annotated, Callable, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ..agents import stages
from ..services import Services


def _merge(a: dict, b: dict) -> dict:
    return {**(a or {}), **(b or {})}


class FlowState(TypedDict, total=False):
    project_id: int
    item: dict
    preferred_model_id: int | None
    stage: str
    resolution: str  # "code" | "no_code"
    outputs: Annotated[dict, _merge]  # stage name -> that stage's output
    feedback: dict  # stage name -> reviewer comment for the next attempt
    history: Annotated[list[dict], operator.add]  # gate decisions


# gate -> the stage it reviews (and re-runs on "revise")
GATES = {"recommendation": "knowledge", "plan": "plan", "change": "build", "pages": "document"}


def _stage(name: str, fn: Callable) -> Callable:
    def node(state: FlowState) -> dict:
        svc = Services(state["project_id"])
        return {"outputs": {name: fn(svc, state)}, "stage": name}

    return node


def _gate(name: str) -> Callable:
    def node(state: FlowState) -> dict:
        decision = interrupt({"gate": name})
        update: dict = {"history": [{"gate": name, **decision}]}
        if decision.get("action") == "revise":
            update["feedback"] = {**(state.get("feedback") or {}), GATES[name]: decision.get("comment", "")}
        if name == "recommendation" and decision.get("action") in ("approve", "no_code"):
            update["resolution"] = "no_code" if decision["action"] == "no_code" else "code"
        if decision.get("model_id") is not None:
            update["preferred_model_id"] = decision["model_id"]
        return update

    return node


def _route(on_approve: str, on_revise: str, on_no_code: str | None = None) -> Callable:
    def route(state: FlowState) -> str:
        action = state["history"][-1]["action"]
        if action == "no_code" and on_no_code:
            return on_no_code
        return on_approve if action == "approve" else on_revise

    return route


def build_graph(checkpointer):
    g = StateGraph(FlowState)
    for name in ("intake", "knowledge", "impact", "plan", "build", "document", "publish"):
        g.add_node(name, _stage(name, getattr(stages, name)))
    for gate in GATES:
        g.add_node(f"gate_{gate}", _gate(gate))

    g.add_edge(START, "intake")
    g.add_edge("intake", "knowledge")
    g.add_edge("knowledge", "gate_recommendation")
    g.add_conditional_edges("gate_recommendation", _route("impact", "knowledge", on_no_code="document"),
                            ["impact", "knowledge", "document"])
    g.add_edge("impact", "plan")
    g.add_edge("plan", "gate_plan")
    g.add_conditional_edges("gate_plan", _route("build", "plan"), ["build", "plan"])
    g.add_edge("build", "gate_change")
    g.add_conditional_edges("gate_change", _route("document", "build"), ["document", "build"])
    g.add_edge("document", "gate_pages")
    g.add_conditional_edges("gate_pages", _route("publish", "document"), ["publish", "document"])
    g.add_edge("publish", END)
    return g.compile(checkpointer=checkpointer)
