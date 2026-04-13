"""Consensus orchestration shared by the hidden web feature and skill script."""

from __future__ import annotations

import asyncio
import dataclasses
import re
from enum import StrEnum
from typing import Literal

import anthropic
import openai
from google import genai
from google.genai import types

import util

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
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclasses.dataclass(frozen=True)
class ConsensusConfig:
    anthropic_model: str
    openai_model: str
    gemini_model: str
    thinking_level: ThinkingLevel
    max_turns: int


@dataclasses.dataclass(frozen=True)
class RoundResult:
    turn: int
    responses: dict[str, str]


@dataclasses.dataclass(frozen=True)
class ConsensusResult:
    answer: str
    reached_consensus: bool
    stop_reason: Literal["consensus", "max_turns"]
    rounds: list[RoundResult]


def load_config(*, thinking: str = "high", max_turns: int = DEFAULT_MAX_TURNS) -> ConsensusConfig:
    return ConsensusConfig(
        anthropic_model=util.resolve_env_var("ANTHROPIC_MODEL", "claude-opus-4-6"),
        openai_model=util.resolve_env_var("OPENAI_MODEL", "gpt-5.4"),
        gemini_model=util.resolve_env_var("GEMINI_MODEL", "gemini-3.1-pro-preview"),
        thinking_level=ThinkingLevel(thinking),
        max_turns=max_turns,
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
    try:
        response = await client.chat.completions.create(
            model=config.openai_model,
            messages=[{"role": "developer", "content": system_prompt}] + messages,
            reasoning_effort=config.thinking_level.openai_effort,
            max_completion_tokens=16_000,
        )
        return response.choices[0].message.content or ""
    except openai.BadRequestError as error:
        if "messages" not in str(error):
            raise

    input_messages = [{"role": "developer", "content": system_prompt}] + messages
    response = await client.responses.create(
        model=config.openai_model,
        input=input_messages,
        reasoning={"effort": config.thinking_level.openai_effort},
        max_output_tokens=16_000,
    )
    return response.output_text


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


async def run_chat(messages: list[ChatMessage], config: ConsensusConfig) -> ConsensusResult:
    if not messages:
        raise ValueError("At least one message is required.")
    if messages[-1].role != "user":
        raise ValueError("The last message must be a user message.")

    histories = {
        key: [{"role": message.role, "content": message.content} for message in messages]
        for key in MODEL_KEYS
    }
    systems = {key: build_system_prompt(MODEL_NAMES[key]) for key in MODEL_KEYS}
    anthropic_client = anthropic.AsyncAnthropic(api_key=util.resolve_env_var("ANTHROPIC_API_KEY"))
    openai_client = openai.AsyncOpenAI(api_key=util.resolve_env_var("OPENAI_API_KEY"))
    gemini_client = genai.Client(api_key=util.resolve_env_var("GEMINI_API_KEY"))
    rounds: list[RoundResult] = []
    responses = {key: "" for key in MODEL_KEYS}

    for turn in range(1, config.max_turns + 1):
        results = await asyncio.gather(
            ask_claude(anthropic_client, systems["claude"], histories["claude"], config),
            ask_gpt(openai_client, systems["gpt"], histories["gpt"], config),
            ask_gemini(gemini_client, systems["gemini"], histories["gemini"], config),
            return_exceptions=True,
        )

        for key, result in zip(MODEL_KEYS, results, strict=True):
            responses[key] = f"[error: {result}]" if isinstance(result, Exception) else result

        rounds.append(RoundResult(turn=turn, responses=dict(responses)))
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

    return ConsensusResult(
        answer=(
            "No consensus was reached. Last-round responses:\n\n"
            f"{format_round_summary(responses)}"
        ),
        reached_consensus=False,
        stop_reason="max_turns",
        rounds=rounds,
    )


def run_question(question: str, config: ConsensusConfig) -> ConsensusResult:
    return asyncio.run(run_chat([ChatMessage(role="user", content=question)], config))
