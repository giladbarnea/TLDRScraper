import supabase_client


def _normalize_daily_payload(payload, fallback_date=None):
    if payload is None:
        return None, False

    normalized_payload = dict(payload)
    changed = False

    payload_date = normalized_payload.get('date') or fallback_date
    if not payload_date:
        raise ValueError("Daily payload missing 'date'")

    if normalized_payload.get('date') != payload_date:
        normalized_payload['date'] = payload_date
        changed = True

    articles = normalized_payload.get('articles') or []
    normalized_articles = []

    for article in articles:
        normalized_article = dict(article)
        article_changed = False

        issue_date = (
            normalized_article.get('issueDate')
            or normalized_article.get('issue_date')
            or normalized_article.get('date')
            or payload_date
        )

        if issue_date is None:
            raise ValueError("Article missing issue date information")

        if normalized_article.get('issueDate') != issue_date:
            normalized_article['issueDate'] = issue_date
            article_changed = True

        if 'issue_date' in normalized_article:
            normalized_article.pop('issue_date')
            article_changed = True

        if 'date' in normalized_article:
            normalized_article.pop('date')
            article_changed = True

        normalized_articles.append(normalized_article)
        if article_changed:
            changed = True

    normalized_payload['articles'] = normalized_articles
    return normalized_payload, changed


def _upsert_daily_payload(date, payload):
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache').upsert({
        'date': date,
        'payload': payload
    }).execute()
    return result.data[0] if result.data else None

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
        raw_payload = result.data[0]['payload']
        payload, changed = _normalize_daily_payload(raw_payload, date)
        if changed:
            _upsert_daily_payload(payload['date'], payload)
        return payload
    return None

def set_daily_payload(date, payload):
    """
    Save or update daily payload (upsert).

    >>> set_daily_payload('2025-11-09', {'date': '2025-11-09', 'articles': [...]})
    {'date': '2025-11-09', 'payload': {...}, ...}
    """
    normalized_payload, _ = _normalize_daily_payload(payload, date)
    return _upsert_daily_payload(normalized_payload['date'], normalized_payload)

def get_daily_payloads_range(start_date, end_date):
    """
    Get all cached payloads in date range (inclusive).

    >>> get_daily_payloads_range('2025-11-07', '2025-11-09')
    [{'date': '2025-11-09', ...}, {'date': '2025-11-08', ...}, ...]
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache') \
        .select('payload') \
        .gte('date', start_date) \
        .lte('date', end_date) \
        .order('date', desc=True) \
        .execute()

    payloads = []
    for row in result.data:
        raw_payload = row['payload']
        payload, changed = _normalize_daily_payload(raw_payload)
        if changed:
            _upsert_daily_payload(payload['date'], payload)
        payloads.append(payload)

    return payloads

def is_date_cached(date):
    """
    Check if a specific date exists in cache.

    >>> is_date_cached('2025-11-09')
    True
    """
    supabase = supabase_client.get_supabase_client()
    result = supabase.table('daily_cache').select('date').eq('date', date).execute()

    return len(result.data) > 0
