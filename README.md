# Trend Antenna — Brilliantio Book Concept Signal Discovery

> Fork of [liyedanpdx/reddit-ai-trends](https://github.com/liyedanpdx/reddit-ai-trends), customised for Brilliantio's publishing use case.

Trend Antenna surfaces emerging problem signals from online communities, scored and filtered for book publishing potential. It delivers brand-partitioned weekly reports to Paul's Monday pre-flight.

## How It Works

1. **Collect** — Fetches recent posts from brand-specific subreddit lists via the Reddit API
2. **Enrich** — Adds comments, YouTube transcripts, and web content summaries
3. **Analyse** — An LLM identifies the top 10 "problem signals" per brand — pain points, frustrations, and unmet needs that could become nonfiction book concepts
4. **Report** — Outputs one markdown report per brand per run, with conviction scores, saturation estimates, and evidence quotes

## Brands

| Key | Brand | Subreddits | Focus |
|-----|-------|------------|-------|
| `ztm` | Zero to Made | 10 | Non-technical adults building with AI |
| `tch` | The Creator Handbook | 10 | Content creators across disciplines |
| `gbq_cm` | Great British Quizzes / Charlie Mercer | 5 | UK quiz, trivia, puzzle, fiction audiences |
| `fps` | First Person Science | 5 | First-person science/medical experience writing |

Brand subreddit research is documented in `brands/`.

## Architecture

- **Brand-partitioned**: Each brand has its own subreddit list and analysis lens
- **Per-brand reports**: One report per brand per run (4 reports per cycle)
- **English only**: Bilingual support removed for simplicity
- **Smart caching**: MongoDB-backed caching for all enrichments
- **LLM provider**: OpenRouter (free tier with DeepSeek R1)

## Report Output

```
reports/
  {YYYY}/
    {MM}/
      {DD}/
        trend-antenna_ztm_{YYYYMMDD_HHMMSS}.md
        trend-antenna_tch_{YYYYMMDD_HHMMSS}.md
        trend-antenna_gbq_cm_{YYYYMMDD_HHMMSS}.md
        trend-antenna_fps_{YYYYMMDD_HHMMSS}.md
```

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Generate all brand reports (one-time)
python report_generation.py --skip-mongodb

# Generate for a specific brand
python report_generation.py --brands ztm tch --skip-mongodb

# Scheduled daily generation
python report_generation.py --interval 24
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required:
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` — Reddit API credentials
- `OPENROUTER_API_KEY` — LLM provider (or `GROQ_API_KEY` for Groq)
- `MONGODB_URI` — MongoDB connection string

Optional:
- `FIRECRAWL_API_KEY` — Web content analysis (500 free credits/month)
- `FETCH_COMMENTS=smart` — Comment fetching strategy
- `ANALYZE_IMAGES=false` — Image analysis (disabled by default)

See `.env.example` for full documentation.

## Deployment

```bash
docker-compose up -d
```

## Upstream Sync

This is a fork of `liyedanpdx/reddit-ai-trends`. Upstream sync cadence: monthly.

```bash
git fetch upstream
git merge upstream/main
```

## Linear Project

[DEV_0017 Trend Antenna](https://linear.app/brilliantio/project/dev-0017-trend-antenna)

## Upstream README

The original project README is preserved at [README_UPSTREAM.md](README_UPSTREAM.md).
