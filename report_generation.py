#!/usr/bin/env python3
"""
Trend Antenna — Book Concept Signal Discovery for Brilliantio

Generates per-brand reports identifying emerging problem signals from Reddit
communities, scored and filtered for publishing potential.

Forked from liyedanpdx/reddit-ai-trends.
"""

import os
import sys
import logging
import argparse
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.reddit_collection.collector import RedditDataCollector
from services.llm_processing.report_processor import ReportProcessor
from database.mongodb import MongoDBClient
from config import REPORT_CONFIG, BRANDS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("report_generation.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def generate_report(
    skip_mongodb: bool = False,
    reference_date: Optional[datetime] = None,
    hours: int = 24,
    save_to_db: bool = True,
    save_to_file: bool = True,
    brand_keys: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Generate book-concept signal reports for all (or selected) brands.

    Args:
        skip_mongodb: Whether to skip saving the report to MongoDB
        reference_date: Optional specific date to generate report for
        hours: Number of hours to look back for posts
        save_to_db: Whether to save the report to MongoDB
        save_to_file: Whether to save the report to file
        brand_keys: Optional list of brand keys to generate for (default: all)

    Returns:
        Dictionary mapping brand keys to report file paths
    """
    logger.info("Starting Trend Antenna report generation")
    start_time = time.time()

    current_time = reference_date if reference_date is not None else datetime.now()
    logger.info(f"Using reference date: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Determine which brands to process
    brands_to_process = brand_keys or list(BRANDS.keys())
    logger.info(f"Generating reports for brands: {brands_to_process}")

    try:
        reddit_collector = RedditDataCollector()
        report_processor = ReportProcessor()
        mongodb_client = MongoDBClient()

        # Collect all subreddits needed across selected brands
        all_subreddits = set()
        for bk in brands_to_process:
            all_subreddits.update(BRANDS[bk]["subreddits"])
        all_subreddits = list(all_subreddits)

        posts_per_subreddit = REPORT_CONFIG.get("posts_per_subreddit", 30)

        # Time range
        end_time = current_time
        start_time_range = end_time - timedelta(hours=hours)
        logger.info(f"Collecting posts from {start_time_range} to {end_time}")

        # Collect posts from all subreddits
        all_posts = []
        for subreddit in all_subreddits:
            posts = reddit_collector.get_detailed_subreddit_posts(
                subreddit=subreddit,
                limit=posts_per_subreddit,
                time_filter="week",
            )
            # Filter by time range
            for post in posts:
                post_time = post.get("created_utc")
                if isinstance(post_time, str):
                    try:
                        post_time = datetime.fromisoformat(post_time.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                if post_time and start_time_range <= post_time <= end_time:
                    all_posts.append(post)

        # Filter posts with sufficient engagement
        filtered_posts = [p for p in all_posts if p.get("num_comments", 0) > 10]
        logger.info(
            f"Filtered {len(filtered_posts)} posts with >10 comments from {len(all_posts)} total"
        )

        # Get weekly and monthly popular posts
        weekly_posts = reddit_collector.get_weekly_popular_posts(all_subreddits)
        monthly_posts = reddit_collector.get_monthly_popular_posts(all_subreddits)

        # Get previous report for comparison
        previous_report = mongodb_client.get_latest_report()

        # Generate per-brand reports
        reports = report_processor.generate_all_brand_reports(
            all_posts=filtered_posts,
            previous_report=previous_report,
            weekly_posts=weekly_posts,
            monthly_posts=monthly_posts,
            reference_date=current_time,
            save_to_file=save_to_file,
        )

        # Collect report file paths
        report_paths = {}
        timestamp = current_time.strftime("%Y%m%d_%H%M%S")

        for brand_key, report in reports.items():
            if brand_key not in brands_to_process:
                continue

            report_dir = os.path.join(
                REPORT_CONFIG["report_directory"],
                str(current_time.year),
                f"{current_time.month:02d}",
                f"{current_time.day:02d}",
            )
            filepath = os.path.join(report_dir, f"trend-antenna_{brand_key}_{timestamp}.md")
            report_paths[brand_key] = filepath
            logger.info(f"Report for '{brand_key}': {filepath}")

        # Save to MongoDB
        if save_to_db and not skip_mongodb:
            all_posts_to_save = []
            all_posts_to_save.extend(filtered_posts)
            all_posts_to_save.extend(weekly_posts)
            all_posts_to_save.extend(monthly_posts)

            post_result = mongodb_client.insert_or_update_posts(all_posts_to_save)
            logger.info(
                f"Saved {post_result['inserted']} new posts, "
                f"updated {post_result['updated']} posts"
            )

            # Save each brand report
            for brand_key, report in reports.items():
                mongodb_client.save_report(
                    {"en": report.get("content", "")},
                    filtered_posts,
                    weekly_posts,
                    monthly_posts,
                )
            logger.info("Saved reports to MongoDB")

        elapsed = time.time() - start_time
        logger.info(f"Report generation completed in {elapsed:.2f} seconds")

        return report_paths

    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        raise


def schedule_report_generation(skip_mongodb: bool = False) -> None:
    """Schedule report generation to run daily."""
    generation_time = REPORT_CONFIG.get("generation_time", "06:00")

    logger.info(f"Scheduling report generation daily at {generation_time}")
    schedule.every().day.at(generation_time).do(
        lambda: generate_report(skip_mongodb=skip_mongodb)
    )

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Trend Antenna — Generate book-concept signal reports from Reddit"
    )
    parser.add_argument(
        "--brands",
        nargs="+",
        default=None,
        help="Brand keys to generate reports for (e.g., ztm tch). Default: all brands",
    )
    parser.add_argument(
        "--skip-mongodb",
        action="store_true",
        help="Skip saving reports to MongoDB",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Schedule interval in hours (0 = run once)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=168,
        help="Number of hours to look back for posts (default: 168 = 1 week)",
    )
    args = parser.parse_args()

    if args.interval > 0:
        schedule_report_generation(skip_mongodb=args.skip_mongodb)
    else:
        generate_report(
            skip_mongodb=args.skip_mongodb,
            brand_keys=args.brands,
            hours=args.hours,
        )
