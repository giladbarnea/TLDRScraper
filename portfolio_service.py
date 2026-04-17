from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
import uuid

import supabase_client

PORTFOLIO_TRANSACTION_KEY_PREFIX = "portfolio_app:transaction:"


def list_transactions() -> list[dict]:
    supabase = supabase_client.get_supabase_client()
    result = (
        supabase.table("settings")
        .select("key,value")
        .like("key", f"{PORTFOLIO_TRANSACTION_KEY_PREFIX}%")
        .order("key", desc=False)
        .execute()
    )
    rows = result.data or []
    return [row["value"] for row in rows]


def append_transaction(symbol_id: str, transaction_amount_dollars: float, shares: float) -> dict:
    transaction_id = str(uuid.uuid4())
    transaction_timestamp = datetime.now(timezone.utc).isoformat()
    transaction = {
        "id": transaction_id,
        "symbol_id": symbol_id,
        "transaction_amount_dollars": transaction_amount_dollars,
        "shares": shares,
        "transaction_timestamp": transaction_timestamp,
    }
    transaction_key = f"{PORTFOLIO_TRANSACTION_KEY_PREFIX}{transaction_timestamp}:{transaction_id}"

    supabase = supabase_client.get_supabase_client()
    supabase.table("settings").insert({"key": transaction_key, "value": transaction}).execute()
    return transaction


def summarize_positions(transactions: list[dict]) -> list[dict]:
    """Aggregate append-only transactions into current positions.

    >>> summarize_positions([
    ...     {'symbol_id': 'AAPL', 'transaction_amount_dollars': 1000, 'shares': 5},
    ...     {'symbol_id': 'AAPL', 'transaction_amount_dollars': -100, 'shares': -0.5},
    ... ])[0]['transaction_amount_dollars']
    900.0
    """
    positions_by_symbol: dict[str, dict[str, Decimal]] = {}
    for transaction in transactions:
        symbol_id = transaction["symbol_id"]
        if symbol_id not in positions_by_symbol:
            positions_by_symbol[symbol_id] = {
                "transaction_amount_dollars": Decimal("0"),
                "shares": Decimal("0"),
            }

        positions_by_symbol[symbol_id]["transaction_amount_dollars"] += Decimal(
            str(transaction["transaction_amount_dollars"])
        )
        positions_by_symbol[symbol_id]["shares"] += Decimal(str(transaction["shares"]))

    positions = [
        {
            "symbol_id": symbol_id,
            "transaction_amount_dollars": float(values["transaction_amount_dollars"]),
            "shares": float(values["shares"]),
        }
        for symbol_id, values in positions_by_symbol.items()
    ]
    return sorted(positions, key=lambda position: position["transaction_amount_dollars"], reverse=True)
