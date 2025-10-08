#!/usr/bin/env python3

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import util
from tldr_service import (
    ServiceError,
    fetch_prompt_template,
    remove_url as remove_url_from_service,
    scrape_newsletters as scrape_newsletters_from_service,
    summarize_url_content,
)


def _configure_logging() -> None:
    logging.basicConfig(level=util.resolve_env_var("LOG_LEVEL", "INFO"))


def _print_json(payload):
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _handle_error(error: Exception, logger: logging.Logger) -> None:
    util.log(
        f"[tldr_cli] error error={repr(error)}",
        level=logging.ERROR,
        logger=logger,
    )
    if isinstance(error, ServiceError):
        message = {"success": False, "error": str(error)}
    else:
        message = {"success": False, "error": repr(error)}
    json.dump(message, sys.stderr, indent=2)
    sys.stderr.write("\n")
    sys.stderr.flush()


def _scrape(args, logger):
    result = scrape_newsletters_from_service(args.start_date, args.end_date)
    _print_json(result)


def _prompt(args, logger):
    prompt = fetch_prompt_template()
    sys.stdout.write(prompt)
    if not prompt.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()


def _summarize(args, logger):
    result = summarize_url_content(
        args.url,
        cache_only=args.cache_only,
        summary_effort=args.summary_effort,
    )
    _print_json(result)


def _remove(args, logger):
    result = remove_url_from_service(args.url)
    _print_json(result)


def main(argv=None):
    _configure_logging()
    logger = logging.getLogger("tldr_cli")

    parser = argparse.ArgumentParser(description="CLI for TLDR Scraper operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser(
        "scrape", help="Scrape newsletters for a date range"
    )
    scrape_parser.add_argument("start_date", help="Start date (YYYY-MM-DD)")
    scrape_parser.add_argument("end_date", help="End date (YYYY-MM-DD)")
    scrape_parser.set_defaults(func=_scrape)

    prompt_parser = subparsers.add_parser(
        "prompt", help="Show the summarize prompt template"
    )
    prompt_parser.set_defaults(func=_prompt)

    summarize_parser = subparsers.add_parser(
        "summarize-url", help="Summarize a URL"
    )
    summarize_parser.add_argument("url", help="URL to summarize")
    summarize_parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Only return cached summaries",
    )
    summarize_parser.add_argument(
        "--summary-effort",
        default="low",
        help="Summary effort level",
    )
    summarize_parser.set_defaults(func=_summarize)

    remove_parser = subparsers.add_parser(
        "remove-url", help="Remove a URL from future scrapes"
    )
    remove_parser.add_argument("url", help="URL to remove")
    remove_parser.set_defaults(func=_remove)

    args = parser.parse_args(argv)

    try:
        args.func(args, logger)
    except Exception as error:  # noqa: BLE001
        _handle_error(error, logger)
        sys.exit(1)


if __name__ == "__main__":
    main()
