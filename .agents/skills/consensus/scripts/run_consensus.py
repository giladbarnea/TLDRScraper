#!/usr/bin/env python3
"""Run a multi-model consensus roundtrip for a single user question."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import os
import re
from enum import StrEnum
from typing import Literal

import anthropic
import openai
from google import genai
from google.genai import types

MODEL_KEYS = ("claude", "gpt", "gemini")
MODEL_NAMES = {
    "claude": "Claude",
    "gpt": "GPT",
    "gemini": "Gemini",
}
DEFAULT_MAX_TURNS = 4
CONCLUSION_REGEX = re.compile(r"<conclusion>(.*?)</conclusion>", re.DOTALL)
SYSTEM_PROMPT = """\
You are participating in a structured discussion with two other AI assistants.
Each of you is a different model provider. Your name is {name}.

Goal: produce the most truthful, useful final answer for the user.
- Be concise and specific.
- Critically evaluate other responses.
- Agree when agreement is warranted.
- Disagree clearly when needed.

If true convergence is reached, wrap the final user-facing answer in
<conclusion>...</conclusion>.
Only emit <conclusion> when consensus is real.
"""


class ThinkingLevel(StrEnum):
    LOW = "low"
    HIGH = "high"

    @property
    def openai_effort(self) -> str:
        return "xhigh" if self is ThinkingLevel.HIGH else "low"

    @property
    def anthropic_effort(self) -> str:
        return self.value

    @property
    def gemini_level(self) -> str:
        return self.value


@dataclasses.dataclass(frozen=True)
class ConsensusConfig:
    anthropic_model: str
    openai_model: str
    gemini_model: str
    thinking_level: ThinkingLevel
    max_turns: int


@dataclasses.dataclass(frozen=True)
class ConsensusResult:
    answer: str
    reached_consensus: bool
    stop_reason: Literal["consensus", "max_turns"]
    rounds: list[dict[str, str]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", type=str, help="The user prompt to evaluate")
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    parser.add_argument("--thinking", choices=["low", "high"], default="low")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args()


def load_config(args: argparse.Namespace) -> ConsensusConfig:
    return ConsensusConfig(
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
        thinking_level=ThinkingLevel(args.thinking),
        max_turns=args.max_turns,
    )


def build_system_prompt(name: str) -> str:
    return SYSTEM_PROMPT.format(name=name)


def extract_conclusion(responses: dict[str, str]) -> str | None:
    for key in MODEL_KEYS:
        match = CONCLUSION_REGEX.search(responses[key])
        if match:
            return match.group(1).strip()
    return None


def format_round_summary(responses: dict[str, str]) -> str:
    return "\n\n---\n\n".join(
        f"[{MODEL_NAMES[key]}]:\n{responses[key]}" for key in MODEL_KEYS
    )


async def ask_claude(
    client: anthropic.AsyncAnthropic,
    system_prompt: str,
    messages: list[dict[str, str]],
    config: ConsensusConfig,
) -> str:
    request_kwargs: dict[str, object] = {
        "model": config.anthropic_model,
        "system": system_prompt,
        "messages": messages,
        "max_tokens": 16_000,
    }
    if config.thinking_level is ThinkingLevel.HIGH:
        request_kwargs["thinking"] = {"type": "adaptive"}
        request_kwargs["output_config"] = {"effort": config.thinking_level.anthropic_effort}

    response = await client.messages.create(**request_kwargs)
    for block in response.content:
        if block.type == "text":
            return block.text
    return response.content[0].text


async def ask_gpt(
    client: openai.AsyncOpenAI,
    system_prompt: str,
    messages: list[dict[str, str]],
    config: ConsensusConfig,
) -> str:
    response = await client.chat.completions.create(
        model=config.openai_model,
        messages=[{"role": "developer", "content": system_prompt}] + messages,
        reasoning_effort=config.thinking_level.openai_effort,
        max_completion_tokens=16_000,
    )
    return response.choices[0].message.content or ""


async def ask_gemini(
    client: genai.Client,
    system_prompt: str,
    messages: list[dict[str, str]],
    config: ConsensusConfig,
) -> str:
    contents: list[types.Content] = []
    for message in messages:
        role = "user" if message["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=message["content"])],
            )
        )

    response = await client.aio.models.generate_content(
        model=config.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            thinking_config=types.ThinkingConfig(
                thinking_level=config.thinking_level.gemini_level
            ),
        ),
    )
    return response.text


async def run_consensus(question: str, config: ConsensusConfig) -> ConsensusResult:
    histories = {
        key: [{"role": "user", "content": question}]
        for key in MODEL_KEYS
    }
    systems = {key: build_system_prompt(MODEL_NAMES[key]) for key in MODEL_KEYS}
    anthropic_client = anthropic.AsyncAnthropic()
    openai_client = openai.AsyncOpenAI()
    gemini_client = genai.Client()
    rounds: list[dict[str, str]] = []
    responses = {key: "" for key in MODEL_KEYS}

    for _turn in range(1, config.max_turns + 1):
        results = await asyncio.gather(
            ask_claude(anthropic_client, systems["claude"], histories["claude"], config),
            ask_gpt(openai_client, systems["gpt"], histories["gpt"], config),
            ask_gemini(gemini_client, systems["gemini"], histories["gemini"], config),
            return_exceptions=True,
        )

        for key, result in zip(MODEL_KEYS, results, strict=True):
            responses[key] = str(result) if isinstance(result, Exception) else result

        rounds.append(dict(responses))
        conclusion = extract_conclusion(responses)
        if conclusion:
            return ConsensusResult(
                answer=conclusion,
                reached_consensus=True,
                stop_reason="consensus",
                rounds=rounds,
            )

        next_user_message = (
            "Here is what everyone said this round:\n\n"
            f"{format_round_summary(responses)}"
        )
        for key in MODEL_KEYS:
            histories[key].append({"role": "assistant", "content": responses[key]})
            histories[key].append({"role": "user", "content": next_user_message})

    final_answer = (
        "No consensus was reached. Last-round responses:\n\n"
        f"{format_round_summary(responses)}"
    )
    return ConsensusResult(
        answer=final_answer,
        reached_consensus=False,
        stop_reason="max_turns",
        rounds=rounds,
    )


def main() -> None:
    args = parse_args()
    config = load_config(args)
    result = asyncio.run(run_consensus(args.question, config))

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
