#!/usr/bin/env python3
"""Debug Supabase connection issues."""

import os
import util

def debug_env_vars():
    """Print Supabase environment variables for debugging."""
    url = util.resolve_env_var("SUPABASE_URL")
    key_exists = bool(util.resolve_env_var("SUPABASE_SERVICE_KEY"))

    print(f"SUPABASE_URL: {url}")
    print(f"SUPABASE_URL length: {len(url)}")
    print(f"SUPABASE_SERVICE_KEY exists: {key_exists}")

    # Check if URL looks valid
    if url:
        if not url.startswith("https://"):
            print("⚠ URL doesn't start with https://")
        if not url.endswith(".supabase.co"):
            print("⚠ URL doesn't end with .supabase.co")
        else:
            print("✓ URL format looks correct")

    return url

if __name__ == "__main__":
    print("Debugging Supabase configuration...")
    debug_env_vars()