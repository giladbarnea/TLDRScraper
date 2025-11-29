import sys
import datetime
import os
from supabase_client import get_supabase_client

def clean_today():
    today = datetime.date.today().isoformat()
    print(f"Cleaning data for {today}...")
    try:
        supabase = get_supabase_client()
        response = supabase.table("daily_cache").delete().eq("date", today).execute()
        # Check if data attribute exists and is a list
        if hasattr(response, 'data') and isinstance(response.data, list):
             print(f"Deleted rows: {len(response.data)}")
        else:
             print("Deleted rows (count unknown, response.data not a list or missing)")

    except Exception as e:
        print(f"Error cleaning data: {e}")

if __name__ == "__main__":
    clean_today()
