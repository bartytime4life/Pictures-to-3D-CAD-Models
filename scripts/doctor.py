#!/usr/bin/env python3
"""Report app readiness without installing packages, downloading models or running inference."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.runtime_status import summarize_runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print a structured report")
    parser.add_argument(
        "--skip-ai", action="store_true", help="Skip the local Ollama metadata check"
    )
    args = parser.parse_args()
    report = summarize_runtime(include_development=True, check_ai=not args.skip_ai)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("App setup is ready." if report["ready"] else "App setup needs attention.")
        for check in report["checks"]:
            print(f"\n[{check['status'].upper()}] {check['label']}: {check['detail']}")
            if action := check.get("action"):
                print(f"  {action['label']}: {action['command']}")
        print("\nThis check does not install anything, execute CAD, or generate AI responses.")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
