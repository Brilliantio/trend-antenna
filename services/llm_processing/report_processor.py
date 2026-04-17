"""
Report Processor

This module provides functionality to process and format Reddit reports,
generating per-brand book-concept signal reports for Brilliantio.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import markdown
from services.llm_processing.core.factory import LLMClientFactory
from config import REPORT_CONFIG, BRANDS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReportProcessor:
    """Service for processing and formatting Reddit reports."""

    def __init__(self):
        """Initialize the report processor."""
        self.llm_client = LLMClientFactory.create_client()
        logger.info("Report processor initialized")

    def generate_brand_report(
        self,
        brand_key: str,
        posts: List[Dict[str, Any]],
        previous_report: Optional[Dict[str, Any]] = None,
        weekly_posts: Optional[List[Dict[str, Any]]] = None,
        monthly_posts: Optional[List[Dict[str, Any]]] = None,
        reference_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generate a report for a single brand.

        Args:
            brand_key: Key into the BRANDS dict (e.g. 'ztm')
            posts: List of post dicts (already filtered to this brand's subreddits)
            previous_report: Optional previous report for comparison
            weekly_posts: List of weekly popular posts for this brand
            monthly_posts: List of monthly popular posts for this brand
            reference_date: Optional specific date for the report

        Returns:
            Report dictionary with content, metadata, etc.
        """
        brand = BRANDS[brand_key]
        brand_name = brand["name"]
        brand_focus = brand["focus"]
        brand_subreddits = brand["subreddits"]

        logger.info(f"Generating report for brand '{brand_name}' ({brand_key}) with {len(posts)} posts")

        markdown_content = self.llm_client.generate_report(
            posts,
            previous_report,
            weekly_posts,
            monthly_posts,
            language="en",
            reference_date=reference_date,
            brand_name=brand_name,
            brand_focus=brand_focus,
            brand_subreddits=brand_subreddits,
        )

        timestamp = reference_date if reference_date is not None else datetime.utcnow()

        title = REPORT_CONFIG.get(
            "report_title_format",
            "Trend Antenna Report — {brand} — {date}",
        ).format(brand=brand_name, date=timestamp.strftime("%Y-%m-%d %H:%M UTC"))

        report = {
            "report_id": f"trend-antenna_{brand_key}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
            "timestamp": timestamp,
            "language": "en",
            "brand": brand_key,
            "brand_name": brand_name,
            "title": title,
            "content": markdown_content,
            "post_count": len(posts),
            "post_ids": [post.get("post_id") for post in posts if post.get("post_id")],
            "subreddits": brand_subreddits,
            "html_content": markdown.markdown(markdown_content),
        }

        logger.info(f"Report generated: {report['report_id']}")
        return report

    def generate_all_brand_reports(
        self,
        all_posts: List[Dict[str, Any]],
        previous_report: Optional[Dict[str, Any]] = None,
        weekly_posts: Optional[List[Dict[str, Any]]] = None,
        monthly_posts: Optional[List[Dict[str, Any]]] = None,
        reference_date: Optional[datetime] = None,
        save_to_file: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate reports for all configured brands.

        Posts are filtered per-brand based on each brand's subreddit list.

        Args:
            all_posts: All collected posts across all subreddits
            previous_report: Optional previous report for comparison
            weekly_posts: All weekly popular posts
            monthly_posts: All monthly popular posts
            reference_date: Optional specific date for the report
            save_to_file: Whether to save each report to disk

        Returns:
            Dict mapping brand_key -> report dict
        """
        reports = {}

        for brand_key, brand_config in BRANDS.items():
            brand_subs = set(brand_config["subreddits"])

            # Filter posts to this brand's subreddits
            brand_posts = [p for p in all_posts if p.get("subreddit") in brand_subs]
            brand_weekly = [p for p in (weekly_posts or []) if p.get("subreddit") in brand_subs]
            brand_monthly = [p for p in (monthly_posts or []) if p.get("subreddit") in brand_subs]

            logger.info(
                f"Brand '{brand_key}': {len(brand_posts)} daily, "
                f"{len(brand_weekly)} weekly, {len(brand_monthly)} monthly posts"
            )

            report = self.generate_brand_report(
                brand_key=brand_key,
                posts=brand_posts,
                previous_report=previous_report,
                weekly_posts=brand_weekly,
                monthly_posts=brand_monthly,
                reference_date=reference_date,
            )
            reports[brand_key] = report

            if save_to_file:
                self.save_report_to_file(report)

        return reports

    def save_report_to_file(self, report: Dict[str, Any]) -> str:
        """
        Save a report to a file.

        Output path: reports/{YYYY}/{MM}/{DD}/trend-antenna_{brand}_{YYYYMMDD_HHMMSS}.md

        Args:
            report: Report dictionary

        Returns:
            Path to the saved file
        """
        timestamp = report.get("timestamp", datetime.utcnow())
        brand_key = report.get("brand", "unknown")

        # Create directory: reports/YYYY/MM/DD/
        report_dir = os.path.join(
            REPORT_CONFIG["report_directory"],
            str(timestamp.year),
            f"{timestamp.month:02d}",
            f"{timestamp.day:02d}",
        )
        os.makedirs(report_dir, exist_ok=True)

        filename = f"trend-antenna_{brand_key}_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(report_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report["content"])

        logger.info(f"Report saved to file: {filepath}")

        # Save metadata
        metadata_filename = f"trend-antenna_{brand_key}_{timestamp.strftime('%Y%m%d_%H%M%S')}_metadata.json"
        metadata_filepath = os.path.join(report_dir, metadata_filename)

        metadata = {
            "report_id": report.get("report_id"),
            "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
            "brand": brand_key,
            "brand_name": report.get("brand_name"),
            "title": report.get("title"),
            "post_count": report.get("post_count"),
            "post_ids": report.get("post_ids"),
            "subreddits": report.get("subreddits"),
            "filepath": filepath,
        }

        with open(metadata_filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Report metadata saved to file: {metadata_filepath}")
        return filepath
