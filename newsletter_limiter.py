"""
Max-Min Fairness (Waterfilling) algorithm for distributing daily article quotas.

The algorithm equitably distributes a fixed number of slots among sources,
ensuring small sources get their full allocation before larger sources are capped.
"""


def calculate_quotas(source_counts: dict[str, int], total_limit: int) -> dict[str, int]:
    """
    Calculate per-source quotas using Max-Min Fairness algorithm.

    Args:
        source_counts: Dict mapping source_id to article count
        total_limit: Total number of articles to distribute

    Returns:
        Dict mapping source_id to allocated quota

    Algorithm:
        1. Filter out sources with 0 articles
        2. Calculate fair share = remaining_limit / active_sources
        3. Identify "fewers" (count <= fair_share) and "morers" (count > fair_share)
        4. Allocate full count to fewers, reduce remaining limit
        5. Repeat until all sources allocated or limit exhausted

    >>> result = calculate_quotas({'hn': 100, 'tldr': 15, 'blog': 1}, 50)
    >>> result['hn'] == 34 and result['tldr'] == 15 and result['blog'] == 1
    True

    >>> result = calculate_quotas({'a': 10, 'b': 10, 'c': 10}, 15)
    >>> result['a'] == 5 and result['b'] == 5 and result['c'] == 5
    True

    >>> calculate_quotas({'a': 100}, 50)
    {'a': 50}

    >>> calculate_quotas({}, 50)
    {}

    >>> result = calculate_quotas({'a': 5, 'b': 3}, 20)
    >>> result['a'] == 5 and result['b'] == 3
    True

    >>> calculate_quotas({'a': 0, 'b': 10}, 5)
    {'b': 5}
    """
    if total_limit <= 0:
        return {source: 0 for source in source_counts}

    active_sources = {s: c for s, c in source_counts.items() if c > 0}

    if not active_sources:
        return {}

    quotas = {}
    remaining_limit = total_limit

    while active_sources:
        fair_share = remaining_limit / len(active_sources)

        fewers = {s: c for s, c in active_sources.items() if c <= fair_share}
        morers = {s: c for s, c in active_sources.items() if c > fair_share}

        if fewers:
            for source, count in fewers.items():
                quotas[source] = count
                remaining_limit -= count
                del active_sources[source]
        else:
            for source in active_sources:
                quotas[source] = int(fair_share)
            break

    return quotas
