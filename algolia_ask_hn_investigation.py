#!/usr/bin/env python3
"""
Deep dive investigation into Ask HN availability in Algolia API

Questions to answer:
1. Does Algolia have Ask HN posts at all?
2. How frequent are quality Ask HN posts?
3. What quality thresholds make sense for Ask HN?
4. Should Ask HN be treated differently than stories?
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict
import time


BASE_URL = "http://hn.algolia.com/api/v1"


def test_ask_hn_existence():
    """Test if Algolia has ANY Ask HN posts"""
    print("=" * 80)
    print("TEST 1: Does Algolia have Ask HN posts at all?")
    print("=" * 80)

    url = f"{BASE_URL}/search_by_date"
    params = {
        "tags": "ask_hn",
        "hitsPerPage": 100
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        total_hits = data.get('nbHits', 0)
        hits = data.get('hits', [])

        print(f"✅ Algolia HAS Ask HN posts!")
        print(f"   Total Ask HN posts indexed: {total_hits:,}")
        print(f"   Retrieved: {len(hits)} recent posts")

        if hits:
            # Show most recent
            print(f"\n   Most recent Ask HN posts:")
            for i, hit in enumerate(hits[:5], 1):
                created = datetime.fromtimestamp(hit['created_at_i'])
                print(f"   {i}. [{hit.get('points', 0)} pts, {hit.get('num_comments', 0)} cmts] {hit.get('title', '')[:60]}")
                print(f"      {created.strftime('%Y-%m-%d %H:%M')} - {hit.get('url', 'no url')}")

        return True
    else:
        print(f"❌ Error: {response.status_code}")
        return False


def test_ask_hn_across_dates():
    """Test Ask HN availability across last 7 days"""
    print("\n" + "=" * 80)
    print("TEST 2: Ask HN Volume Across Last 7 Days")
    print("=" * 80)

    results = []

    for days_ago in range(7):
        target_date = datetime.now() - timedelta(days=days_ago)
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=0)

        start_ts = int(start_of_day.timestamp())
        end_ts = int(end_of_day.timestamp())
        date_str = target_date.strftime('%Y-%m-%d')

        url = f"{BASE_URL}/search_by_date"
        params = {
            "tags": "ask_hn",
            "numericFilters": f"created_at_i>{start_ts},created_at_i<{end_ts}",
            "hitsPerPage": 100
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            hits = response.json().get('hits', [])

            # Calculate stats
            total = len(hits)
            with_points = [h for h in hits if h.get('points', 0) > 0]
            quality_10 = [h for h in hits if h.get('points', 0) >= 10]
            quality_20 = [h for h in hits if h.get('points', 0) >= 20]
            quality_50 = [h for h in hits if h.get('points', 0) >= 50]

            results.append({
                'date': date_str,
                'total': total,
                'with_points': len(with_points),
                'pts_10+': len(quality_10),
                'pts_20+': len(quality_20),
                'pts_50+': len(quality_50),
                'hits': hits
            })

            print(f"{date_str}: Total={total:3}, Points>0={len(with_points):3}, >=10pts={len(quality_10):3}, >=20pts={len(quality_20):3}, >=50pts={len(quality_50):3}")

        time.sleep(0.2)  # Be nice to API

    # Summary
    print(f"\n{'Summary across 7 days:':40}")
    print(f"  Average Ask HN posts per day: {sum(r['total'] for r in results) / 7:.1f}")
    print(f"  Average with >=10 points: {sum(r['pts_10+'] for r in results) / 7:.1f}")
    print(f"  Average with >=20 points: {sum(r['pts_20+'] for r in results) / 7:.1f}")
    print(f"  Average with >=50 points: {sum(r['pts_50+'] for r in results) / 7:.1f}")

    return results


def test_quality_thresholds_for_ask_hn(date_results):
    """Test different quality thresholds for Ask HN"""
    print("\n" + "=" * 80)
    print("TEST 3: What Quality Threshold Makes Sense for Ask HN?")
    print("=" * 80)

    # Use yesterday's data (most complete)
    yesterday = date_results[1] if len(date_results) > 1 else date_results[0]
    hits = yesterday['hits']

    if not hits:
        print("⚠️  No Ask HN posts found for yesterday. Using most recent date with data.")
        for result in date_results:
            if result['hits']:
                yesterday = result
                hits = result['hits']
                break

    print(f"\nAnalyzing {yesterday['date']} ({len(hits)} Ask HN posts)")

    # Calculate score distribution
    scores = []
    for hit in hits:
        points = hit.get('points', 0)
        comments = hit.get('num_comments', 0)
        leading_score = (2 * points) + comments
        scores.append({
            'title': hit.get('title', ''),
            'points': points,
            'comments': comments,
            'leading_score': leading_score,
            'created_at': datetime.fromtimestamp(hit['created_at_i'])
        })

    scores.sort(key=lambda x: x['leading_score'], reverse=True)

    # Show distribution
    if scores:
        leading_scores = [s['leading_score'] for s in scores]
        print(f"\nLeading Score Distribution:")
        print(f"  Max: {max(leading_scores)}")
        print(f"  75th percentile: {sorted(leading_scores)[int(len(leading_scores) * 0.75)]}")
        print(f"  Median: {sorted(leading_scores)[len(leading_scores) // 2]}")
        print(f"  25th percentile: {sorted(leading_scores)[int(len(leading_scores) * 0.25)]}")
        print(f"  Min: {min(leading_scores)}")

        print(f"\nCount by threshold:")
        thresholds = [5, 10, 15, 20, 30, 50, 100]
        for threshold in thresholds:
            count = len([s for s in scores if s['leading_score'] >= threshold])
            percentage = 100 * count / len(scores)
            print(f"  Leading score >= {threshold:3}: {count:3} posts ({percentage:5.1f}%)")

        print(f"\nTop 10 Ask HN by leading_score:")
        for i, s in enumerate(scores[:10], 1):
            print(f"  {i:2}. [Score: {s['leading_score']:3}] {s['points']:3}pts, {s['comments']:3}cmts - {s['title'][:55]}")


def compare_types_across_dates():
    """Compare Ask HN volume with other story types"""
    print("\n" + "=" * 80)
    print("TEST 4: Ask HN vs Story vs Show HN Volume Comparison")
    print("=" * 80)

    target_date = datetime.now() - timedelta(days=1)
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=0)

    start_ts = int(start_of_day.timestamp())
    end_ts = int(end_of_day.timestamp())
    date_str = target_date.strftime('%Y-%m-%d')

    types = ['story', 'ask_hn', 'show_hn']
    results = {}

    print(f"\nDate: {date_str}")
    print(f"\n{'Type':<12} {'Total':<8} {'>=10pts':<10} {'>=20pts':<10} {'>=50pts':<10} {'Avg Score':<12}")
    print("-" * 70)

    for story_type in types:
        url = f"{BASE_URL}/search_by_date"
        params = {
            "tags": story_type,
            "numericFilters": f"created_at_i>{start_ts},created_at_i<{end_ts}",
            "hitsPerPage": 100
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            hits = response.json().get('hits', [])

            scores = []
            for hit in hits:
                points = hit.get('points', 0)
                comments = hit.get('num_comments', 0)
                leading_score = (2 * points) + comments
                scores.append(leading_score)

            total = len(hits)
            pts_10 = len([s for s in scores if s >= 10])
            pts_20 = len([s for s in scores if s >= 20])
            pts_50 = len([s for s in scores if s >= 50])
            avg_score = sum(scores) / len(scores) if scores else 0

            results[story_type] = {
                'total': total,
                'pts_10+': pts_10,
                'pts_20+': pts_20,
                'pts_50+': pts_50,
                'avg_score': avg_score
            }

            print(f"{story_type:<12} {total:<8} {pts_10:<10} {pts_20:<10} {pts_50:<10} {avg_score:<12.1f}")

        time.sleep(0.2)

    # Analysis
    print(f"\n{'Analysis:':40}")
    if results.get('story') and results.get('ask_hn'):
        ratio = results['ask_hn']['total'] / results['story']['total'] * 100
        print(f"  Ask HN is {ratio:.1f}% the volume of regular stories")

        quality_ratio = results['ask_hn']['pts_20+'] / results['story']['pts_20+'] * 100 if results['story']['pts_20+'] > 0 else 0
        print(f"  Quality Ask HN (>=20pts) is {quality_ratio:.1f}% of quality stories")


def test_ask_hn_with_filters():
    """Test Ask HN with different filter combinations"""
    print("\n" + "=" * 80)
    print("TEST 5: Ask HN with Different Filter Combinations")
    print("=" * 80)

    yesterday = datetime.now() - timedelta(days=1)
    start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)

    start_ts = int(start_of_day.timestamp())
    end_ts = int(end_of_day.timestamp())
    date_str = yesterday.strftime('%Y-%m-%d')

    print(f"\nDate: {date_str}")
    print(f"\n{'Filter':<40} {'Count':<8} {'Top Score'}")
    print("-" * 60)

    filter_configs = [
        ("No quality filter", ""),
        ("Points >= 5", ",points>=5"),
        ("Points >= 10", ",points>=10"),
        ("Points >= 15", ",points>=15"),
        ("Points >= 20", ",points>=20"),
        ("Points >= 10, Comments >= 3", ",points>=10,num_comments>=3"),
        ("Points >= 15, Comments >= 5", ",points>=15,num_comments>=5"),
        ("Points >= 20, Comments >= 10", ",points>=20,num_comments>=10"),
    ]

    for label, filter_str in filter_configs:
        url = f"{BASE_URL}/search_by_date"
        params = {
            "tags": "ask_hn",
            "numericFilters": f"created_at_i>{start_ts},created_at_i<{end_ts}{filter_str}",
            "hitsPerPage": 50
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            hits = response.json().get('hits', [])

            if hits:
                top_score = max((2 * h.get('points', 0)) + h.get('num_comments', 0) for h in hits)
                print(f"{label:<40} {len(hits):<8} {top_score}")
            else:
                print(f"{label:<40} {0:<8} N/A")

        time.sleep(0.15)


def recommendation():
    """Provide recommendation for Ask HN strategy"""
    print("\n" + "=" * 80)
    print("RECOMMENDATION FOR ASK HN HANDLING")
    print("=" * 80)

    print("""
    Based on the investigation:

    1. ✅ Algolia DOES have Ask HN posts
    2. Ask HN posts are less frequent than regular stories
    3. Ask HN posts generally have lower scores than top stories
    4. Quality Ask HN posts (worthy of inclusion) exist but are rarer

    Recommended Strategy for Ask HN:

    Option A: Include Ask HN in combined query with LOWER threshold
    -----------------------------------------------------------------
    Regular query:
      tags: "(story,show_hn)"
      filters: "points>=30,num_comments>=5"

    Separate Ask HN query:
      tags: "ask_hn"
      filters: "points>=15,num_comments>=3"  ← Lower bar

    Rationale: Ask HN is conversational by nature, so engagement matters
    more than raw points. This ensures you catch quality discussions.

    Option B: Include Ask HN in combined query with same threshold
    ---------------------------------------------------------------
    Single query:
      tags: "(story,ask_hn,show_hn)"
      filters: "points>=30,num_comments>=5"

    Rationale: Simplest approach. If an Ask HN post hits the quality bar,
    it's included. If not, it's filtered out. Natural selection.

    Option C: Skip Ask HN entirely
    -------------------------------
    Only fetch: tags="(story,show_hn)"

    Rationale: If Ask HN posts rarely meet your quality bar, why fetch them?
    Focus on regular stories and Show HN which have higher hit rates.

    ⚡ QUICK WIN: Start with Option B (combined query, same threshold)
       - Test for a week
       - Measure how many Ask HN posts make the cut
       - If too few (<5%), consider Option C (skip it)
       - If too many low-quality, use Option A (separate with lower bar)
    """)


def main():
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*22 + "ASK HN DEEP DIVE INVESTIGATION" + " "*25 + "║")
    print("╚" + "="*78 + "╝")
    print()

    # Test 1: Does Algolia have Ask HN?
    has_ask_hn = test_ask_hn_existence()
    time.sleep(0.5)

    if not has_ask_hn:
        print("\n❌ Algolia doesn't have Ask HN posts. Investigation complete.")
        return

    # Test 2: Volume across dates
    date_results = test_ask_hn_across_dates()
    time.sleep(0.5)

    # Test 3: Quality thresholds
    test_quality_thresholds_for_ask_hn(date_results)
    time.sleep(0.5)

    # Test 4: Compare with other types
    compare_types_across_dates()
    time.sleep(0.5)

    # Test 5: Filter combinations
    test_ask_hn_with_filters()

    # Final recommendation
    recommendation()

    print("\n" + "="*80)
    print("Investigation complete!")
    print("="*80)


if __name__ == "__main__":
    main()
