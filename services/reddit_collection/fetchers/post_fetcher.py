"""
Post Fetcher

This module handles fetching Reddit posts and converting them to RedditPost objects.
Responsible for basic post retrieval without enrichments.
"""

import logging
from typing import List
from ..models import RedditPost
from ..client import RedditClient

logger = logging.getLogger(__name__)


class PostFetcher:
    """Handles fetching Reddit posts from subreddits."""

    def __init__(self, client: RedditClient):
        """
        Initialize the post fetcher.

        Args:
            client: RedditClient instance
        """
        self.client = client

    def fetch_top_posts(
        self,
        subreddit: str,
        time_filter: str = "week",
        limit: int = 30
    ) -> List[RedditPost]:
        """
        Fetch top posts from a subreddit.

        Args:
            subreddit: Subreddit name
            time_filter: Time filter (hour, day, week, month, year, all)
            limit: Maximum number of posts to fetch

        Returns:
            List of RedditPost objects
        """
        logger.info(f"Fetching top {limit} posts from r/{subreddit} (time_filter={time_filter})")

        try:
            posts = []
            post_dicts = self.client.get_top_posts(subreddit, time_filter, limit)

            for post_data in post_dicts:
                category = self._determine_category(post_data)
                post = RedditPost.from_json(post_data, category=category)
                posts.append(post)

            logger.info(f"Successfully fetched {len(posts)} posts from r/{subreddit}")
            return posts

        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit}: {e}")
            return []

    def fetch_hot_posts(self, subreddit: str, limit: int = 30) -> List[RedditPost]:
        """
        Fetch hot posts from a subreddit.

        Args:
            subreddit: Subreddit name
            limit: Maximum number of posts to fetch

        Returns:
            List of RedditPost objects
        """
        logger.info(f"Fetching hot {limit} posts from r/{subreddit}")

        try:
            posts = []
            post_dicts = self.client.get_hot_posts(subreddit, limit)

            for post_data in post_dicts:
                category = self._determine_category(post_data)
                post = RedditPost.from_json(post_data, category=category)
                posts.append(post)

            logger.info(f"Successfully fetched {len(posts)} hot posts from r/{subreddit}")
            return posts

        except Exception as e:
            logger.error(f"Error fetching hot posts from r/{subreddit}: {e}")
            return []

    def fetch_new_posts(self, subreddit: str, limit: int = 30) -> List[RedditPost]:
        """
        Fetch new posts from a subreddit.

        Args:
            subreddit: Subreddit name
            limit: Maximum number of posts to fetch

        Returns:
            List of RedditPost objects
        """
        logger.info(f"Fetching new {limit} posts from r/{subreddit}")

        try:
            posts = []
            post_dicts = self.client.get_new_posts(subreddit, limit)

            for post_data in post_dicts:
                category = self._determine_category(post_data)
                post = RedditPost.from_json(post_data, category=category)
                posts.append(post)

            logger.info(f"Successfully fetched {len(posts)} new posts from r/{subreddit}")
            return posts

        except Exception as e:
            logger.error(f"Error fetching new posts from r/{subreddit}: {e}")
            return []

    def fetch_post_by_id(self, post_id: str, subreddit: str = None) -> RedditPost:
        """
        Fetch a single post by ID.

        Args:
            post_id: Reddit post ID
            subreddit: Subreddit name (optional; makes lookup more efficient)

        Returns:
            RedditPost object or None if not found
        """
        logger.info(f"Fetching post by ID: {post_id}")

        try:
            post_data = self.client.get_submission(post_id, subreddit=subreddit)
            category = self._determine_category(post_data)
            post = RedditPost.from_json(post_data, category=category)

            logger.info(f"Successfully fetched post {post_id}")
            return post

        except Exception as e:
            logger.error(f"Error fetching post {post_id}: {e}")
            return None

    def _determine_category(self, post_data: dict) -> str:
        """
        Determine the category of a post based on its flair.

        Args:
            post_data: Raw post data dict from Reddit JSON API

        Returns:
            Category string (flair text or 'general')
        """
        flair = post_data.get("link_flair_text")
        return flair if flair else "general"
