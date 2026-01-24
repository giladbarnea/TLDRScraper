import supabase_client

def get_setting(key):
    """
    Get setting value by key.

    >>> get_setting('cache:enabled')
    True
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('settings').select('value').eq('key', key).execute()

    if result.data:
        return result.data[0]['value']
    return None

def set_setting(key, value):
    """
    Set setting value by key (upsert).

    >>> set_setting('cache:enabled', False)
    {'key': 'cache:enabled', 'value': False, ...}
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('settings').upsert({
        'key': key,
        'value': value
    }).execute()

    return result.data[0] if result.data else None

def get_daily_payload(date):
    """
    Get cached payload for a specific date.

    >>> get_daily_payload('2025-11-09')
    {'date': '2025-11-09', 'articles': [...], ...}
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache').select('payload').eq('date', date).execute()

    if result.data:
        return result.data[0]['payload']
    return None

def set_daily_payload(date, payload):
    """
    Save or update daily payload (upsert).
    Does NOT update cached_at - use set_daily_payload_from_scrape() for scrape results.

    >>> set_daily_payload('2025-11-09', {'date': '2025-11-09', 'articles': [...]})
    {'date': '2025-11-09', 'payload': {...}, ...}
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache').upsert({
        'date': date,
        'payload': payload
    }).execute()

    return result.data[0] if result.data else None

def set_daily_payload_from_scrape(date, payload):
    """
    Save or update daily payload from a scrape operation (upsert).
    Updates cached_at to current timestamp to track scrape freshness.

    >>> set_daily_payload_from_scrape('2025-11-09', {'date': '2025-11-09', 'articles': [...]})
    {'date': '2025-11-09', 'payload': {...}, 'cached_at': '...'}
    """
    from datetime import datetime, timezone
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache').upsert({
        'date': date,
        'payload': payload,
        'cached_at': datetime.now(timezone.utc).isoformat()
    }).execute()

    return result.data[0] if result.data else None

def get_daily_payloads_range(start_date, end_date):
    """
    Get all cached payloads in date range (inclusive).

    >>> get_daily_payloads_range('2025-11-07', '2025-11-09')
    [{'date': '2025-11-09', 'payload': {...}, 'cached_at': '...'}, ...]
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache') \
        .select('date, payload, cached_at') \
        .gte('date', start_date) \
        .lte('date', end_date) \
        .order('date', desc=True) \
        .execute()

    return [
        {'date': row['date'], 'payload': row['payload'], 'cached_at': row['cached_at']}
        for row in result.data
    ]

def is_date_cached(date):
    """
    Check if a specific date exists in cache.

    >>> is_date_cached('2025-11-09')
    True
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache').select('date').eq('date', date).execute()

    return len(result.data) > 0