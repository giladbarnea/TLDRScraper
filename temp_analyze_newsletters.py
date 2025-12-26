"""
Temp script to analyze newsletter publishing patterns over the last 4 weeks.
Scrapes all newsletters, persists results, and calculates statistics.
"""
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

import util
from newsletter_scraper import scrape_date_range
from newsletter_config import NEWSLETTER_CONFIGS


def main():
    # Calculate date range: last 4 weeks (28 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=27)  # 28 days total including end_date

    print(f"Scraping newsletters from {start_date} to {end_date} (28 days)")
    print(f"Total sources to scrape: {len(NEWSLETTER_CONFIGS)}")
    print("=" * 80)

    # Scrape all newsletters
    print("Starting scrape...")
    result = scrape_date_range(start_date, end_date)

    # Persist raw results
    os.makedirs("temp_results", exist_ok=True)
    raw_file = "temp_results/raw_scrape_results.json"
    with open(raw_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nRaw results saved to: {raw_file}")

    # Analyze the data
    articles = result.get("articles", [])
    print(f"\nTotal articles scraped: {len(articles)}")

    # Group articles by source and date
    articles_by_source = defaultdict(lambda: defaultdict(list))

    for article in articles:
        source_id = article.get("source_id")
        date = article.get("date")
        if source_id and date:
            articles_by_source[source_id][date].append(article)

    # Calculate statistics for each newsletter
    stats = {}

    for source_id in sorted(NEWSLETTER_CONFIGS.keys()):
        source_data = articles_by_source.get(source_id, {})

        # Get all dates that had articles
        dates_with_articles = sorted(source_data.keys())

        if not dates_with_articles:
            stats[source_id] = {
                "display_name": NEWSLETTER_CONFIGS[source_id].display_name,
                "total_articles": 0,
                "days_with_articles": 0,
                "avg_articles_per_week": 0.0,
                "avg_articles_per_publishing_day": 0.0,
                "publishing_pattern": "no data",
                "daily_counts": []
            }
            continue

        # Calculate total articles
        total_articles = sum(len(articles) for articles in source_data.values())

        # Calculate average articles per week
        num_weeks = 4.0
        avg_articles_per_week = total_articles / num_weeks

        # Calculate daily article counts (for variability analysis)
        daily_counts = [len(articles) for articles in source_data.values()]
        avg_articles_per_publishing_day = statistics.mean(daily_counts)

        # Calculate variability (standard deviation)
        if len(daily_counts) > 1:
            std_dev = statistics.stdev(daily_counts)
            coefficient_of_variation = std_dev / avg_articles_per_publishing_day if avg_articles_per_publishing_day > 0 else 0
        else:
            std_dev = 0
            coefficient_of_variation = 0

        # Determine publishing pattern
        days_with_articles = len(dates_with_articles)
        if days_with_articles >= 20:  # Publishing most days
            pattern = "daily"
        elif days_with_articles >= 10:  # Publishing frequently
            pattern = "frequent"
        elif days_with_articles >= 4:  # Weekly-ish
            pattern = "weekly"
        else:  # Infrequent
            pattern = "sporadic"

        # Check if articles are clustered (high variability)
        if coefficient_of_variation > 1.0:
            pattern += " (bursty)"
        elif coefficient_of_variation < 0.3:
            pattern += " (consistent)"

        stats[source_id] = {
            "display_name": NEWSLETTER_CONFIGS[source_id].display_name,
            "total_articles": total_articles,
            "days_with_articles": days_with_articles,
            "avg_articles_per_week": round(avg_articles_per_week, 2),
            "avg_articles_per_publishing_day": round(avg_articles_per_publishing_day, 2),
            "std_dev": round(std_dev, 2),
            "coefficient_of_variation": round(coefficient_of_variation, 2),
            "publishing_pattern": pattern,
            "daily_counts": daily_counts,
            "dates_with_articles": dates_with_articles
        }

    # Save stats to file
    stats_file = "temp_results/newsletter_stats.json"
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Statistics saved to: {stats_file}")

    # Print summary report
    print("\n" + "=" * 80)
    print("NEWSLETTER PUBLISHING PATTERNS (Last 4 Weeks)")
    print("=" * 80)
    print(f"{'Newsletter':<30} {'Avg/Week':<12} {'Pattern':<25} {'Days':<6} {'Variability':<12}")
    print("-" * 80)

    # Sort by avg articles per week (descending)
    sorted_sources = sorted(
        stats.items(),
        key=lambda x: x[1]["avg_articles_per_week"],
        reverse=True
    )

    for source_id, data in sorted_sources:
        if data["total_articles"] == 0:
            continue

        name = data["display_name"][:28]
        avg_week = f"{data['avg_articles_per_week']:.1f}"
        pattern = data["publishing_pattern"][:23]
        days = data["days_with_articles"]
        cv = f"CV={data['coefficient_of_variation']:.2f}"

        print(f"{name:<30} {avg_week:<12} {pattern:<25} {days:<6} {cv:<12}")

    print("\n" + "=" * 80)
    print("LEGEND:")
    print("  - Avg/Week: Average number of articles per week")
    print("  - Pattern: Publishing frequency (daily/frequent/weekly/sporadic)")
    print("  - CV (Coefficient of Variation): Measure of variability")
    print("    * CV < 0.3: Consistent publishing volume")
    print("    * CV > 1.0: Bursty (irregular) publishing volume")
    print("  - Days: Number of days (out of 28) with at least one article")
    print("=" * 80)

    # Print sources with no data
    no_data_sources = [s for s, d in stats.items() if d["total_articles"] == 0]
    if no_data_sources:
        print("\nSources with no articles in the last 4 weeks:")
        for source_id in no_data_sources:
            print(f"  - {NEWSLETTER_CONFIGS[source_id].display_name}")


if __name__ == "__main__":
    main()
