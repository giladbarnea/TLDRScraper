import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import portfolio_service


def test_zero_share_positions_never_fetch_close_rate_and_stay_zero_growth(monkeypatch):
    calls = []

    def fake_get_or_fetch_latest_close_rate(symbol_id: str):
        calls.append(symbol_id)
        return {"close_price": 999.0, "close_date": "2026-04-20", "source_symbol": symbol_id}

    monkeypatch.setattr(portfolio_service, "get_or_fetch_latest_close_rate", fake_get_or_fetch_latest_close_rate)

    transactions = [
        {"symbol_id": "AAPL", "transaction_amount_dollars": 3175.92, "shares": 0.0},
        {"symbol_id": "NVDA", "transaction_amount_dollars": 15301.92, "shares": 0.0},
    ]

    summarized_positions = portfolio_service.summarize_positions(transactions)
    enriched_positions = portfolio_service.enrich_positions_with_market_data(summarized_positions)

    assert calls == []
    assert all(position["total_percent_change"] == 0.0 for position in enriched_positions)
    assert all(position["current_price_per_share"] is None for position in enriched_positions)
