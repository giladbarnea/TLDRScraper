"""
Fetch 4 weeks of HackerNews data for analysis.

Fetches HN articles programmatically (not via API) to analyze average
articles per week. Persists successful requests to /tmp for resume capability.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from adapters.hackernews_adapter import HackerNewsAdapter
from newsletter_config import NEWSLETTER_CONFIGS
import util

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/hn_analysis.log')
    ]
)
logger = logging.getLogger(__name__)

# Persistence paths
RESULTS_DIR = Path('/tmp/hn_analysis_results')
RESULTS_DIR.mkdir(exist_ok=True)
SUCCESS_FILE = RESULTS_DIR / 'successful_dates.json'
FAILED_FILE = RESULTS_DIR / 'failed_dates.json'
STATS_FILE = RESULTS_DIR / 'analysis_stats.json'


def load_state():
    """Load previously successful and failed dates."""
    successful = set()
    failed = set()

    if SUCCESS_FILE.exists():
        with open(SUCCESS_FILE) as f:
            successful = set(json.load(f))
        logger.info(f"Loaded {len(successful)} previously successful dates")

    if FAILED_FILE.exists():
        with open(FAILED_FILE) as f:
            failed = set(json.load(f))
        logger.info(f"Loaded {len(failed)} previously failed dates")

    return successful, failed


def save_successful(date_str, articles):
    """Save successful fetch result."""
    successful, _ = load_state()
    successful.add(date_str)

    # Save to success file
    with open(SUCCESS_FILE, 'w') as f:
        json.dump(sorted(list(successful)), f, indent=2)

    # Save articles data
    date_file = RESULTS_DIR / f'{date_str}.json'
    with open(date_file, 'w') as f:
        json.dump(articles, f, indent=2)

    logger.info(f"✓ Saved {len(articles)} articles for {date_str}")


def save_failed(date_str, error_msg):
    """Save failed fetch result."""
    _, failed = load_state()
    failed_dict = {}

    if FAILED_FILE.exists():
        with open(FAILED_FILE) as f:
            failed_dict = json.load(f)

    failed_dict[date_str] = {
        'error': str(error_msg),
        'timestamp': datetime.now().isoformat()
    }

    with open(FAILED_FILE, 'w') as f:
        json.dump(failed_dict, f, indent=2)

    logger.error(f"✗ Failed to fetch {date_str}: {error_msg}")


def get_date_range(weeks=4):
    """Generate list of dates for the last N weeks."""
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=weeks)

    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    return dates


def fetch_hn_for_date(adapter, date_str):
    """Fetch HackerNews articles for a specific date."""
    try:
        logger.info(f"Fetching HN articles for {date_str}...")
        result = adapter.scrape_date(date_str, excluded_urls=[])

        articles = result.get('articles', [])
        if not articles:
            logger.warning(f"No articles found for {date_str}")

        return articles

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)

        # Check for network/SSL errors
        if 'SSL' in error_msg or 'ssl' in error_msg.lower():
            logger.error(f"SSL ERROR for {date_str}: {error_msg}")
        elif 'Connection' in error_msg or 'timeout' in error_msg.lower():
            logger.error(f"NETWORK ERROR for {date_str}: {error_msg}")

        raise


def analyze_results():
    """Analyze collected data and generate statistics."""
    successful, _ = load_state()

    if not successful:
        logger.warning("No successful fetches to analyze")
        return

    # Load all article data
    weekly_stats = {}
    total_articles = 0

    for date_str in sorted(successful):
        date_file = RESULTS_DIR / f'{date_str}.json'
        if not date_file.exists():
            continue

        with open(date_file) as f:
            articles = json.load(f)

        # Get week number
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        week_key = date_obj.strftime('%Y-W%U')

        if week_key not in weekly_stats:
            weekly_stats[week_key] = {
                'total_articles': 0,
                'by_category': {},
                'dates': []
            }

        weekly_stats[week_key]['total_articles'] += len(articles)
        weekly_stats[week_key]['dates'].append(date_str)
        total_articles += len(articles)

        # Count by category
        for article in articles:
            category = article.get('category', 'Unknown')
            if category not in weekly_stats[week_key]['by_category']:
                weekly_stats[week_key]['by_category'][category] = 0
            weekly_stats[week_key]['by_category'][category] += 1

    # Calculate averages
    num_weeks = len(weekly_stats)
    avg_per_week = total_articles / num_weeks if num_weeks > 0 else 0

    stats = {
        'total_dates_fetched': len(successful),
        'total_articles': total_articles,
        'num_weeks': num_weeks,
        'avg_articles_per_week': round(avg_per_week, 2),
        'weekly_breakdown': weekly_stats
    }

    # Save stats
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("ANALYSIS SUMMARY")
    logger.info("="*60)
    logger.info(f"Total dates fetched: {len(successful)}")
    logger.info(f"Total articles: {total_articles}")
    logger.info(f"Number of weeks: {num_weeks}")
    logger.info(f"Average articles per week: {avg_per_week:.2f}")
    logger.info("\nWeekly breakdown:")

    for week_key in sorted(weekly_stats.keys()):
        week_data = weekly_stats[week_key]
        logger.info(f"  {week_key}: {week_data['total_articles']} articles across {len(week_data['dates'])} days")
        for category, count in sorted(week_data['by_category'].items()):
            logger.info(f"    - {category}: {count}")

    logger.info(f"\nDetailed stats saved to: {STATS_FILE}")
    logger.info("="*60)


def main():
    """Main execution function."""
    logger.info("Starting HackerNews 4-week analysis")

    # Initialize adapter
    hn_config = NEWSLETTER_CONFIGS['hackernews']
    adapter = HackerNewsAdapter(hn_config)

    # Get date range
    dates = get_date_range(weeks=4)
    logger.info(f"Generated {len(dates)} dates from {dates[0]} to {dates[-1]}")

    # Load existing state
    successful, failed = load_state()

    # Determine which dates to fetch
    to_fetch = [d for d in dates if d not in successful]
    logger.info(f"{len(to_fetch)} dates to fetch (skipping {len(successful)} already successful)")

    if not to_fetch:
        logger.info("All dates already fetched. Running analysis...")
        analyze_results()
        return

    # Fetch data
    fetch_count = 0
    error_count = 0

    for date_str in to_fetch:
        try:
            articles = fetch_hn_for_date(adapter, date_str)
            save_successful(date_str, articles)
            fetch_count += 1

        except Exception as e:
            save_failed(date_str, str(e))
            error_count += 1

    # Final summary
    logger.info("\n" + "="*60)
    logger.info("FETCH SUMMARY")
    logger.info("="*60)
    logger.info(f"Successfully fetched: {fetch_count}")
    logger.info(f"Failed: {error_count}")

    if error_count > 0:
        logger.info(f"\nFailed dates logged to: {FAILED_FILE}")
        logger.info("Re-run this script to retry failed dates")

    # Run analysis
    logger.info("\nRunning analysis...")
    analyze_results()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Progress saved to /tmp/hn_analysis_results/")
        logger.info("Re-run to continue from where you left off")
        sys.exit(0)
