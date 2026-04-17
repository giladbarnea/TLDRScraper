import logging
import time

import supabase_client


logger = logging.getLogger("storage_service")
_seen_urls_table_probe_completed = False
_seen_urls_table_is_available = True
_seen_urls_probe_retry_after_monotonic_seconds = 0.0
_SEEN_URLS_PROBE_RETRY_INTERVAL_SECONDS = 30.0

def get_setting(key):
    """
    Get setting value by key.

    >>> get_setting('ui:theme')
    'dark'
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('settings').select('value').eq('key', key).execute()

    if result.data:
        return result.data[0]['value']
    return None

def set_setting(key, value):
    """
    Set setting value by key (upsert).

    >>> set_setting('ui:theme', 'light')
    {'key': 'ui:theme', 'value': 'light', ...}
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


def get_daily_payload_row(date):
    """Get payload and optimistic concurrency timestamp for a specific date."""
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache').select('payload, cached_at').eq('date', date).execute()
    if not result.data:
        return None
    row = result.data[0]
    payload = row['payload']
    updated_at = payload.get('storage_updated_at') or row['cached_at']
    return {
        'payload': payload,
        'updated_at': updated_at,
    }

def set_daily_payload(date, payload):
    """
    Save or update daily payload (upsert).
    Does NOT update cached_at - use set_daily_payload_from_scrape() for scrape results.
    This path is for user-state updates (read/removed/TLDR) and must not advance cached_at,
    which tracks scrape freshness only.

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

    cached_at reflects the last scrape time and is only advanced by
    set_daily_payload_from_scrape().

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


def patch_daily_article(date, url, patch, expected_updated_at):
    """Atomically patch one article in daily_cache payload using RPC."""
    supabase = supabase_client.get_supabase_client()
    result = supabase.rpc(
        'patch_daily_article',
        {
            'target_date': date,
            'article_url': url,
            'article_patch': patch,
            'expected_updated_at': expected_updated_at,
        },
    ).execute()
    if not result.data:
        raise RuntimeError("patch_daily_article RPC returned no rows")
    return result.data[0]


def get_digest(digest_id: str) -> dict | None:
    """Return cached digest row for digest_id, or None on miss or error.

    >>> get_digest("nonexistent_id_that_does_not_exist") is None
    True
    """
    try:
        supabase = supabase_client.get_supabase_client()
        result = (
            supabase.table('digests')
            .select('markdown, included_urls, article_count, effort')
            .eq('digest_id', digest_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as error:
        logger.warning(
            "get_digest failed; treating as cache miss digest_id_prefix=%s error=%s",
            digest_id[:8],
            repr(error),
        )
        return None


def set_digest(
    digest_id: str,
    markdown: str,
    included_urls: list[str],
    article_count: int,
    effort: str,
) -> None:
    """Persist a generated digest to the cache table (upsert).

    >>> set_digest("test_id", "# Digest", ["a.com/1"], 1, "low")
    """
    try:
        supabase = supabase_client.get_supabase_client()
        supabase.table('digests').upsert({
            'digest_id': digest_id,
            'markdown': markdown,
            'included_urls': included_urls,
            'article_count': article_count,
            'effort': effort,
        }).execute()
    except Exception as error:
        logger.warning(
            "set_digest failed; result not cached digest_id_prefix=%s error=%s",
            digest_id[:8],
            repr(error),
        )


def _probe_seen_urls_table_once() -> bool:
    """Probe seen_urls table availability and retry after transient failures.

    >>> isinstance(_probe_seen_urls_table_once(), bool)
    True
    """
    global _seen_urls_table_probe_completed
    global _seen_urls_table_is_available
    global _seen_urls_probe_retry_after_monotonic_seconds

    if _seen_urls_table_probe_completed and _seen_urls_table_is_available:
        return True

    current_time = time.monotonic()
    if current_time < _seen_urls_probe_retry_after_monotonic_seconds:
        return False

    try:
        supabase = supabase_client.get_supabase_client()
        supabase.table('seen_urls').select('canonical_url').limit(1).execute()
        _seen_urls_table_probe_completed = True
        _seen_urls_table_is_available = True
        _seen_urls_probe_retry_after_monotonic_seconds = 0.0
        return True
    except Exception as error:
        _seen_urls_table_probe_completed = False
        _seen_urls_table_is_available = False
        _seen_urls_probe_retry_after_monotonic_seconds = (
            current_time + _SEEN_URLS_PROBE_RETRY_INTERVAL_SECONDS
        )
        logger.warning(
            "seen_urls table probe failed; history dedup temporarily disabled retry_in_seconds=%s error=%s",
            int(_SEEN_URLS_PROBE_RETRY_INTERVAL_SECONDS),
            repr(error),
            exc_info=True,
        )
        return False


def filter_new_urls_for_history_dedup(
    source_id: str,
    first_seen_date: str,
    canonical_urls: list[str],
) -> set[str]:
    """Return URLs not yet seen globally, and persist them into seen_urls.

    >>> filter_new_urls_for_history_dedup('example_source', '2026-03-08', [])
    set()
    """
    if not canonical_urls:
        return set()

    if not _probe_seen_urls_table_once():
        return set(canonical_urls)

    supabase = supabase_client.get_supabase_client()
    unique_canonical_urls = list(dict.fromkeys(canonical_urls))
    try:
        existing_rows = (
            supabase.table('seen_urls')
            .select('canonical_url')
            .in_('canonical_url', unique_canonical_urls)
            .execute()
        )
    except Exception as error:
        logger.warning(
            "failed reading seen_urls; history dedup bypassed for source_id=%s error=%s",
            source_id,
            repr(error),
            exc_info=True,
        )
        return set(unique_canonical_urls)

    existing_canonical_urls = {
        row['canonical_url'] for row in (existing_rows.data or []) if row.get('canonical_url')
    }
    new_canonical_urls = [
        canonical_url
        for canonical_url in unique_canonical_urls
        if canonical_url not in existing_canonical_urls
    ]

    if not new_canonical_urls:
        return set()

    rows_to_insert = [
        {
            'canonical_url': canonical_url,
            'source_id': source_id,
            'first_seen_date': first_seen_date,
        }
        for canonical_url in new_canonical_urls
    ]

    try:
        supabase.table('seen_urls').upsert(rows_to_insert).execute()
    except Exception as error:
        logger.warning(
            "failed writing seen_urls; continuing with current scrape source_id=%s error=%s",
            source_id,
            repr(error),
            exc_info=True,
        )

    return set(new_canonical_urls)
