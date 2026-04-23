#!/usr/bin/env -S uv run
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from hidden_apps.portfolio import api, service


FIXTURE_TRANSACTIONS = [
    {
        "id": "fixture-aapl-snapshot",
        "symbol_id": "AAPL",
        "transaction_amount_dollars": 1000,
        "shares": 0,
        "transaction_timestamp": "2026-04-17T13:39:14.002625+00:00",
    }
]


def install_fixture_market_data() -> None:
    def snapshot_close_rate(symbol_id: str, requested_date: str) -> dict:
        return {"close_price": 100.0, "close_date": requested_date, "source_symbol": symbol_id}

    def latest_close_rate(symbol_id: str) -> dict:
        return {"close_price": 125.0, "close_date": "2026-04-22", "source_symbol": symbol_id}

    service.get_or_fetch_close_rate_on_or_before = snapshot_close_rate
    service.get_or_fetch_latest_close_rate = latest_close_rate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()

    if args.fixture:
        install_fixture_market_data()
        payload, status_code = api.positions_response_for_transactions(FIXTURE_TRANSACTIONS)
    else:
        payload, status_code = api.positions_response()

    print(json.dumps({"status_code": status_code, "payload": payload}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
