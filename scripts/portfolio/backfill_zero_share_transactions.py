from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import portfolio_service
import supabase_client


def _fetch_close_rate_for_date(symbol: str, target_date: str) -> tuple[float, str]:
    response = requests.get(
        portfolio_service.ALPHA_VANTAGE_DAILY_ENDPOINT,
        params={
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact",
            "apikey": portfolio_service.ALPHA_VANTAGE_API_KEY,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if "Error Message" in payload:
        raise ValueError(payload["Error Message"])
    if "Note" in payload:
        raise ValueError(payload["Note"])
    if "Information" in payload:
        raise ValueError(payload["Information"])

    time_series = payload["Time Series (Daily)"]
    available_dates = [date for date in time_series.keys() if date <= target_date]
    if len(available_dates) == 0:
        raise ValueError(f"No daily close found for symbol={symbol} date={target_date}")

    close_date = max(available_dates)
    close_price = float(time_series[close_date]["4. close"])
    return close_price, close_date


def _normalize_transaction_date(transaction_timestamp: str) -> str:
    return datetime.fromisoformat(transaction_timestamp).date().isoformat()


def _infer_shares_for_transaction(transaction: dict, symbol_close_cache: dict[tuple[str, str], tuple[float, str]]) -> tuple[float, str]:
    symbol_id = transaction["symbol_id"]
    mapped_symbol = portfolio_service.ALPHA_VANTAGE_SYMBOL_MAP.get(symbol_id, symbol_id)
    if mapped_symbol is None:
        raise ValueError(f"Cannot infer shares for unmapped symbol {symbol_id}")

    transaction_date = _normalize_transaction_date(transaction["transaction_timestamp"])
    cache_key = (mapped_symbol, transaction_date)
    if cache_key not in symbol_close_cache:
        symbol_close_cache[cache_key] = _fetch_close_rate_for_date(mapped_symbol, transaction_date)

    close_price, close_date = symbol_close_cache[cache_key]
    inferred_shares = float(transaction["transaction_amount_dollars"]) / close_price
    return inferred_shares, close_date


def run_backfill(apply_changes: bool) -> None:
    supabase = supabase_client.get_supabase_client()
    settings_rows = (
        supabase.table("settings")
        .select("key,value")
        .like("key", f"{portfolio_service.PORTFOLIO_TRANSACTION_KEY_PREFIX}%")
        .order("key", desc=False)
        .execute()
        .data
        or []
    )

    candidate_rows = []
    for row in settings_rows:
        transaction = row["value"]
        if float(transaction["shares"]) == 0.0 and float(transaction["transaction_amount_dollars"]) != 0.0:
            mapped_symbol = portfolio_service.ALPHA_VANTAGE_SYMBOL_MAP.get(transaction["symbol_id"], transaction["symbol_id"])
            if mapped_symbol is not None:
                candidate_rows.append(row)

    print(f"Found {len(candidate_rows)} candidate zero-share transactions to backfill")
    if len(candidate_rows) == 0:
        return

    symbol_close_cache: dict[tuple[str, str], tuple[float, str]] = {}
    updates_by_symbol: dict[str, int] = defaultdict(int)
    failed_rows = 0

    for row in candidate_rows:
        transaction = row["value"]
        try:
            inferred_shares, close_date = _infer_shares_for_transaction(transaction, symbol_close_cache)
        except Exception as error:
            failed_rows += 1
            print(f"FAILED {row['key']} symbol={transaction['symbol_id']} error={error}")
            continue

        updates_by_symbol[transaction["symbol_id"]] += 1
        updated_transaction = {
            **transaction,
            "shares": inferred_shares,
        }
        print(
            f"{row['key']} symbol={transaction['symbol_id']} amount={transaction['transaction_amount_dollars']} "
            f"date={transaction['transaction_timestamp']} close_date={close_date} inferred_shares={inferred_shares:.8f}"
        )

        if apply_changes:
            supabase.table("settings").update({"value": updated_transaction}).eq("key", row["key"]).execute()

    print("Updates by symbol:")
    for symbol_id, updates in sorted(updates_by_symbol.items()):
        print(f"  {symbol_id}: {updates}")
    if failed_rows:
        print(f"Failed rows: {failed_rows}")

    if not apply_changes:
        print("Dry run complete. Re-run with --apply to persist updates.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run_backfill(apply_changes=args.apply)
