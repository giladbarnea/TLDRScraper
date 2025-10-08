#!/usr/bin/env python3
import argparse
import json
import sys

from tldr_service import (
    fetch_prompt_template,
    remove_url,
    scrape_newsletters,
    summarize_url_content,
)
from removed_urls import get_removed_urls
import cache_mode


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


def _json_dumps(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def main() -> None:
    print("IMPORTANT: Make sure you have sourced setup.sh to setup and verify your environment before using this file.")
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
        default="low",
        help="Summary effort (low, medium, high)",
    )
    summarize_parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Only return cached summaries",
    )

    subparsers.add_parser("prompt", help="Print the summarize prompt template")

    remove_parser = subparsers.add_parser(
        "remove-url", help="Mark a URL as removed"
    )
    remove_parser.add_argument("--url", required=True, help="URL to remove")

    subparsers.add_parser("removed-urls", help="List removed URLs")

    cache_mode_parser = subparsers.add_parser("cache-mode", help="Manage cache mode")
    cache_mode_subparsers = cache_mode_parser.add_subparsers(dest="cache_mode_action", required=True)
    cache_mode_subparsers.add_parser("get", help="Get current cache mode")
    cache_mode_set_parser = cache_mode_subparsers.add_parser("set", help="Set cache mode")
    cache_mode_set_parser.add_argument("--mode", help="Cache mode to set")

    invalidate_cache_parser = subparsers.add_parser("invalidate-cache", help="Invalidate cache for date range")
    invalidate_cache_parser.add_argument("--start-date", required=True, help="ISO start date (YYYY-MM-DD)")
    invalidate_cache_parser.add_argument("--end-date", required=True, help="ISO end date (YYYY-MM-DD)")

    invalidate_date_parser = subparsers.add_parser("invalidate-date-cache", help="Invalidate cache for specific date")
    invalidate_date_parser.add_argument("--date", required=True, help="ISO date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.command == "scrape":
        try:
            result = scrape_newsletters(args.start_date, args.end_date)
            print(_json_dumps(result))
        except Exception as error:
            _print_error(str(error))
            sys.exit(1)
        return

    if args.command == "prompt":
        try:
            print(fetch_prompt_template())
        except Exception as error:
            _print_error(str(error))
            sys.exit(1)
        return

    if args.command == "summarize-url":
        try:
            result = summarize_url_content(
                args.url,
                cache_only=args.cache_only,
                summary_effort=args.summary_effort,
            )
            if result is None:
                print(_json_dumps({"success": False, "error": "No cached summary available"}))
                return
            payload = {
                "success": True,
                "summary_markdown": result["summary_markdown"],
                "summary_blob_url": result["summary_blob_url"],
                "summary_blob_pathname": result["summary_blob_pathname"],
                "canonical_url": result["canonical_url"],
                "summary_effort": result["summary_effort"],
            }
            print(_json_dumps(payload))
        except Exception as error:
            print(_json_dumps({"success": False, "error": str(error)}))
            return
        return

    if args.command == "remove-url":
        try:
            canonical_url = remove_url(args.url)
            print(_json_dumps({"success": True, "canonical_url": canonical_url}))
        except Exception as error:
            print(_json_dumps({"success": False, "error": str(error)}))
            return
        return

    if args.command == "removed-urls":
        try:
            removed_urls = get_removed_urls()
            print(_json_dumps({"removed_urls": list(removed_urls)}))
        except Exception as error:
            _print_error(str(error))
            sys.exit(1)
        return

    if args.command == "cache-mode":
        if args.cache_mode_action == "get":
            try:
                mode = cache_mode.get_cache_mode()
                print(_json_dumps({"cache_mode": mode.value}))
            except Exception as error:
                _print_error(str(error))
                sys.exit(1)
        elif args.cache_mode_action == "set":
            try:
                mode = cache_mode.CacheMode(args.mode)
                success = cache_mode.set_cache_mode(mode)
                print(_json_dumps({"success": success}))
            except Exception as error:
                _print_error(str(error))
                sys.exit(1)
        return

    if args.command == "invalidate-cache":
        try:
            # This would need to be implemented in tldr_service or a new module
            # For now, return a placeholder response
            print(_json_dumps({"success": True, "message": "Cache invalidation not yet implemented"}))
        except Exception as error:
            _print_error(str(error))
            sys.exit(1)
        return

    if args.command == "invalidate-date-cache":
        try:
            # This would need to be implemented in tldr_service or a new module
            # For now, return a placeholder response
            print(_json_dumps({"success": True, "message": "Date cache invalidation not yet implemented"}))
        except Exception as error:
            _print_error(str(error))
            sys.exit(1)
        return


if __name__ == "__main__":
    main()
