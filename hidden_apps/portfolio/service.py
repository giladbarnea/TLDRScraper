from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
import logging
import uuid
from urllib.parse import quote
from zoneinfo import ZoneInfo

from curl_cffi import requests

import supabase_client

logger = logging.getLogger("hidden_apps.portfolio.service")

YAHOO_CHART_ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart"
YAHOO_CHART_RANGE = "5y"
PORTFOLIO_TRANSACTION_TABLE = "portfolio_transactions"
PORTFOLIO_LATEST_CLOSE_RATE_TABLE = "portfolio_latest_close_rates"
PORTFOLIO_HISTORICAL_CLOSE_RATE_TABLE = "portfolio_historical_close_rates"
_daily_close_prices_by_symbol_and_fetch_date: dict[tuple[str, str], dict[str, float]] = {}

YAHOO_SYMBOL_MAP = {
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
    "TA-125": "^TA125.TA",
    "NAVITAS": "NVTS",
    "SK HYNIX": "000660.KS",
    "US BONDS 11/34": None,
}


@dataclass
class SnapshotLot:
    snapshot_market_value_dollars: Decimal
    snapshot_date: str


@dataclass
class PositionAccumulator:
    transaction_amount_dollars: Decimal = Decimal("0")
    shares: Decimal = Decimal("0")
    snapshot_lots: list[SnapshotLot] = field(default_factory=list)


def _transaction_row_to_payload(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "symbol_id": str(row["symbol_id"]),
        "transaction_amount_dollars": float(row["transaction_amount_dollars"]),
        "shares": float(row["shares"]),
        "transaction_timestamp": str(row["transaction_timestamp"]),
    }


def list_transactions() -> list[dict]:
    supabase = supabase_client.get_supabase_client()
    result = (
        supabase.table(PORTFOLIO_TRANSACTION_TABLE)
        .select("id,symbol_id,transaction_amount_dollars,shares,transaction_timestamp")
        .order("transaction_timestamp", desc=False)
        .execute()
    )
    return [_transaction_row_to_payload(row) for row in result.data or []]


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

    supabase = supabase_client.get_supabase_client()
    supabase.table(PORTFOLIO_TRANSACTION_TABLE).insert(transaction).execute()
    return transaction


def _mapped_market_symbol(symbol_id: str) -> str | None:
    return YAHOO_SYMBOL_MAP.get(symbol_id, symbol_id)


def _transaction_date(transaction: dict) -> str:
    timestamp = str(transaction["transaction_timestamp"])
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()


def _is_snapshot_lot(symbol_id: str, transaction_amount_dollars: Decimal, shares: Decimal) -> bool:
    return (
        shares == Decimal("0")
        and transaction_amount_dollars != Decimal("0")
        and _mapped_market_symbol(symbol_id) is not None
    )


def summarize_positions(transactions: list[dict]) -> list[dict]:
    """Aggregate append-only transactions into current positions.

    >>> summarize_positions([
    ...     {'symbol_id': 'AAPL', 'transaction_amount_dollars': 1000, 'shares': 5},
    ...     {'symbol_id': 'AAPL', 'transaction_amount_dollars': -100, 'shares': -0.5},
    ... ])[0]['transaction_amount_dollars']
    900.0
    """
    positions_by_symbol: dict[str, PositionAccumulator] = {}
    for transaction in transactions:
        symbol_id = transaction["symbol_id"]
        transaction_amount_dollars = Decimal(str(transaction["transaction_amount_dollars"]))
        shares = Decimal(str(transaction["shares"]))
        accumulator = positions_by_symbol.setdefault(symbol_id, PositionAccumulator())

        accumulator.transaction_amount_dollars += transaction_amount_dollars
        accumulator.shares += shares
        if _is_snapshot_lot(symbol_id, transaction_amount_dollars, shares):
            accumulator.snapshot_lots.append(
                SnapshotLot(
                    snapshot_market_value_dollars=transaction_amount_dollars,
                    snapshot_date=_transaction_date(transaction),
                )
            )

    positions = [
        {
            "symbol_id": symbol_id,
            "transaction_amount_dollars": float(values.transaction_amount_dollars),
            "shares": float(values.shares),
            "snapshot_lots": [
                {
                    "snapshot_market_value_dollars": float(snapshot_lot.snapshot_market_value_dollars),
                    "snapshot_date": snapshot_lot.snapshot_date,
                }
                for snapshot_lot in values.snapshot_lots
            ],
        }
        for symbol_id, values in positions_by_symbol.items()
    ]
    return sorted(positions, key=lambda position: position["transaction_amount_dollars"], reverse=True)


def _fetch_daily_close_prices_from_yahoo(symbol: str) -> dict[str, float]:
    fetch_date = datetime.now(timezone.utc).date().isoformat()
    cache_key = (symbol, fetch_date)
    if cache_key in _daily_close_prices_by_symbol_and_fetch_date:
        return _daily_close_prices_by_symbol_and_fetch_date[cache_key]

    response = requests.get(
        f"{YAHOO_CHART_ENDPOINT}/{quote(symbol, safe='')}",
        params={
            "range": YAHOO_CHART_RANGE,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        },
        impersonate="chrome",
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    chart = payload["chart"]
    if chart["error"]:
        raise ValueError(chart["error"])

    result = chart["result"][0]
    timestamps = result["timestamp"]
    quotes = result["indicators"]["quote"][0]
    close_prices = quotes["close"]
    market_timezone = ZoneInfo(result["meta"]["exchangeTimezoneName"])
    close_prices_by_date = {
        datetime.fromtimestamp(timestamp, market_timezone).date().isoformat(): float(close_price)
        for timestamp, close_price in zip(timestamps, close_prices)
        if close_price is not None
    }
    if not close_prices_by_date:
        raise ValueError(f"No Yahoo close rates found for {symbol}")

    _daily_close_prices_by_symbol_and_fetch_date[cache_key] = close_prices_by_date
    return close_prices_by_date


def _fetch_close_rate_from_yahoo(symbol: str, requested_date: str | None = None) -> dict:
    close_prices_by_date = _fetch_daily_close_prices_from_yahoo(symbol)
    eligible_dates = [
        close_date
        for close_date in close_prices_by_date
        if requested_date is None or close_date <= requested_date
    ]
    if not eligible_dates:
        raise ValueError(f"No Yahoo close rate found for {symbol} on or before {requested_date}")

    close_date = max(eligible_dates)
    return {
        "close_price": close_prices_by_date[close_date],
        "close_date": close_date,
        "source_symbol": symbol,
    }


def _close_rate_row_to_payload(row: dict, requested_date: str | None = None) -> dict:
    close_rate = {
        "symbol_id": str(row["symbol_id"]),
        "close_price": float(row["close_price"]),
        "close_date": str(row["close_date"]),
        "source_symbol": str(row["source_symbol"]),
        "updated_at": str(row["updated_at"]),
    }
    if requested_date is not None:
        close_rate["requested_date"] = requested_date

    return close_rate


def _get_cached_latest_close_rate(symbol_id: str) -> dict | None:
    supabase = supabase_client.get_supabase_client()
    result = (
        supabase.table(PORTFOLIO_LATEST_CLOSE_RATE_TABLE)
        .select("symbol_id,close_price,close_date,source_symbol,updated_at")
        .eq("symbol_id", symbol_id)
        .execute()
    )
    return _close_rate_row_to_payload(result.data[0]) if result.data else None


def _get_cached_historical_close_rate(symbol_id: str, requested_date: str) -> dict | None:
    supabase = supabase_client.get_supabase_client()
    result = (
        supabase.table(PORTFOLIO_HISTORICAL_CLOSE_RATE_TABLE)
        .select("symbol_id,requested_date,close_price,close_date,source_symbol,updated_at")
        .eq("symbol_id", symbol_id)
        .eq("requested_date", requested_date)
        .execute()
    )
    return _close_rate_row_to_payload(result.data[0], requested_date) if result.data else None


def _get_cached_close_rate(symbol_id: str, requested_date: str | None = None) -> dict | None:
    if requested_date is not None:
        return _get_cached_historical_close_rate(symbol_id, requested_date)

    return _get_cached_latest_close_rate(symbol_id)


def _close_rate_payload(symbol_id: str, close_rate: dict, requested_date: str | None = None) -> dict:
    payload = {
        "symbol_id": symbol_id,
        "close_price": close_rate["close_price"],
        "close_date": close_rate["close_date"],
        "source_symbol": close_rate["source_symbol"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if requested_date is not None:
        payload["requested_date"] = requested_date

    return payload


def _upsert_cached_close_rate(symbol_id: str, close_rate: dict, requested_date: str | None = None) -> dict:
    cache_value = _close_rate_payload(symbol_id, close_rate, requested_date)
    table_name = PORTFOLIO_HISTORICAL_CLOSE_RATE_TABLE if requested_date is not None else PORTFOLIO_LATEST_CLOSE_RATE_TABLE

    supabase = supabase_client.get_supabase_client()
    supabase.table(table_name).upsert(cache_value).execute()
    return cache_value


def _cached_latest_close_rate_is_fresh(cached_close_rate: dict) -> bool:
    today_utc = datetime.now(timezone.utc).date().isoformat()
    updated_at = cached_close_rate.get("updated_at")
    if updated_at:
        updated_date = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00")).date().isoformat()
        return updated_date >= today_utc

    return cached_close_rate["close_date"] >= today_utc


def get_or_fetch_latest_close_rate(symbol_id: str) -> dict | None:
    mapped_symbol = _mapped_market_symbol(symbol_id)
    if mapped_symbol is None:
        return None

    cached_close_rate = _get_cached_close_rate(symbol_id)
    if cached_close_rate and _cached_latest_close_rate_is_fresh(cached_close_rate):
        return cached_close_rate

    try:
        fetched_close_rate = _fetch_close_rate_from_yahoo(mapped_symbol)
        return _upsert_cached_close_rate(symbol_id, fetched_close_rate)
    except Exception as error:
        logger.warning(
            "yahoo close-rate fetch failed symbol_id=%s mapped_symbol=%s error=%s",
            symbol_id,
            mapped_symbol,
            repr(error),
            exc_info=True,
        )
        return cached_close_rate


def get_or_fetch_close_rate_on_or_before(symbol_id: str, requested_date: str) -> dict | None:
    mapped_symbol = _mapped_market_symbol(symbol_id)
    if mapped_symbol is None:
        return None

    cached_close_rate = _get_cached_close_rate(symbol_id, requested_date)
    if cached_close_rate:
        return cached_close_rate

    try:
        fetched_close_rate = _fetch_close_rate_from_yahoo(mapped_symbol, requested_date)
        return _upsert_cached_close_rate(symbol_id, fetched_close_rate, requested_date)
    except Exception as error:
        logger.warning(
            "yahoo historical close-rate fetch failed symbol_id=%s mapped_symbol=%s requested_date=%s error=%s",
            symbol_id,
            mapped_symbol,
            requested_date,
            repr(error),
            exc_info=True,
        )
        return cached_close_rate


def _infer_snapshot_shares(symbol_id: str, snapshot_lots: list[dict]) -> tuple[Decimal, list[str]]:
    inferred_shares = Decimal("0")
    missing_snapshot_dates = []
    for snapshot_lot in snapshot_lots:
        snapshot_date = snapshot_lot["snapshot_date"]
        close_rate = get_or_fetch_close_rate_on_or_before(symbol_id, snapshot_date)
        if not close_rate:
            missing_snapshot_dates.append(snapshot_date)
            continue

        inferred_shares += Decimal(str(snapshot_lot["snapshot_market_value_dollars"])) / Decimal(
            str(close_rate["close_price"])
        )

    return inferred_shares, missing_snapshot_dates


def enrich_positions_with_market_data(positions: list[dict]) -> list[dict]:
    """Attach latest close rates and gain metrics to aggregated positions.

    >>> enrich_positions_with_market_data([{'symbol_id': 'US BONDS 11/34', 'transaction_amount_dollars': 1000.0, 'shares': 0.0}])[0]['current_market_value_dollars']
    1000.0
    """
    enriched_positions = []
    for position in positions:
        transaction_amount_dollars = float(position["transaction_amount_dollars"])
        symbol_id = position["symbol_id"]
        explicit_shares = Decimal(str(position["shares"]))
        inferred_snapshot_shares, missing_snapshot_dates = _infer_snapshot_shares(
            symbol_id,
            position.get("snapshot_lots", []),
        )
        market_shares = explicit_shares + inferred_snapshot_shares
        if missing_snapshot_dates:
            raise ValueError(
                f"Portfolio snapshot asset {symbol_id} is missing close rates for snapshot dates "
                f"{missing_snapshot_dates}; cannot infer shares."
            )

        latest_close_rate = get_or_fetch_latest_close_rate(symbol_id) if market_shares != 0 else None
        if market_shares != 0 and latest_close_rate is None:
            raise ValueError(f"Portfolio market asset {symbol_id} has shares={float(market_shares)} but no close rate is available.")

        if latest_close_rate:
            current_price_per_share = float(latest_close_rate["close_price"])
            current_market_value_dollars = current_price_per_share * float(market_shares)
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
                "shares": float(explicit_shares),
                "inferred_snapshot_shares": float(inferred_snapshot_shares),
                "market_shares": float(market_shares),
                "current_price_per_share": current_price_per_share,
                "current_market_value_dollars": current_market_value_dollars,
                "total_dollar_gain": total_dollar_gain,
                "total_percent_change": total_percent_change,
                "latest_close_date": latest_close_rate["close_date"] if latest_close_rate else None,
            }
        )

    return sorted(enriched_positions, key=lambda position: position["current_market_value_dollars"], reverse=True)
