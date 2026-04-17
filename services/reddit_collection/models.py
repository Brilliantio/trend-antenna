"""
Reddit Data Models

This module defines data models for Reddit posts and comments using dataclasses.
Provides a unified interface for converting between Reddit JSON API responses
and the internal data shape consumed by the rest of the pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class RedditComment:
    """Data model for a Reddit comment."""

    comment_id: str
    author: str
    created_utc: datetime
    score: int
    body: str

    # Tracking fields (added by database merge logic)
    first_seen: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    score_history: List[Dict[str, Any]] = field(default_factory=list)
    historical: bool = False
    dropped_from_top: Optional[datetime] = None

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'RedditComment':
        """
        Create a RedditComment from a Reddit JSON API comment data dict.

        Args:
            data: Comment data dict from Reddit's public JSON endpoint

        Returns:
            RedditComment instance
        """
        return cls(
            comment_id=data.get("id", ""),
            author=data.get("author") or "[deleted]",
            created_utc=datetime.fromtimestamp(data.get("created_utc", 0)),
            score=data.get("score", 0),
            body=data.get("body", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for database storage.

        Returns:
            Dictionary representation
        """
        return {
            "comment_id": self.comment_id,
            "author": self.author,
            "created_utc": self.created_utc,
            "score": self.score,
            "body": self.body,
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
            "score_history": self.score_history,
            "historical": self.historical,
            "dropped_from_top": self.dropped_from_top
        }


@dataclass
class RedditPost:
    """Data model for a Reddit post."""

    post_id: str
    title: str
    author: str
    created_utc: datetime
    score: int
    upvote_ratio: float
    num_comments: int
    permalink: str
    url: str
    is_self: bool
    selftext: str
    subreddit: str
    link_flair_text: Optional[str]
    category: str

    # Optional enrichment fields
    comments: List[Dict[str, Any]] = field(default_factory=list)
    photo_parse: Optional[str] = None

    # Database tracking fields
    historical_metrics: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: Optional[datetime] = None

    @classmethod
    def from_json(cls, data: Dict[str, Any], category: str = "general") -> 'RedditPost':
        """
        Create a RedditPost from a Reddit JSON API post data dict.

        Args:
            data: Post data dict from Reddit's public JSON endpoint
            category: Post category (default: "general")

        Returns:
            RedditPost instance
        """
        permalink = data.get("permalink", "")
        if permalink and not permalink.startswith("http"):
            permalink = f"https://www.reddit.com{permalink}"

        is_self = data.get("is_self", False)
        return cls(
            post_id=data.get("id", ""),
            title=data.get("title", ""),
            author=data.get("author") or "[deleted]",
            created_utc=datetime.fromtimestamp(data.get("created_utc", 0)),
            score=data.get("score", 0),
            upvote_ratio=data.get("upvote_ratio", 0.0),
            num_comments=data.get("num_comments", 0),
            permalink=permalink,
            url=data.get("url", ""),
            is_self=is_self,
            selftext=data.get("selftext", "") if is_self else "",
            subreddit=data.get("subreddit", ""),
            link_flair_text=data.get("link_flair_text"),
            category=category,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for database storage or API response.

        Returns:
            Dictionary representation
        """
        return {
            "post_id": self.post_id,
            "title": self.title,
            "author": self.author,
            "created_utc": self.created_utc,
            "score": self.score,
            "upvote_ratio": self.upvote_ratio,
            "num_comments": self.num_comments,
            "permalink": self.permalink,
            "url": self.url,
            "is_self": self.is_self,
            "selftext": self.selftext,
            "subreddit": self.subreddit,
            "link_flair_text": self.link_flair_text,
            "category": self.category,
            "comments": self.comments,
            "photo_parse": self.photo_parse,
            "historical_metrics": self.historical_metrics,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RedditPost':
        """
        Create a RedditPost from a dictionary (e.g., from database).

        Args:
            data: Dictionary with post data

        Returns:
            RedditPost instance
        """
        return cls(
            post_id=data.get("post_id", ""),
            title=data.get("title", ""),
            author=data.get("author", ""),
            created_utc=data.get("created_utc", datetime.utcnow()),
            score=data.get("score", 0),
            upvote_ratio=data.get("upvote_ratio", 0.0),
            num_comments=data.get("num_comments", 0),
            permalink=data.get("permalink", ""),
            url=data.get("url", ""),
            is_self=data.get("is_self", False),
            selftext=data.get("selftext", ""),
            subreddit=data.get("subreddit", ""),
            link_flair_text=data.get("link_flair_text"),
            category=data.get("category", "general"),
            comments=data.get("comments", []),
            photo_parse=data.get("photo_parse"),
            historical_metrics=data.get("historical_metrics", []),
            last_updated=data.get("last_updated")
        )

    def should_fetch_comments(self, min_selftext_length: int = 100) -> bool:
        """
        Determine if comments should be fetched for this post (smart mode logic).

        Args:
            min_selftext_length: Minimum selftext length to skip comments

        Returns:
            True if comments should be fetched, False otherwise
        """
        if not self.is_self:
            # Link/image/video posts - fetch comments
            return True
        elif len(self.selftext.strip()) < min_selftext_length:
            # Short text - fetch comments
            return True
        else:
            # Sufficient text - skip comments
            return False
