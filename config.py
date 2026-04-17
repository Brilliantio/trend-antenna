"""
Configuration file for Trend Antenna — Brilliantio Book Concept Signal Discovery

Forked from liyedanpdx/reddit-ai-trends.
Customised for brand-partitioned weekly reports across Brilliantio publishing brands.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Brand Configuration
# ---------------------------------------------------------------------------
# Each brand monitors its own set of subreddits and has a specific focus lens
# for the LLM analysis prompt.  Reports are generated per-brand per run.

BRANDS = {
    "ztm": {
        "name": "Zero to Made",
        "subreddits": [
            "nocode",
            "vibecoding",
            "SideProject",
            "EntrepreneurRideAlong",
            "smallbusiness",
            "Entrepreneur",
            "ChatGPTCoding",
            "ClaudeAI",
            "SaaS",
            "learnprogramming",
        ],
        "focus": (
            "Book-concept signals for non-technical adults building websites, "
            "apps, and digital products using AI tools. Audience: aspiring "
            "solopreneurs, creatives, and small business owners who are NOT "
            "developers but want to ship."
        ),
    },
    "tch": {
        "name": "The Creator Handbook",
        "subreddits": [
            "Filmmakers",
            "screenwriting",
            "WeAreTheMusicMakers",
            "NewTubers",
            "podcasting",
            "VideoEditing",
            "audioengineering",
            "cinematography",
            "videography",
            "youtube",
        ],
        "focus": (
            "Book-concept signals for content creators across disciplines — "
            "filmmakers, narrators, audio producers, screenwriters, podcasters, "
            "video editors, YouTubers, musicians, photographers, and streamers."
        ),
    },
    "gbq_cm": {
        "name": "Great British Quizzes / Charlie Mercer",
        "subreddits": [
            "CasualUK",
            "nostalgia",
            "puzzles",
            "BritishProblems",
            "trivia",
        ],
        "focus": (
            "Book-concept signals for mainstream UK adult audiences interested "
            "in quiz, trivia, puzzles, fiction, and nostalgia-driven stories."
        ),
    },
    "fps": {
        "name": "First Person Science",
        "subreddits": [
            "psychology",
            "AskDocs",
            "MentalHealth",
            "ChronicPain",
            "neuroscience",
        ],
        "focus": (
            "Book-concept signals for first-person accounts of scientific, "
            "medical, and psychological experience — patient memoirs, lab "
            "researcher accounts, and lived-experience science writing. "
            "NOTE: Brand scope is provisional and awaits Paul's confirmation."
        ),
    },
}

# Flat list of all subreddits across brands (used by data collection layer)
ALL_BRAND_SUBREDDITS = []
for _brand in BRANDS.values():
    ALL_BRAND_SUBREDDITS.extend(_brand["subreddits"])
ALL_BRAND_SUBREDDITS = list(dict.fromkeys(ALL_BRAND_SUBREDDITS))  # dedupe, preserve order

# ---------------------------------------------------------------------------
# LLM Provider Configuration
# ---------------------------------------------------------------------------
CURRENT_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()

LLM_PROVIDERS = {
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY"),
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.4")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
    },
    "openrouter": {
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "model": os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1-distill-llama-70b:free"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "1")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
    },
}

LLM_CONFIG = LLM_PROVIDERS.get(CURRENT_LLM_PROVIDER, LLM_PROVIDERS["openrouter"])

# ---------------------------------------------------------------------------
# Reddit Data Collection Configuration
# ---------------------------------------------------------------------------
# Categories to exclude from analysis (empty = no exclusions)
EXCLUDED_CATEGORIES: list = []

REDDIT_COLLECTION_CONFIG = {
    "fetch_comments": os.getenv("FETCH_COMMENTS", "smart").lower(),
    "top_comments_limit": int(os.getenv("TOP_COMMENTS_LIMIT", "5")),
    "min_selftext_length": int(os.getenv("MIN_SELFTEXT_LENGTH", "100")),
    "analyze_images": os.getenv("ANALYZE_IMAGES", "false").lower() == "true",
    "posts_per_subreddit": int(os.getenv("POSTS_PER_SUBREDDIT", "30")),
    "subreddits": ALL_BRAND_SUBREDDITS,
}

# ---------------------------------------------------------------------------
# Report Generation Configuration
# ---------------------------------------------------------------------------
REPORT_CONFIG = {
    "frequency_hours": 24,
    "report_title_format": "Trend Antenna Report — {brand} — {date}",
    "report_directory": "reports",
    "database_name": "trend-antenna",
    "collections": {
        "posts": "posts",
        "reports": "reports",
    },
    "generation_time": os.getenv("REPORT_GENERATION_TIME", "06:00"),
    "languages": ["en"],  # English only
    "posts_per_subreddit": REDDIT_COLLECTION_CONFIG["posts_per_subreddit"],
    "subreddits": REDDIT_COLLECTION_CONFIG["subreddits"],
}

# ---------------------------------------------------------------------------
# Image Analysis Configuration
# ---------------------------------------------------------------------------
IMAGE_ANALYSIS_CONFIG = {
    "model": os.getenv("IMAGE_ANALYSIS_MODEL", "qwen/qwen2.5-vl-72b-instruct:free"),
    "fallback_models": os.getenv(
        "IMAGE_ANALYSIS_FALLBACK_MODELS",
        "google/gemini-2.0-flash-exp:free,mistralai/mistral-small-3.2-24b-instruct:free,mistralai/mistral-small-3.1-24b-instruct:free,meta-llama/llama-4-maverick:free",
    ).split(","),
    "max_tokens": int(os.getenv("IMAGE_ANALYSIS_MAX_TOKENS", "500")),
}

# ---------------------------------------------------------------------------
# YouTube Transcript Analysis Configuration
# ---------------------------------------------------------------------------
YOUTUBE_ANALYSIS_CONFIG = {
    "enabled": os.getenv("YOUTUBE_ANALYSIS_ENABLED", "true").lower() == "true",
    "model": os.getenv("YOUTUBE_ANALYSIS_MODEL", "deepseek/deepseek-chat-v3.1:free"),
    "max_tokens": int(os.getenv("YOUTUBE_ANALYSIS_MAX_TOKENS", "500")),
}

# ---------------------------------------------------------------------------
# Web Content Analysis Configuration
# ---------------------------------------------------------------------------
WEB_CONTENT_ANALYSIS_CONFIG = {
    "enabled": os.getenv("WEB_CONTENT_ANALYSIS_ENABLED", "true").lower() == "true",
    "firecrawl_api_key": os.getenv("FIRECRAWL_API_KEY"),
    "model": os.getenv("WEB_CONTENT_ANALYSIS_MODEL", "deepseek/deepseek-chat-v3.1:free"),
    "max_tokens": int(os.getenv("WEB_CONTENT_ANALYSIS_MAX_TOKENS", "500")),
}

# ---------------------------------------------------------------------------
# Docker Configuration
# ---------------------------------------------------------------------------
DOCKER_CONFIG = {
    "image_name": "trend-antenna",
    "container_name": "trend-antenna-container",
    "port": 8080,
}
