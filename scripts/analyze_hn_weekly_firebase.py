"""
Fetch 4 weeks of HackerNews data using Firebase API.

Works around SSL/TLS proxy issues by using the official Firebase API
which successfully negotiates through the Claude Code proxy.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/hn_firebase_analysis.log')
    ]
)
logger = logging.getLogger(__name__)

# Persistence paths
RESULTS_DIR = Path('/tmp/hn_firebase_results')
RESULTS_DIR.mkdir(exist_ok=True)
STATS_FILE = RESULTS_DIR / 'weekly_stats.json'

# HN Firebase API base
HN_API = "https://hacker-news.firebaseio.com/v0"

# Quality thresholds (matching the adapter)
MIN_SCORE = 30
MIN_COMMENTS = 5


def fetch_story(story_id):
    """Fetch individual story from Firebase API."""
    try:
        url = f"{HN_API}/item/{story_id}.json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch story {story_id}: {e}")
        return None


def fetch_stories_for_date(target_date):
    """
    Fetch stories for a specific date using Firebase API.

    Since Firebase doesn't support date filtering, we:
    1. Fetch recent story lists (top, new, ask, show)
    2. Fetch individual stories
    3. Filter by date and quality thresholds
    """
    logger.info(f"Fetching stories for {target_date.strftime('%Y-%m-%d')}")

    start_of_day = target_date.replace(hour=0, minute=0, second=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59)

    start_timestamp = int(start_of_day.timestamp())
    end_timestamp = int(end_of_day.timestamp())

    # Fetch story ID lists
    story_lists = {
        'top': f"{HN_API}/topstories.json",
        'new': f"{HN_API}/newstories.json",
        'ask': f"{HN_API}/askstories.json",
        'show': f"{HN_API}/showstories.json"
    }

    all_story_ids = set()

    for story_type, url in story_lists.items():
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            story_ids = response.json()

            # Sample first 100 to keep it reasonable
            all_story_ids.update(story_ids[:100])
            logger.info(f"  Fetched {len(story_ids[:100])} {story_type} story IDs")
        except Exception as e:
            logger.error(f"Failed to fetch {story_type} stories: {e}")

    logger.info(f"  Total unique story IDs to check: {len(all_story_ids)}")

    # Fetch individual stories and filter
    matching_stories = []

    for idx, story_id in enumerate(all_story_ids):
        if idx % 50 == 0:
            logger.info(f"  Progress: {idx}/{len(all_story_ids)} stories checked")

        story = fetch_story(story_id)
        if not story:
            continue

        # Check if story matches our date range
        story_time = story.get('time', 0)
        if not (start_timestamp <= story_time <= end_timestamp):
            continue

        # Check quality thresholds
        score = story.get('score', 0)
        descendants = story.get('descendants', 0)  # comment count

        if score < MIN_SCORE or descendants < MIN_COMMENTS:
            continue

        # Check if it has a URL (skip text-only posts)
        if not story.get('url'):
            continue

        # Determine category
        story_type = story.get('type', 'story')
        title = story.get('title', '')

        if 'Ask HN' in title or story_type == 'ask':
            category = 'HN Ask'
        elif 'Show HN' in title or story_type == 'show':
            category = 'HN Show'
        else:
            category = 'HN Top'

        matching_stories.append({
            'id': story.get('id'),
            'title': title,
            'url': story.get('url'),
            'score': score,
            'comments': descendants,
            'category': category,
            'timestamp': story_time
        })

        # Rate limiting
        time.sleep(0.1)

    logger.info(f"  Found {len(matching_stories)} matching stories for {target_date.strftime('%Y-%m-%d')}")
    return matching_stories


def analyze_weekly_data(weeks=4):
    """Fetch and analyze data for the specified number of weeks."""
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=weeks)

    logger.info(f"Analyzing {weeks} weeks from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # Sample every 3rd day to reduce API calls (still gives good average)
    dates_to_check = []
    current = start_date
    while current <= end_date:
        dates_to_check.append(current)
        current += timedelta(days=3)

    logger.info(f"Will sample {len(dates_to_check)} dates (every 3 days) to estimate weekly average")

    all_stories_by_date = {}

    for date in dates_to_check:
        stories = fetch_stories_for_date(date)
        date_str = date.strftime('%Y-%m-%d')
        all_stories_by_date[date_str] = stories

        # Save daily results
        daily_file = RESULTS_DIR / f'{date_str}.json'
        with open(daily_file, 'w') as f:
            json.dump(stories, f, indent=2)

    # Calculate weekly statistics
    weekly_stats = {}
    total_articles = 0

    for date_str, stories in all_stories_by_date.items():
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        week_key = date_obj.strftime('%Y-W%U')

        if week_key not in weekly_stats:
            weekly_stats[week_key] = {
                'total_articles': 0,
                'sampled_days': 0,
                'by_category': {},
                'dates': []
            }

        weekly_stats[week_key]['total_articles'] += len(stories)
        weekly_stats[week_key]['sampled_days'] += 1
        weekly_stats[week_key]['dates'].append(date_str)
        total_articles += len(stories)

        for story in stories:
            category = story.get('category', 'Unknown')
            if category not in weekly_stats[week_key]['by_category']:
                weekly_stats[week_key]['by_category'][category] = 0
            weekly_stats[week_key]['by_category'][category] += 1

    # Extrapolate to full weeks (we sample every 3 days, so ~2.3 samples per week)
    # 7 days / 3 = 2.33 samples per week
    for week_key in weekly_stats:
        sampled_days = weekly_stats[week_key]['sampled_days']
        if sampled_days > 0:
            # Extrapolate: (articles per sampled days) * (7 days / days between samples)
            weekly_stats[week_key]['extrapolated_weekly_total'] = round(
                weekly_stats[week_key]['total_articles'] * (7 / (sampled_days * 3))
            )

    num_weeks = len(weekly_stats)
    total_extrapolated = sum(w['extrapolated_weekly_total'] for w in weekly_stats.values())
    avg_per_week = total_extrapolated / num_weeks if num_weeks > 0 else 0

    stats = {
        'methodology': 'Sampled every 3 days, extrapolated to weekly totals',
        'dates_sampled': len(dates_to_check),
        'total_articles_sampled': total_articles,
        'num_weeks': num_weeks,
        'total_extrapolated_weekly': total_extrapolated,
        'avg_articles_per_week': round(avg_per_week, 2),
        'quality_thresholds': {
            'min_score': MIN_SCORE,
            'min_comments': MIN_COMMENTS
        },
        'weekly_breakdown': weekly_stats
    }

    # Save stats
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

    # Print summary
    logger.info("\n" + "="*70)
    logger.info("WEEKLY ANALYSIS SUMMARY (Firebase API)")
    logger.info("="*70)
    logger.info(f"Methodology: {stats['methodology']}")
    logger.info(f"Dates sampled: {len(dates_to_check)}")
    logger.info(f"Articles found (sampled days): {total_articles}")
    logger.info(f"Number of weeks: {num_weeks}")
    logger.info(f"Estimated avg articles per week: {avg_per_week:.2f}")
    logger.info(f"\nQuality thresholds: ≥{MIN_SCORE} points, ≥{MIN_COMMENTS} comments")
    logger.info("\nWeekly breakdown:")

    for week_key in sorted(weekly_stats.keys()):
        week_data = weekly_stats[week_key]
        logger.info(f"  {week_key}:")
        logger.info(f"    Sampled: {week_data['total_articles']} articles across {week_data['sampled_days']} days")
        logger.info(f"    Extrapolated weekly total: ~{week_data['extrapolated_weekly_total']} articles")
        for category, count in sorted(week_data['by_category'].items()):
            logger.info(f"      - {category}: {count}")

    logger.info(f"\nDetailed stats saved to: {STATS_FILE}")
    logger.info("="*70)

    return stats


def main():
    """Main execution."""
    logger.info("Starting HackerNews 4-week analysis (Firebase API)")
    logger.info("This uses Firebase API which works through the proxy")

    try:
        stats = analyze_weekly_data(weeks=4)
        logger.info("\n✓ Analysis complete!")
        logger.info(f"Average HN articles per week: {stats['avg_articles_per_week']}")
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Progress saved to /tmp/hn_firebase_results/")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
