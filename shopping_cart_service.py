from __future__ import annotations

from datetime import datetime, timezone
import uuid

import supabase_client


def list_shopping_cart_entries() -> list[dict]:
    supabase = supabase_client.get_supabase_client()
    result = (
        supabase.table("shopping_cart_entries")
        .select("id,person_name,product_name,input_date,created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def append_shopping_cart_entry(person_name: str, product_name: str) -> dict:
    now_utc = datetime.now(timezone.utc)
    shopping_cart_entry = {
        "id": str(uuid.uuid4()),
        "person_name": person_name,
        "product_name": product_name,
        "input_date": now_utc.date().isoformat(),
        "created_at": now_utc.isoformat(),
    }

    supabase = supabase_client.get_supabase_client()
    supabase.table("shopping_cart_entries").insert(shopping_cart_entry).execute()
    return shopping_cart_entry
