#!/usr/bin/env python3
"""Readiness and opt-in real inference checks through production code. Never pulls models."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import assistant, creative


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe", action="store_true", help="Run synthetic assistant/creative prompts"
    )
    parser.add_argument("--model", help="Use this installed local chat model")
    parser.add_argument("--output", type=Path, help="Write a JSON receipt to this file")
    args = parser.parse_args()
    status = assistant.assistant_status()
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "status": status,
        "probes": [],
        "inference_verified": False,
    }
    try:
        report["ollama_version"] = assistant.ollama_request("GET", "/api/version").get("version")
    except assistant.AssistantError:
        report["ollama_version"] = None
    model = args.model or status["recommended_model"]
    code = 0 if status["running"] and model else 1
    if args.model and not any(item["name"] == model for item in status["models"]):
        code = 1
        report["error"] = "Requested model is not a verified local chat model."
    elif args.probe and not code:
        try:
            report["probes"].append(
                {
                    "tool": "assistant",
                    "reply": assistant.chat(
                        assistant.AssistantRequest(
                            model=model,
                            question="What should I measure before building a flat part from a photo?",
                        )
                    ),
                }
            )
            for tool in creative.TOOLS:
                report["probes"].append(
                    {
                        "tool": tool,
                        "reply": creative.run_tool(
                            creative.CreativeRequest(
                                model=model,
                                tool=tool,
                                brief="A modular desk organizer with removable trays.",
                                constraints="Use a small test piece first. No dimensions measured yet.",
                            )
                        ),
                    }
                )
            report["inference_verified"] = True
        except assistant.AssistantError as exc:
            code = 1
            report["error"] = exc.detail
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
