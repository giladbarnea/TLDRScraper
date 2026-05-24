"""
Pipeline replay control panel.

Load into IPython:
    %load pipeline_replay.py

Each section exposes one stage of the scrape → merge → persist pipeline as it
runs in production. Functions are imported as-is from the real modules; no
wrapping logic. Helpers below are pure date math, factory access, or display.

Prerequisites: run from the project root with Supabase env vars loaded:
    set -a && source .env && set +a
    ipython
"""

import datetime as dt
import json

import util
import storage_service
from newsletter_config import NEWSLETTER_CONFIGS
from newsletter_scraper import (
    _get_adapter_for_source,            # source_id → adapter instance (factory)
    scrape_single_source_for_date,      # ENTRY: one source × one date
    merge_source_results_for_date,      # ENTRY: union all sources for one date
)
from tldr_service import (
    _article_to_payload,                # one raw article dict → API article shape
    _build_payload_from_scrape,         # ⚠ filters issues by date; articles pass through
    _merge_payloads,                    # union fresh scrape onto cached payload
    scrape_newsletters_in_date_range,   # ENTRY: full driver (cache → scrape → merge → persist)
)


# ────────────────────────────────────────────────────────────────
# Date helpers
# ────────────────────────────────────────────────────────────────

def today_pacific():
    """Today's date in Pacific time, ISO format. The system's notion of 'today'."""
    return dt.datetime.now(util.PACIFIC_TZ).date().isoformat()


def days_ago_pacific(n):
    """N days before today_pacific(), ISO format."""
    return (dt.datetime.now(util.PACIFIC_TZ).date() - dt.timedelta(days=n)).isoformat()


def list_sources():
    """All registered source_ids."""
    return sorted(NEWSLETTER_CONFIGS.keys())


def make_adapter(source_id):
    """Instantiate the adapter for `source_id`. Call `.scrape_date(date, excluded_urls)`."""
    return _get_adapter_for_source(NEWSLETTER_CONFIGS[source_id])


# ────────────────────────────────────────────────────────────────
# Stage 1 — Adapter call (one source × one date)
# ────────────────────────────────────────────────────────────────
# Raw adapter (zoomed in — no canonicalization, no history dedup):
#   adapter = make_adapter("deepmind")
#   raw = adapter.scrape_date("2026-05-19", [])
#       # → {"articles": [...], "issues": [...]}
#
# Production wrapper (canonicalizes URLs, applies history dedup):
#   date_str, result = scrape_single_source_for_date("2026-05-19", "deepmind", [])
#       # result = {"articles", "issues", "network_articles", "error", "source_id"}


# ────────────────────────────────────────────────────────────────
# Stage 2 — Per-date merge across sources
# ────────────────────────────────────────────────────────────────
# merge_source_results_for_date(date_str, [(source_id, result), ...])
#   URL-deduplicates articles; keys issues by (date, source_id, category).
#
# Example after running Stage 1 for several sources:
#   sids = ["deepmind", "simon_willison", "hackernews"]
#   results = [scrape_single_source_for_date("2026-05-19", sid, [])[1] for sid in sids]
#   pairs = [(r["source_id"], r) for r in results]
#   merged = merge_source_results_for_date("2026-05-19", pairs)
#       # → {"articles", "issues", "network_fetches"}


# ────────────────────────────────────────────────────────────────
# Stage 3 — Build payload from scrape  (date filter lives HERE)
# ────────────────────────────────────────────────────────────────
# _build_payload_from_scrape(date_str, articles, issues)
#   Builds the per-date payload. Filters ISSUES by issue["date"] == date_str;
#   articles are passed through unfiltered. ← suspected leak point.
#
# _article_to_payload(article)  → single article in API shape.
#
# Example:
#   payload = _build_payload_from_scrape("2026-05-19", merged["articles"], merged["issues"])


# ────────────────────────────────────────────────────────────────
# Stage 4 — Cache merge
# ────────────────────────────────────────────────────────────────
# _merge_payloads(new_payload, cached_payload)
#   Article union by URL (cached user-state preserved); issue union by triple-key.
#
# Example:
#   cached = storage_service.get_daily_payload("2026-05-19") or {"articles": [], "issues": []}
#   final = _merge_payloads(payload, cached)


# ────────────────────────────────────────────────────────────────
# Stage 5 — End-to-end pipeline
# ────────────────────────────────────────────────────────────────
# scrape_newsletters_in_date_range(start, end, source_ids=None, excluded_urls=None)
#   Cache check → parallel scrape per (date, source) → per-date merge →
#   _build_payload_from_scrape → _merge_payloads against cache → persist.
#
# Examples:
#   scrape_newsletters_in_date_range("2026-05-19", "2026-05-19", source_ids=["deepmind"])
#   scrape_newsletters_in_date_range(days_ago_pacific(3), today_pacific())


# ────────────────────────────────────────────────────────────────
# Stage 6 — Storage (Supabase daily_cache)
# ────────────────────────────────────────────────────────────────
# Reads:
#   storage_service.get_daily_payload(date)               # payload dict or None
#   storage_service.get_daily_payload_row(date)           # adds cached_at / updated_at
#   storage_service.get_daily_payloads_range(start, end)  # list of rows
#   storage_service.get_daily_payloads_summary(start, end)# flat per-article overview
#
# Writes (DESTRUCTIVE — bypass scrape):
#   storage_service.set_daily_payload(date, payload)              # no cached_at bump
#   storage_service.set_daily_payload_from_scrape(date, payload)  # advances cached_at
#
# Delete:
#   storage_service.delete_daily_payloads_range(start, end)
#   clear_storage(date) or clear_storage(start, end)

def clear_storage(start, end=None):
    """Delete daily payloads in [start, end] (inclusive). End defaults to start."""
    return storage_service.delete_daily_payloads_range(start, end or start)


# ────────────────────────────────────────────────────────────────
# Display
# ────────────────────────────────────────────────────────────────

def show(payload, *, limit=10):
    """Compact print of a payload: counts, issues, first N articles."""
    if payload is None:
        print("None"); return
    articles = payload.get("articles", []) if isinstance(payload, dict) else []
    issues = payload.get("issues", []) if isinstance(payload, dict) else []
    print(f"date={payload.get('date')}  articles={len(articles)}  issues={len(issues)}")
    if issues:
        print("issues:")
        for issue in issues:
            print(f"  source={issue.get('source_id'):25s} date={issue.get('date')}  category={issue.get('category')!r}")
    if articles:
        print(f"articles (first {min(limit, len(articles))}):")
        for article in articles[:limit]:
            article_date = article.get("date") or article.get("issueDate")
            source = article.get("source_id") or article.get("sourceId")
            print(f"  date={article_date}  source={source}  url={article.get('url')}")
        if len(articles) > limit:
            print(f"  … {len(articles) - limit} more")


def dump(obj):
    """Pretty JSON dump."""
    print(json.dumps(obj, indent=2, default=str))


# ────────────────────────────────────────────────────────────────
# Thin CLI
# ────────────────────────────────────────────────────────────────
# Run as:   uv run python3 pipeline_replay.py <cmd> [args]
# Requires Supabase env vars loaded for any storage / pipeline command.

def _resolve_end(end, start):
    return end or start


def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="TLDRScraper pipeline replay")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sources", help="List registered source_ids")

    p = sub.add_parser("peek", help="Stage 1 (raw): adapter.scrape_date — no canonicalization, no dedup")
    p.add_argument("date"); p.add_argument("source")

    p = sub.add_parser("scrape-source", help="Stage 1 (prod-wrapped): scrape_single_source_for_date")
    p.add_argument("date"); p.add_argument("source")

    p = sub.add_parser("merge-day", help="Stage 1+2: scrape several sources then merge_source_results_for_date")
    p.add_argument("date"); p.add_argument("sources", nargs="+")

    p = sub.add_parser("payload-day", help="Stage 1+2+3: + _build_payload_from_scrape (issue date filter)")
    p.add_argument("date"); p.add_argument("sources", nargs="+")

    p = sub.add_parser("pipeline", help="Stage 5: scrape_newsletters_in_date_range (writes to storage)")
    p.add_argument("start"); p.add_argument("end", nargs="?")
    p.add_argument("--sources", nargs="+")

    p = sub.add_parser("get", help="Storage: get_daily_payload_row")
    p.add_argument("date")

    p = sub.add_parser("summary", help="Storage: get_daily_payloads_summary over a date range")
    p.add_argument("start"); p.add_argument("end", nargs="?")

    p = sub.add_parser("clear", help="Storage: delete_daily_payloads_range (DESTRUCTIVE)")
    p.add_argument("start"); p.add_argument("end", nargs="?")
    p.add_argument("--yes", action="store_true", help="Skip confirmation")

    p = sub.add_parser("today", help="Print today_pacific()")

    args = parser.parse_args()

    if args.cmd == "sources":
        for sid in list_sources(): print(sid)

    elif args.cmd == "today":
        print(today_pacific())

    elif args.cmd == "peek":
        adapter = make_adapter(args.source)
        raw = adapter.scrape_date(args.date, [])
        show({"date": args.date, "articles": raw.get("articles", []), "issues": raw.get("issues", [])})

    elif args.cmd == "scrape-source":
        date_str, result = scrape_single_source_for_date(args.date, args.source, [])
        print(f"date_str={date_str}  source={result['source_id']}  network={result['network_articles']}  error={result['error']}")
        show({"date": date_str, "articles": result["articles"], "issues": result["issues"]})

    elif args.cmd == "merge-day":
        pairs = []
        for sid in args.sources:
            _, result = scrape_single_source_for_date(args.date, sid, [])
            pairs.append((sid, result))
        merged = merge_source_results_for_date(args.date, pairs)
        print(f"network_fetches={merged['network_fetches']}")
        show({"date": args.date, "articles": merged["articles"], "issues": merged["issues"]})

    elif args.cmd == "payload-day":
        pairs = []
        for sid in args.sources:
            _, result = scrape_single_source_for_date(args.date, sid, [])
            pairs.append((sid, result))
        merged = merge_source_results_for_date(args.date, pairs)
        payload = _build_payload_from_scrape(args.date, merged["articles"], merged["issues"])
        print(f"PRE-FILTER  articles={len(merged['articles'])}  issues={len(merged['issues'])}")
        print(f"POST-FILTER articles={len(payload['articles'])}  issues={len(payload['issues'])}")
        show(payload)

    elif args.cmd == "pipeline":
        end = _resolve_end(args.end, args.start)
        result = scrape_newsletters_in_date_range(args.start, end, source_ids=args.sources)
        print(f"source={result['source']}  stats={result['stats']}")
        for payload in result["payloads"]:
            show(payload)
            print()

    elif args.cmd == "get":
        row = storage_service.get_daily_payload_row(args.date)
        if row is None:
            print("None"); return
        print(f"updated_at={row['updated_at']}")
        show(row["payload"])

    elif args.cmd == "summary":
        end = _resolve_end(args.end, args.start)
        for day in storage_service.get_daily_payloads_summary(args.start, end):
            print(f"{day['date']}  cached_at={day['cached_at']}  articles={day['article_count']}")

    elif args.cmd == "clear":
        end = _resolve_end(args.end, args.start)
        if not args.yes:
            confirm = input(f"DELETE rows in [{args.start}, {end}]? (yes/no) ")
            if confirm != "yes":
                print("aborted"); return
        deleted = storage_service.delete_daily_payloads_range(args.start, end)
        print(f"deleted={deleted}")


if __name__ == "__main__":
    _cli()
