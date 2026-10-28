"""Small text helpers shared by connectors and agents."""

import html
import json
import re

OBJECT_NAME = re.compile(r"\b[ZY][A-Z0-9_]{3,29}(?:=>[A-Z0-9_]+)?\b")


def find_objects(text: str) -> list[str]:
    """Custom SAP object names (Z*/Y*) mentioned in free text, in order of first mention."""
    seen: list[str] = []
    for name in OBJECT_NAME.findall(text.upper()):
        if name not in seen:
            seen.append(name)
    return seen


def base_object(name: str) -> str:
    """ZCL_FOO=>BAR -> ZCL_FOO"""
    return name.split("=>")[0].strip()


def html_to_text(markup: str) -> str:
    text = re.sub(r"<(br|/p|/li|/h\d|/tr)[^>]*>", "\n", markup or "", flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def adf_to_text(node) -> str:
    """Flatten Atlassian Document Format (Jira Cloud descriptions) to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(n) for n in node)
    if node.get("type") == "text":
        return node.get("text", "")
    inner = adf_to_text(node.get("content", []))
    return inner + ("\n" if node.get("type") in {"paragraph", "heading", "listItem"} else "")


def parse_json(text: str) -> dict:
    """Extract the first JSON object from a model reply (tolerates ```json fences and prose around it)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    candidate = fenced.group(1) if fenced else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("The model did not return JSON")
    return json.loads(candidate[start:end + 1])
