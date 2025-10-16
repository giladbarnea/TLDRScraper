#!/usr/bin/env python3
"""
IMPORTANT: Make sure you have sourced setup.sh to setup and verify your environment before using this file.
"""

import argparse
import json
import sys
from typing import Callable, Any

import requests

import tldr_app


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


def _json_dumps(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _value_error_payload(error: Exception) -> dict:
    return {"success": False, "error": str(error)}


def _network_error_payload(error: requests.RequestException) -> dict:
    return {"success": False, "error": f"Network error: {repr(error)}"}


def _unexpected_error_payload(error: Exception) -> dict:
    return {"success": False, "error": repr(error)}


def _run_json_command(
    command: Callable[[], Any],
    *,
    error_handlers: tuple[
        tuple[type[Exception], Callable[[Exception], dict]],
        ...,
    ] = (),
    default_error_handler: Callable[[Exception], dict] | None = None,
    exit_code: int | None = 1,
) -> None:
    try:
        result = command()
    except Exception as error:
        for exception_type, handler in error_handlers:
            if isinstance(error, exception_type):
                print(_json_dumps(handler(error)))
                if exit_code is not None:
                    sys.exit(exit_code)
                return

        if default_error_handler is not None:
            print(_json_dumps(default_error_handler(error)))
            if exit_code is not None:
                sys.exit(exit_code)
            return

        _print_error(str(error))
        if exit_code is not None:
            sys.exit(exit_code)
        return

    print(_json_dumps(result))


def _run_text_command(command: Callable[[], str]) -> None:
    try:
        result = command()
    except Exception as error:
        _print_error(str(error))
        sys.exit(1)

    print(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="TLDR Scraper local CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser("scrape", help="Scrape newsletters")
    scrape_parser.add_argument(
        "--start-date", required=True, help="ISO start date (YYYY-MM-DD)"
    )
    scrape_parser.add_argument(
        "--end-date", required=True, help="ISO end date (YYYY-MM-DD)"
    )

    summarize_parser = subparsers.add_parser(
        "summarize-url", help="Summarize a URL using the existing summarizer"
    )
    summarize_parser.add_argument("--url", required=True, help="URL to summarize")
    summarize_parser.add_argument(
        "--summary-effort",
        default="minimal",
        help="Summary effort (low, medium, high)",
    )
    summarize_parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Only return cached summaries",
    )

    tldr_parser = subparsers.add_parser(
        "tldr-url", help="Create a TLDR of a URL"
    )
    tldr_parser.add_argument("--url", required=True, help="URL to TLDR")
    tldr_parser.add_argument(
        "--summary-effort",
        default="minimal",
        help="Summary effort (low, medium, high)",
    )
    tldr_parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Only return cached TLDRs",
    )

    subparsers.add_parser("prompt", help="Print the summarize prompt template")
    subparsers.add_parser("tldr-prompt", help="Print the TLDR prompt template")

    remove_parser = subparsers.add_parser("remove-url", help="Mark a URL as removed")
    remove_parser.add_argument("--url", required=True, help="URL to remove")

    subparsers.add_parser("removed-urls", help="List removed URLs")

    cache_mode_parser = subparsers.add_parser("cache-mode", help="Manage cache mode")
    cache_mode_subparsers = cache_mode_parser.add_subparsers(
        dest="cache_mode_action", required=True
    )
    cache_mode_subparsers.add_parser("get", help="Get current cache mode")
    cache_mode_set_parser = cache_mode_subparsers.add_parser(
        "set", help="Set cache mode"
    )
    cache_mode_set_parser.add_argument(
        "--cache-mode",
        "--mode",
        dest="cache_mode",
        required=True,
        help="Cache mode to set",
    )

    invalidate_cache_parser = subparsers.add_parser(
        "invalidate-cache", help="Invalidate cache for date range"
    )
    invalidate_cache_parser.add_argument(
        "--start-date", required=True, help="ISO start date (YYYY-MM-DD)"
    )
    invalidate_cache_parser.add_argument(
        "--end-date", required=True, help="ISO end date (YYYY-MM-DD)"
    )

    invalidate_date_parser = subparsers.add_parser(
        "invalidate-date-cache", help="Invalidate cache for specific date"
    )
    invalidate_date_parser.add_argument(
        "--date", required=True, help="ISO date (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    command_handlers: dict[str, Callable[[argparse.Namespace], None]] = {
        "scrape": lambda command_args: _run_json_command(
            lambda: tldr_app.scrape_newsletters(
                command_args.start_date, command_args.end_date
            ),
            error_handlers=((ValueError, _value_error_payload),),
            default_error_handler=_value_error_payload,
        ),
        "prompt": lambda command_args: _run_text_command(
            tldr_app.get_summarize_prompt_template
        ),
        "tldr-prompt": lambda command_args: _run_text_command(
            tldr_app.get_tldr_prompt_template
        ),
        "summarize-url": lambda command_args: _run_json_command(
            lambda: tldr_app.summarize_url(
                command_args.url,
                cache_only=command_args.cache_only,
                summary_effort=command_args.summary_effort,
            ),
            error_handlers=(
                (ValueError, _value_error_payload),
                (requests.RequestException, _network_error_payload),
            ),
            default_error_handler=_unexpected_error_payload,
            exit_code=None,
        ),
        "tldr-url": lambda command_args: _run_json_command(
            lambda: tldr_app.tldr_url(
                command_args.url,
                cache_only=command_args.cache_only,
                summary_effort=command_args.summary_effort,
            ),
            error_handlers=(
                (ValueError, _value_error_payload),
                (requests.RequestException, _network_error_payload),
            ),
            default_error_handler=_unexpected_error_payload,
            exit_code=None,
        ),
        "remove-url": lambda command_args: _run_json_command(
            lambda: tldr_app.remove_url(command_args.url),
            error_handlers=(
                (ValueError, _value_error_payload),
                (RuntimeError, _value_error_payload),
            ),
            default_error_handler=_unexpected_error_payload,
            exit_code=None,
        ),
        "removed-urls": lambda command_args: _run_json_command(
            tldr_app.list_removed_urls,
            default_error_handler=_unexpected_error_payload,
        ),
        "cache-mode": lambda command_args: _run_cache_mode_command(
            command_args
        ),
        "invalidate-cache": lambda command_args: _run_json_command(
            lambda: tldr_app.invalidate_cache_in_date_range(
                command_args.start_date, command_args.end_date
            ),
            error_handlers=((ValueError, _value_error_payload),),
            default_error_handler=_unexpected_error_payload,
        ),
        "invalidate-date-cache": lambda command_args: _run_json_command(
            lambda: tldr_app.invalidate_cache_for_date(command_args.date),
            error_handlers=((ValueError, _value_error_payload),),
            default_error_handler=_unexpected_error_payload,
        ),
    }

    handler = command_handlers.get(args.command)
    if handler is None:
        _print_error(f"Unknown command: {args.command}")
        sys.exit(1)

    handler(args)


def _run_cache_mode_command(args: argparse.Namespace) -> None:
    if args.cache_mode_action == "get":
        _run_json_command(
            tldr_app.get_cache_mode,
            default_error_handler=_unexpected_error_payload,
        )
        return

    if args.cache_mode_action == "set":
        _run_json_command(
            lambda: tldr_app.set_cache_mode(args.cache_mode),
            error_handlers=((ValueError, _value_error_payload),),
            default_error_handler=_unexpected_error_payload,
        )
        return

    _print_error(f"Unknown cache-mode action: {args.cache_mode_action}")
    sys.exit(1)


if __name__ == "__main__":
    main()
