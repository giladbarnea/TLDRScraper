from __future__ import annotations

import logging

from hidden_apps.portfolio import service

logger = logging.getLogger("hidden_apps.portfolio.api")
JsonResponse = tuple[dict[str, object], int]


def _error_response(message: str, error: Exception) -> JsonResponse:
    logger.error(
        "%s error=%s",
        message,
        repr(error),
        exc_info=True,
    )
    return {"success": False, "error": repr(error)}, 500


def list_transactions_response() -> JsonResponse:
    """Return portfolio transaction list payload and status.

    >>> isinstance(list_transactions_response(), tuple)
    True
    """
    try:
        transactions = service.list_transactions()
        return {"success": True, "transactions": transactions}, 200
    except Exception as error:
        return _error_response("portfolio transaction list failed", error)


def append_transaction_response(data: dict[str, object]) -> JsonResponse:
    """Append a portfolio transaction from request-shaped data.

    >>> append_transaction_response({"symbol_id": "AAPL", "transaction_amount_dollars": 1, "shares": 1}) # doctest: +SKIP
    ({'success': True, 'transaction': {...}}, 200)
    """
    try:
        transaction = service.append_transaction(
            symbol_id=str(data["symbol_id"]),
            transaction_amount_dollars=float(data["transaction_amount_dollars"]),
            shares=float(data["shares"]),
        )
        return {"success": True, "transaction": transaction}, 200
    except Exception as error:
        return _error_response("portfolio transaction append failed", error)


def _positions_payload(transactions: list[dict]) -> dict[str, object]:
    summarized_positions = service.summarize_positions(transactions)
    positions = service.enrich_positions_with_market_data(summarized_positions)
    return {"success": True, "positions": positions, "transactions": transactions}


def positions_response_for_transactions(transactions: list[dict]) -> JsonResponse:
    """Return positions response for caller-supplied transactions.

    >>> isinstance(positions_response_for_transactions([]), tuple)
    True
    """
    try:
        return _positions_payload(transactions), 200
    except Exception as error:
        return _error_response("portfolio positions failed", error)


def positions_response() -> JsonResponse:
    """Return enriched portfolio positions plus source transactions.

    >>> isinstance(positions_response(), tuple)
    True
    """
    try:
        return _positions_payload(service.list_transactions()), 200
    except Exception as error:
        return _error_response("portfolio positions failed", error)
