#!/usr/bin/env python3
"""Test Supabase connection and create tables if needed."""

import supabase_client

def test_connection():
    """Test basic Supabase connection."""
    try:
        client = supabase_client.get_supabase_client()
        print("✓ Successfully connected to Supabase")
        return client
    except Exception as e:
        print(f"✗ Failed to connect to Supabase: {e}")
        return None

def check_tables(client):
    """Check if required tables exist."""
    try:
        # Try to query the settings table
        result = client.table('settings').select('*').limit(1).execute()
        print("✓ 'settings' table exists")
    except Exception as e:
        print(f"✗ 'settings' table does not exist or error: {e}")

    try:
        # Try to query the daily_cache table
        result = client.table('daily_cache').select('*').limit(1).execute()
        print("✓ 'daily_cache' table exists")
    except Exception as e:
        print(f"✗ 'daily_cache' table does not exist or error: {e}")

if __name__ == "__main__":
    print("Testing Supabase connection...")
    client = test_connection()

    if client:
        print("\nChecking tables...")
        check_tables(client)