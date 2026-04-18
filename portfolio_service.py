from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
import logging
import uuid

import requests

import supabase_client
import util

logger = logging.getLogger("portfolio_service")

ALPHA_VANTAGE_API_KEY = util.resolve_env_var("ALPHAVANTAGE_API_KEY", "1N06QED7AXRQEBC1")
ALPHA_VANTAGE_DAILY_ENDPOINT = "https://www.alphavantage.co/query"
PORTFOLIO_TRANSACTION_KEY_PREFIX = "portfolio_app:transaction:"
PORTFOLIO_CLOSE_RATE_KEY_PREFIX = "portfolio_app:close_rate:"

ALPHA_VANTAGE_SYMBOL_MAP = {
    "AAPL": "AAPL",
    "AMD": "AMD",
    "AMZN": "AMZN",
    "CRWV": "CRWV",
    "GOOGL": "GOOGL",
    "INMD": "INMD",
    "MSFT": "MSFT",
    "MU": "MU",
    "NVDA": "NVDA",
    "SE": "SE",
    "TBLA": "TBLA",
    "TSM": "TSM",
    "VST": "VST",
    "TSLA": "TSLA",
    "HFG GY": "HFG.DE",
    "TA-125": "TA125.TA",
    "NAVITAS": "NVTS",
    "SK HYNIX": "000660.KS",
    "US BONDS 11/34": None,
}


def _get_settings_rows_by_prefix(key_prefix: str) -> list[dict]:
    supabase = supabase_client.get_supabase_client()
    result = (
        supabase.table("settings")
        .select("key,value")
        .like("key", f"{key_prefix}%")
        .order("key", desc=False)
        .execute()
    )
    return result.data or []


def list_transactions() -> list[dict]:
    rows = _get_settings_rows_by_prefix(PORTFOLIO_TRANSACTION_KEY_PREFIX)
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


def _fetch_last_close_rate_from_alpha_vantage(symbol: str) -> dict:
    response = requests.get(
        ALPHA_VANTAGE_DAILY_ENDPOINT,
        params={
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact",
            "apikey": ALPHA_VANTAGE_API_KEY,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if "Error Message" in payload:
        raise ValueError(payload["Error Message"])

    if "Note" in payload:
        raise ValueError(payload["Note"])

    time_series = payload["Time Series (Daily)"]
    latest_close_date = max(time_series.keys())
    close_price = float(time_series[latest_close_date]["4. close"])
    return {
        "close_price": close_price,
        "close_date": latest_close_date,
        "source_symbol": symbol,
    }


def _get_cached_close_rate(symbol_id: str) -> dict | None:
    cache_key = f"{PORTFOLIO_CLOSE_RATE_KEY_PREFIX}{symbol_id}"
    supabase = supabase_client.get_supabase_client()
    result = supabase.table("settings").select("value").eq("key", cache_key).execute()
    return result.data[0]["value"] if result.data else None


def _upsert_cached_close_rate(symbol_id: str, close_rate: dict) -> dict:
    cache_key = f"{PORTFOLIO_CLOSE_RATE_KEY_PREFIX}{symbol_id}"
    cache_value = {
        "symbol_id": symbol_id,
        "close_price": close_rate["close_price"],
        "close_date": close_rate["close_date"],
        "source_symbol": close_rate["source_symbol"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase = supabase_client.get_supabase_client()
    supabase.table("settings").upsert({"key": cache_key, "value": cache_value}).execute()
    return cache_value


def get_or_fetch_latest_close_rate(symbol_id: str) -> dict | None:
    mapped_symbol = ALPHA_VANTAGE_SYMBOL_MAP.get(symbol_id, symbol_id)
    if mapped_symbol is None:
        return None

    cached_close_rate = _get_cached_close_rate(symbol_id)
    today_utc = datetime.now(timezone.utc).date().isoformat()
    if cached_close_rate and cached_close_rate["close_date"] >= today_utc:
        return cached_close_rate

    try:
        fetched_close_rate = _fetch_last_close_rate_from_alpha_vantage(mapped_symbol)
        return _upsert_cached_close_rate(symbol_id, fetched_close_rate)
    except Exception as error:
        logger.warning(
            "alpha vantage close-rate fetch failed symbol_id=%s mapped_symbol=%s error=%s",
            symbol_id,
            mapped_symbol,
            repr(error),
            exc_info=True,
        )
        return cached_close_rate


def enrich_positions_with_market_data(positions: list[dict]) -> list[dict]:
    """Attach latest close rates and gain metrics to aggregated positions.

    >>> enrich_positions_with_market_data([{'symbol_id': 'US BONDS 11/34', 'transaction_amount_dollars': 1000.0, 'shares': 0.0}])[0]['current_market_value_dollars']
    1000.0
    """
    enriched_positions = []
    for position in positions:
        transaction_amount_dollars = float(position["transaction_amount_dollars"])
        shares = float(position["shares"])
        latest_close_rate = get_or_fetch_latest_close_rate(position["symbol_id"]) if shares != 0 else None

        if latest_close_rate:
            current_price_per_share = float(latest_close_rate["close_price"])
            current_market_value_dollars = current_price_per_share * shares
        else:
            current_price_per_share = None
            current_market_value_dollars = transaction_amount_dollars

        total_dollar_gain = current_market_value_dollars - transaction_amount_dollars
        if transaction_amount_dollars != 0:
            total_percent_change = (total_dollar_gain / transaction_amount_dollars) * 100
        else:
            total_percent_change = 0.0

        enriched_positions.append(
            {
                **position,
                "current_price_per_share": current_price_per_share,
                "current_market_value_dollars": current_market_value_dollars,
                "total_dollar_gain": total_dollar_gain,
                "total_percent_change": total_percent_change,
                "latest_close_date": latest_close_rate["close_date"] if latest_close_rate else None,
            }
        )

    return sorted(enriched_positions, key=lambda position: position["current_market_value_dollars"], reverse=True)
