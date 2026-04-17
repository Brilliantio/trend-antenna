"""
Comment Fetcher

This module handles fetching comments from Reddit posts via the public JSON API.
Responsible for retrieving top comments sorted by score.
"""

import logging
from typing import List, Dict, Any
from ..models import RedditComment
from ..client import RedditClient

logger = logging.getLogger(__name__)


class CommentFetcher:
    """Handles fetching comments from Reddit posts."""

    def __init__(self, client: RedditClient):
        """
        Initialize the comment fetcher.

        Args:
            client: RedditClient instance
        """
        self.client = client

    def fetch_top_comments(
        self,
        post_id: str,
        subreddit: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Fetch top comments for a post sorted by score.

        Args:
            post_id: Reddit post ID
            subreddit: Subreddit name (required for the JSON endpoint)
            limit: Maximum number of comments to return

        Returns:
            List of comment dictionaries sorted by score (descending)
        """
        logger.info(f"Fetching top {limit} comments for post {post_id} in r/{subreddit}")

        try:
            raw_comments = self.client.get_comments(post_id, subreddit, limit)

            comments = []
            for comment_data in raw_comments:
                reddit_comment = RedditComment.from_json(comment_data)
                comments.append(reddit_comment.to_dict())

            logger.info(f"Successfully fetched {len(comments)} comments for post {post_id}")
            return comments

        except Exception as e:
            logger.error(f"Error fetching comments for post {post_id}: {e}")
            return []

    def fetch_comments_for_posts(
        self,
        post_ids: List[str],
        subreddit: str,
        limit: int = 10,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch top comments for multiple posts in the same subreddit.

        Args:
            post_ids: List of Reddit post IDs
            subreddit: Subreddit name
            limit: Maximum number of comments per post

        Returns:
            Dictionary mapping post_id to list of comments
        """
        logger.info(f"Fetching comments for {len(post_ids)} posts in r/{subreddit}")

        comments_by_post = {}
        for post_id in post_ids:
            comments = self.fetch_top_comments(post_id, subreddit, limit)
            comments_by_post[post_id] = comments

        logger.info(f"Successfully fetched comments for {len(comments_by_post)} posts")
        return comments_by_post
