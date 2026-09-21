#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from guard_decision import run_decision
from guard_probe import run_probe
from guard_reporter import run_digest
from guard_store import read_json


def main() -> int:
    parser = argparse.ArgumentParser(description="TalentFlow stability guard agent")
    parser.add_argument(
        "command",
        choices=["probe-critical", "probe-full", "decide", "digest", "status"],
    )
    args = parser.parse_args()

    if args.command == "probe-critical":
        print(json.dumps(run_probe("critical"), ensure_ascii=False))
        return 0
    if args.command == "probe-full":
        print(json.dumps(run_probe("full"), ensure_ascii=False))
        return 0
    if args.command == "decide":
        print(json.dumps(run_decision(), ensure_ascii=False))
        return 0
    if args.command == "digest":
        print(json.dumps(run_digest(), ensure_ascii=False))
        return 0

    status = {
        "probe": read_json("probe_critical_latest.json", {}),
        "decision": read_json("decision_state.json", {}),
        "digest": read_json("digest_latest.json", {}),
    }
    print(json.dumps(status, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

