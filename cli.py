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


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


def _json_dumps(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


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
                _print_error("No cached summary available")
                sys.exit(1)
            payload = {
                "summary_markdown": result["summary_markdown"],
                "summary_blob_url": result["summary_blob_url"],
                "summary_blob_pathname": result["summary_blob_pathname"],
                "canonical_url": result["canonical_url"],
                "summary_effort": result["summary_effort"],
            }
            print(_json_dumps(payload))
        except Exception as error:
            _print_error(str(error))
            sys.exit(1)
        return

    if args.command == "remove-url":
        try:
            canonical_url = remove_url(args.url)
            print(_json_dumps({"canonical_url": canonical_url}))
        except Exception as error:
            _print_error(str(error))
            sys.exit(1)
        return


if __name__ == "__main__":
    main()
