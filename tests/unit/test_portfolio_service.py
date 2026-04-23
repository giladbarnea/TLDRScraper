import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hidden_apps.portfolio import api as portfolio_api
from hidden_apps.portfolio import service as portfolio_service


def test_snapshot_position_infers_shares_from_snapshot_close(monkeypatch):
    positions = portfolio_service.summarize_positions(
        [
            {
                "symbol_id": "AAPL",
                "transaction_amount_dollars": 1000,
                "shares": 0,
                "transaction_timestamp": "2026-04-17T13:39:14.002625+00:00",
                "entry_kind": "snapshot",
            }
        ]
    )

    def fake_snapshot_close_rate(symbol_id: str, requested_date: str) -> dict:
        assert symbol_id == "AAPL", f"Expected snapshot lookup for AAPL. Got {symbol_id=!r}"
        assert requested_date == "2026-04-17", f"Expected transaction-date lookup. Got {requested_date=!r}"
        return {"close_price": 100.0, "close_date": "2026-04-17", "source_symbol": "AAPL"}

    def fake_latest_close_rate(symbol_id: str) -> dict:
        assert symbol_id == "AAPL", f"Expected latest lookup for AAPL. Got {symbol_id=!r}"
        return {"close_price": 125.0, "close_date": "2026-04-22", "source_symbol": "AAPL"}

    monkeypatch.setattr(portfolio_service, "get_or_fetch_close_rate_on_or_before", fake_snapshot_close_rate)
    monkeypatch.setattr(portfolio_service, "get_or_fetch_latest_close_rate", fake_latest_close_rate)

    enriched_position = portfolio_service.enrich_positions_with_market_data(positions)[0]

    assert positions[0]["snapshot_lots"] == [
        {
            "snapshot_market_value_dollars": 1000.0,
            "snapshot_date": "2026-04-17",
        }
    ], f"Expected zero-share market row to become explicit snapshot lot. Got {positions=!r}"
    assert math.isclose(enriched_position["inferred_snapshot_shares"], 10.0), (
        f"Expected snapshot value / snapshot close to infer shares. Got {enriched_position=!r}"
    )
    assert math.isclose(enriched_position["current_market_value_dollars"], 1250.0), (
        f"Expected latest close multiplied by inferred shares. Got {enriched_position=!r}"
    )
    assert math.isclose(enriched_position["total_dollar_gain"], 250.0), (
        f"Expected current value minus snapshot value. Got {enriched_position=!r}"
    )
    assert math.isclose(enriched_position["total_percent_change"], 25.0), (
        f"Expected gain divided by snapshot value. Got {enriched_position=!r}"
    )


def test_non_market_value_position_stays_amount_based(monkeypatch):
    positions = portfolio_service.summarize_positions(
        [
            {
                "symbol_id": "US BONDS 11/34",
                "transaction_amount_dollars": 1000,
                "shares": 0,
                "transaction_timestamp": "2026-04-17T13:39:14.002625+00:00",
                "entry_kind": "snapshot",
            }
        ]
    )

    def fail_latest_close_rate(symbol_id: str) -> dict:
        raise AssertionError(f"Bond should not request market data. Got {symbol_id=!r}")

    monkeypatch.setattr(portfolio_service, "get_or_fetch_latest_close_rate", fail_latest_close_rate)

    enriched_position = portfolio_service.enrich_positions_with_market_data(positions)[0]

    assert positions[0]["snapshot_lots"] == [], f"Expected bonds to stay out of market snapshots. Got {positions=!r}"
    assert enriched_position["current_market_value_dollars"] == 1000.0, (
        f"Expected unpriced position to stay amount-based. Got {enriched_position=!r}"
    )
    assert enriched_position["total_dollar_gain"] == 0.0, (
        f"Expected no calculated gain for unpriced position. Got {enriched_position=!r}"
    )
    assert enriched_position["total_percent_change"] == 0.0, (
        f"Expected no calculated percent change for unpriced position. Got {enriched_position=!r}"
    )


def test_market_position_with_shares_uses_close_rate(monkeypatch):
    positions = portfolio_service.summarize_positions(
        [
            {
                "symbol_id": "AAPL",
                "transaction_amount_dollars": 1000,
                "shares": 5,
                "transaction_timestamp": "2026-04-17T13:39:14.002625+00:00",
                "entry_kind": "trade",
            }
        ]
    )

    def fake_latest_close_rate(symbol_id: str) -> dict:
        assert symbol_id == "AAPL", f"Expected latest lookup for AAPL. Got {symbol_id=!r}"
        return {"close_price": 250.0, "close_date": "2026-04-22", "source_symbol": "AAPL"}

    monkeypatch.setattr(portfolio_service, "get_or_fetch_latest_close_rate", fake_latest_close_rate)

    enriched_position = portfolio_service.enrich_positions_with_market_data(positions)[0]

    assert math.isclose(enriched_position["current_market_value_dollars"], 1250.0), (
        f"Expected close price multiplied by shares. Got {enriched_position=!r}"
    )
    assert math.isclose(enriched_position["total_dollar_gain"], 250.0), (
        f"Expected current market value minus transaction amount. Got {enriched_position=!r}"
    )
    assert math.isclose(enriched_position["total_percent_change"], 25.0), (
        f"Expected gain divided by transaction amount. Got {enriched_position=!r}"
    )


def test_positions_response_runs_portfolio_flow_without_flask(monkeypatch):
    transactions = [
        {
            "symbol_id": "AAPL",
            "transaction_amount_dollars": 1000,
            "shares": 0,
            "transaction_timestamp": "2026-04-17T13:39:14.002625+00:00",
            "entry_kind": "snapshot",
        }
    ]

    def fake_snapshot_close_rate(symbol_id: str, requested_date: str) -> dict:
        assert symbol_id == "AAPL", f"Expected snapshot lookup for AAPL. Got {symbol_id=!r}"
        assert requested_date == "2026-04-17", f"Expected transaction-date lookup. Got {requested_date=!r}"
        return {"close_price": 100.0, "close_date": "2026-04-17", "source_symbol": "AAPL"}

    def fake_latest_close_rate(symbol_id: str) -> dict:
        assert symbol_id == "AAPL", f"Expected latest lookup for AAPL. Got {symbol_id=!r}"
        return {"close_price": 125.0, "close_date": "2026-04-22", "source_symbol": "AAPL"}

    monkeypatch.setattr(portfolio_service, "get_or_fetch_close_rate_on_or_before", fake_snapshot_close_rate)
    monkeypatch.setattr(portfolio_service, "get_or_fetch_latest_close_rate", fake_latest_close_rate)

    payload, status_code = portfolio_api.positions_response_for_transactions(transactions)

    assert status_code == 200, f"Expected successful response status. Got {status_code=}, {payload=!r}"
    assert payload["success"] is True, f"Expected success payload. Got {payload=!r}"
    position = payload["positions"][0]
    assert math.isclose(position["total_dollar_gain"], 250.0), (
        f"Expected API response to include gain since snapshot. Got {payload=!r}"
    )


def test_zero_share_trade_does_not_become_snapshot(monkeypatch):
    positions = portfolio_service.summarize_positions(
        [
            {
                "symbol_id": "AAPL",
                "transaction_amount_dollars": 1000,
                "shares": 0,
                "transaction_timestamp": "2026-04-17T13:39:14.002625+00:00",
                "entry_kind": "trade",
            }
        ]
    )

    def fail_close_rate_lookup(*args: object) -> dict:
        raise AssertionError(f"Zero-share trade should not request market data. Got {args=!r}")

    monkeypatch.setattr(portfolio_service, "get_or_fetch_close_rate_on_or_before", fail_close_rate_lookup)
    monkeypatch.setattr(portfolio_service, "get_or_fetch_latest_close_rate", fail_close_rate_lookup)

    enriched_position = portfolio_service.enrich_positions_with_market_data(positions)[0]

    assert positions[0]["snapshot_lots"] == [], f"Expected trade entry to stay out of snapshot lots. Got {positions=!r}"
    assert enriched_position["current_market_value_dollars"] == 1000.0, (
        f"Expected zero-share trade to stay amount-based. Got {enriched_position=!r}"
    )


def test_latest_close_rate_uses_fresh_supabase_cache_before_yahoo(monkeypatch):
    cached_close_rate = {
        "symbol_id": "AAPL",
        "close_price": 125.0,
        "close_date": "2026-04-22",
        "source_symbol": "AAPL",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    def fake_cached_close_rate(symbol_id: str, requested_date: str | None = None) -> dict:
        assert symbol_id == "AAPL", f"Expected cache lookup for AAPL. Got {symbol_id=!r}"
        assert requested_date is None, f"Expected latest cache lookup. Got {requested_date=!r}"
        return cached_close_rate

    def fail_yahoo_fetch(symbol: str, requested_date: str | None = None) -> dict:
        raise AssertionError(f"Fresh Supabase cache should prevent Yahoo fetch. Got {symbol=}, {requested_date=!r}")

    monkeypatch.setattr(portfolio_service, "_get_cached_close_rate", fake_cached_close_rate)
    monkeypatch.setattr(portfolio_service, "_fetch_close_rate_from_yahoo", fail_yahoo_fetch)

    close_rate = portfolio_service.get_or_fetch_latest_close_rate("AAPL")

    assert close_rate == cached_close_rate, f"Expected fresh Supabase cache to win. Got {close_rate=!r}"
