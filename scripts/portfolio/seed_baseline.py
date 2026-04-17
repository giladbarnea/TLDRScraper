from __future__ import annotations

import portfolio_service
import supabase_client

BASELINE_DATE = "2026-04-17"
BASELINE_MARKER_KEY = f"portfolio_app:baseline:{BASELINE_DATE}"

BASELINE_TRANSACTIONS = [
    ("AAPL", 3175.92, 0.0),
    ("AMD", 554.00, 0.0),
    ("AMZN", 9237.05, 0.0),
    ("CRWV", 2132.64, 0.0),
    ("GOOGL", 15104.10, 0.0),
    ("INMD", 7662.90, 0.0),
    ("MSFT", 5913.46, 0.0),
    ("MU", 1357.08, 0.0),
    ("NVDA", 15301.92, 0.0),
    ("SE", 273.66, 0.0),
    ("TBLA", 7740.90, 0.0),
    ("TSM", 4377.72, 0.0),
    ("VST", 1663.70, 0.0),
    ("TSLA", 8929.04, 0.0),
    ("HFG GY", 5894.39, 0.0),
    ("TA-125", 4000.00, 0.0),
    ("NAVITAS", 275.00, 0.0),
    ("SK HYNIX", 4000.00, 0.0),
    ("US BONDS 11/34", 40000.00, 0.0),
]


def baseline_already_seeded() -> bool:
    supabase = supabase_client.get_supabase_client()
    result = supabase.table("settings").select("key").eq("key", BASELINE_MARKER_KEY).execute()
    return len(result.data or []) > 0


def seed_baseline() -> None:
    if baseline_already_seeded():
        print("Baseline already seeded")
        return

    for symbol_id, transaction_amount_dollars, shares in BASELINE_TRANSACTIONS:
        transaction = portfolio_service.append_transaction(symbol_id, transaction_amount_dollars, shares)
        print(f"Seeded {transaction['symbol_id']} -> {transaction['transaction_amount_dollars']:.2f}")

    supabase = supabase_client.get_supabase_client()
    supabase.table("settings").insert(
        {
            "key": BASELINE_MARKER_KEY,
            "value": {
                "baseline_date": BASELINE_DATE,
                "transaction_count": len(BASELINE_TRANSACTIONS),
            },
        }
    ).execute()
    print("Baseline seed complete")


if __name__ == "__main__":
    seed_baseline()
