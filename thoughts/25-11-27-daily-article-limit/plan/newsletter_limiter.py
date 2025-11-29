# newsletter_limiter.py
"""
Implements the distribution logic for daily article limits.
Uses Max-Min Fairness (Waterfilling) to allocate slots equitably among sources.
"""

def calculate_quotas(source_counts: dict[str, int], total_limit: int = 50) -> dict[str, int]:
    """
    Calculates the maximum number of articles allowed per source using Max-Min Fairness.

    Args:
        source_counts: Dictionary mapping source_id to available article count (excluding removed).
        total_limit: The maximum global number of articles to display.

    Returns:
        Dictionary mapping source_id to their allocated quota.
    """
    # 1. Initialize quotas dictionary with 0 for all sources
    # quotas = {source: 0 for source in source_counts}
    
    # 2. Identify active sources (those with > 0 articles)
    # active_sources = [s for s, count in source_counts.items() if count > 0]
    # remaining_limit = total_limit

    # 3. Main Allocation Loop
    # while active_sources is not empty AND remaining_limit > 0:
        
        # A. Calculate Fair Share
        # fair_share = remaining_limit // len(active_sources)
        
        # B. Identify "Fewers" and "Morers"
        # fewers = []
        # morers = []
        # for source in active_sources:
            # if source_counts[source] <= fair_share:
                # fewers.append(source)
            # else:
                # morers.append(source)
        
        # C. Branch: Handle "Fewers" (Optimization Step)
        # if len(fewers) > 0:
            # For each source in fewers:
                # Allocate full count: quotas[source] = source_counts[source]
                # Reduce limit: remaining_limit -= source_counts[source]
                # Remove from active_sources
            # Continue to next iteration (re-calculate share for Morers)
            
        # D. Branch: Handle "Morers" only (Final Distribution)
        # else:
            # base_allocation = remaining_limit // len(active_sources)
            # remainder = remaining_limit % len(active_sources)
            
            # For each source in active_sources (which are all morers now):
                # quotas[source] = base_allocation
                # If remainder > 0:
                    # quotas[source] += 1
                    # remainder -= 1
            
            # remaining_limit = 0
            # active_sources = []
            
    # 4. Return final quotas