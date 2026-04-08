#!/usr/bin/env python3
"""Run a multi-model consensus roundtrip for a single user question."""

from __future__ import annotations

import argparse
import dataclasses
import json

import consensus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", type=str, help="The user prompt to evaluate")
    parser.add_argument("--max-turns", type=int, default=consensus.DEFAULT_MAX_TURNS)
    parser.add_argument("--thinking", choices=["low", "high"], default="low")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = consensus.load_config(thinking=args.thinking, max_turns=args.max_turns)
    result = consensus.run_question(args.question, config)

    if args.json_output:
        print(json.dumps(dataclasses.asdict(result), indent=2))
        return

    print("=== Consensus answer ===")
    print(result.answer)
    print("\n=== Metadata ===")
    print(f"reached_consensus: {result.reached_consensus}")
    print(f"stop_reason: {result.stop_reason}")
    print(f"rounds: {len(result.rounds)}")


if __name__ == "__main__":
    main()
