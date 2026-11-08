"""Route finder: which handbook workflow fits an input and a goal.

Reads ``assets/data/routes.json``, the same rules the HTML Toolkit uses through
``CadCalc.recommendRoute`` in ``assets/js/cadcalc.js``. The algorithm is kept
identical in both languages and a Node test compares them for every pair:

1. a goal with a ``lead`` workflow (an exact mount, a holder) goes first;
2. then the pair override's workflow, or the input's base workflow;
3. then any ``also`` workflows from the goal and the pair, without repeats.

A recommendation is a starting point from handbook section 1, not a promise
that the chosen route will reach a required accuracy.
"""

from __future__ import annotations

import json
from pathlib import Path

ROUTES_FILE = Path(__file__).resolve().parent.parent / "assets" / "data" / "routes.json"


def load_routes(path: Path | str = ROUTES_FILE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _unique(items):
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def recommend(routes: dict, input_id: str, goal_id: str) -> dict:
    base = routes["by_input"].get(input_id)
    goal = routes["by_goal"].get(goal_id)
    if base is None:
        raise ValueError(f"unknown input {input_id!r}; expected one of: {', '.join(routes['by_input'])}")
    if goal is None:
        raise ValueError(f"unknown goal {goal_id!r}; expected one of: {', '.join(routes['by_goal'])}")
    pair = routes.get("pairs", {}).get(f"{input_id}|{goal_id}", {})
    sequence = _unique([w for w in [goal.get("lead"), pair.get("workflow") or base["workflow"],
                                    *goal.get("also", []), *pair.get("also", [])] if w])
    return {
        "input": input_id,
        "goal": goal_id,
        "workflows": sequence,
        "sections": [routes["workflows"][w]["section"] for w in sequence],
        "sources": _unique([*base["sources"], *goal["sources"]]),
        "checks": list(goal.get("checks", [])),
        "warnings": [pair["warning"]] if pair.get("warning") else [],
        "calculators": _unique([c for w in sequence for c in routes["workflows"][w]["calculators"]]),
    }


def all_recommendations(routes: dict) -> list[dict]:
    return [recommend(routes, i["id"], g["id"]) for i in routes["inputs"] for g in routes["goals"]]
