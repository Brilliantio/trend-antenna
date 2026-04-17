"""
Reddit API Client

Uses Reddit's public JSON endpoints (unauthenticated) via a SOCKS proxy
(Tor) to avoid datacenter IP blocking.

When SOCKS_PROXY is set (e.g. socks5h://host.docker.internal:9050),
requests are routed through it.  Falls back to direct connection if unset.

Rate limit: ~60 requests/minute. We sleep 1.1s between requests to stay
well within that budget. For a weekly scrape of ~30 subreddits we make
~30 requests total — far below the limit.
"""

import os
import time
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

USER_AGENT = "Brilliantio-Trend-Antenna/0.1 (research project)"
REQUEST_DELAY = 1.1   # seconds between requests (safe margin under 60/min)
MAX_RETRIES = 3


class RedditClient:
    """Unauthenticated Reddit client using public JSON endpoints."""

    def __init__(self):
        """Initialise the client. No credentials required."""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        # Configure SOCKS proxy if available (Tor)
        socks_proxy = os.getenv("SOCKS_PROXY", "")
        if socks_proxy:
            self.session.proxies = {
                "http": socks_proxy,
                "https": socks_proxy,
            }
            logger.info(f"Reddit client using SOCKS proxy: {socks_proxy}")
        else:
            logger.info("Reddit client using direct connection (no proxy)")

        logger.info("Reddit unauthenticated JSON client initialised")

    def _get(self, url: str, params: Optional[Dict] = None) -> Any:
        """
        Make a GET request with rate-limit awareness and exponential backoff.

        Args:
            url: URL to fetch
            params: Optional query parameters

        Returns:
            Parsed JSON response (list or dict depending on endpoint)

        Raises:
            requests.HTTPError: After MAX_RETRIES exhausted
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                time.sleep(REQUEST_DELAY)
                response = self.session.get(url, params=params, timeout=30)

                if response.status_code in (429, 503):
                    wait = 2 ** attempt
                    logger.warning(
                        f"Reddit returned {response.status_code}, "
                        f"backing off {wait}s (attempt {attempt}/{MAX_RETRIES})"
                    )
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.RequestException as exc:
                if attempt == MAX_RETRIES:
                    logger.error(f"Request failed after {MAX_RETRIES} attempts: {exc}")
                    raise
                wait = 2 ** attempt
                logger.warning(f"Request error ({exc}), retrying in {wait}s")
                time.sleep(wait)

    def _extract_posts(self, listing: Dict) -> List[Dict[str, Any]]:
        """Extract post/comment data dicts from a listing response."""
        return [
            child["data"]
            for child in listing.get("data", {}).get("children", [])
        ]

    def get_top_posts(
        self,
        subreddit_name: str,
        time_filter: str = "week",
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get top posts from a subreddit.

        Args:
            subreddit_name: Subreddit name (without r/ prefix)
            time_filter: Time filter (hour, day, week, month, year, all)
            limit: Maximum number of posts to fetch

        Returns:
            List of raw post data dicts
        """
        url = f"https://www.reddit.com/r/{subreddit_name}/top.json"
        data = self._get(url, params={"t": time_filter, "limit": limit})
        return self._extract_posts(data)

    def get_hot_posts(
        self,
        subreddit_name: str,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get hot posts from a subreddit.

        Args:
            subreddit_name: Subreddit name (without r/ prefix)
            limit: Maximum number of posts to fetch

        Returns:
            List of raw post data dicts
        """
        url = f"https://www.reddit.com/r/{subreddit_name}/hot.json"
        data = self._get(url, params={"limit": limit})
        return self._extract_posts(data)

    def get_new_posts(
        self,
        subreddit_name: str,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get new posts from a subreddit.

        Args:
            subreddit_name: Subreddit name (without r/ prefix)
            limit: Maximum number of posts to fetch

        Returns:
            List of raw post data dicts
        """
        url = f"https://www.reddit.com/r/{subreddit_name}/new.json"
        data = self._get(url, params={"limit": limit})
        return self._extract_posts(data)

    def get_submission(
        self,
        post_id: str,
        subreddit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a single post by ID.

        Args:
            post_id: Reddit post ID (without t3_ prefix)
            subreddit: Subreddit name (optional; makes the URL more efficient)

        Returns:
            Raw post data dict, or empty dict if not found
        """
        if subreddit:
            url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        else:
            url = f"https://www.reddit.com/comments/{post_id}.json"

        # Response is [post_listing, comments_listing]
        data = self._get(url, params={"limit": 1})
        posts = self._extract_posts(data[0])
        return posts[0] if posts else {}

    def get_comments(
        self,
        post_id: str,
        subreddit: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get top comments for a post.

        Args:
            post_id: Reddit post ID (without t3_ prefix)
            subreddit: Subreddit name
            limit: Maximum number of comments to return

        Returns:
            List of raw comment data dicts sorted by score (descending)
        """
        url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        # depth=1 skips nested replies; sort=top returns highest-scored first
        data = self._get(url, params={"limit": limit, "sort": "top", "depth": 1})

        # data is [post_listing, comments_listing]
        raw_comments = self._extract_posts(data[1])

        # Filter out "more" stubs and deleted comments
        comments = [
            c for c in raw_comments
            if c.get("body") and c.get("body") not in ("[deleted]", "[removed]")
        ]
        comments.sort(key=lambda c: c.get("score", 0), reverse=True)
        return comments[:limit]
