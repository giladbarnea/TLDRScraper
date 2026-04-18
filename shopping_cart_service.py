from __future__ import annotations

from datetime import datetime, timezone
import logging
import uuid

import supabase_client

logger = logging.getLogger("shopping_cart_service")

SHOPPING_CART_TABLE_NAME = "shopping_cart_entries"
SHOPPING_CART_SETTINGS_NAMESPACE_PREFIX = "shopping_cart_app:item:"
_STORAGE_MODE_TABLE = "table"
_STORAGE_MODE_SETTINGS_NAMESPACE = "settings_namespace"
_storage_mode: str | None = None


def _is_missing_table_error(error: Exception) -> bool:
    error_message = repr(error)
    return "PGRST205" in error_message and SHOPPING_CART_TABLE_NAME in error_message


def _build_settings_namespace_key(created_at_iso_timestamp: str, entry_id: str) -> str:
    """Build a lexicographically sortable namespaced settings key.

    >>> _build_settings_namespace_key("2026-04-18T05:00:00+00:00", "abc")
    'shopping_cart_app:item:2026-04-18T05:00:00+00:00:abc'
    """
    return f"{SHOPPING_CART_SETTINGS_NAMESPACE_PREFIX}{created_at_iso_timestamp}:{entry_id}"


def _normalize_price_in_dollars(raw_price_in_dollars: float | int | None) -> float:
    """Normalize optional client input to a persisted non-null price.

    >>> _normalize_price_in_dollars(None)
    0.0
    >>> _normalize_price_in_dollars(12)
    12.0
    """
    return float(raw_price_in_dollars) if raw_price_in_dollars is not None else 0.0


def _normalize_entry(shopping_cart_entry: dict) -> dict:
    return {
        **shopping_cart_entry,
        "price_in_dollars": _normalize_price_in_dollars(shopping_cart_entry.get("price_in_dollars")),
    }


def _resolve_storage_mode() -> str:
    global _storage_mode
    if _storage_mode is not None:
        return _storage_mode

    supabase = supabase_client.get_supabase_client()
    try:
        supabase.table(SHOPPING_CART_TABLE_NAME).select("id").limit(1).execute()
        _storage_mode = _STORAGE_MODE_TABLE
        return _storage_mode
    except Exception as error:
        if _is_missing_table_error(error):
            logger.warning(
                "shopping cart table missing; falling back to settings namespace prefix=%s error=%s",
                SHOPPING_CART_SETTINGS_NAMESPACE_PREFIX,
                repr(error),
            )
            _storage_mode = _STORAGE_MODE_SETTINGS_NAMESPACE
            return _storage_mode
        raise


def _list_entries_from_settings_namespace() -> list[dict]:
    supabase = supabase_client.get_supabase_client()
    result = (
        supabase.table("settings")
        .select("value")
        .like("key", f"{SHOPPING_CART_SETTINGS_NAMESPACE_PREFIX}%")
        .order("key", desc=True)
        .execute()
    )
    return [_normalize_entry(row["value"]) for row in (result.data or [])]


def _append_entry_to_settings_namespace(shopping_cart_entry: dict) -> None:
    entry_key = _build_settings_namespace_key(
        created_at_iso_timestamp=shopping_cart_entry["created_at"],
        entry_id=shopping_cart_entry["id"],
    )
    supabase = supabase_client.get_supabase_client()
    supabase.table("settings").insert({"key": entry_key, "value": shopping_cart_entry}).execute()


def list_shopping_cart_entries() -> list[dict]:
    storage_mode = _resolve_storage_mode()
    if storage_mode == _STORAGE_MODE_TABLE:
        supabase = supabase_client.get_supabase_client()
        result = (
            supabase.table(SHOPPING_CART_TABLE_NAME)
            .select("id,person_name,product_name,price_in_dollars,input_date,created_at")
            .order("created_at", desc=True)
            .execute()
        )
        return [_normalize_entry(shopping_cart_entry) for shopping_cart_entry in (result.data or [])]

    return _list_entries_from_settings_namespace()


def append_shopping_cart_entry(person_name: str, product_name: str, price_in_dollars: float | None) -> dict:
    now_utc = datetime.now(timezone.utc)
    shopping_cart_entry = {
        "id": str(uuid.uuid4()),
        "person_name": person_name,
        "product_name": product_name,
        "price_in_dollars": _normalize_price_in_dollars(price_in_dollars),
        "input_date": now_utc.date().isoformat(),
        "created_at": now_utc.isoformat(),
    }

    storage_mode = _resolve_storage_mode()
    if storage_mode == _STORAGE_MODE_TABLE:
        supabase = supabase_client.get_supabase_client()
        try:
            supabase.table(SHOPPING_CART_TABLE_NAME).insert(shopping_cart_entry).execute()
            return shopping_cart_entry
        except Exception as error:
            if _is_missing_table_error(error):
                global _storage_mode
                _storage_mode = _STORAGE_MODE_SETTINGS_NAMESPACE
                logger.warning(
                    "shopping cart table missing during insert; switching to settings namespace prefix=%s error=%s",
                    SHOPPING_CART_SETTINGS_NAMESPACE_PREFIX,
                    repr(error),
                )
            else:
                raise

    _append_entry_to_settings_namespace(shopping_cart_entry)
    return shopping_cart_entry
