"""Paths and constants for the NHL predictor."""

import os

# Optional: set NHL_API_KEY in environment if you have an API key for rate limits or alternate sources
NHL_API_KEY = os.environ.get("NHL_API_KEY", "").strip() or None

# Directory for JSON data (config, cache, output)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nhl_data")
os.makedirs(DATA_DIR, exist_ok=True)

# Input: starting goalies by date (from Daily Faceoff or scraper)
STARTING_GOALIES_PATH = os.path.join(DATA_DIR, "starting_goalies.json")

# Optional input: injured players by date (manual or from another agent)
INJURIES_PATH = os.path.join(DATA_DIR, "injuries.json")

# Output: predictions for the app
PREDICTIONS_PATH = os.path.join(DATA_DIR, "predictions.json")

# Optional cache to avoid hitting NHL API every run
STANDINGS_CACHE_PATH = os.path.join(DATA_DIR, "standings_cache.json")
TEAM_STATS_CACHE_PATH = os.path.join(DATA_DIR, "team_stats_cache.json")

# NHL API bases (no API key required)
NHL_WEB_BASE = "https://api-web.nhle.com/v1"
NHL_STATS_BASE = "https://api.nhle.com/stats/rest/en"
NHL_SEARCH_BASE = "https://search.d3.nhle.com/api/v1/search/player"

# Current season ID (format 20252026 for 2025-26)
def current_season_id():
    from datetime import date
    d = date.today()
    # Season starts in Oct; before July use previous season
    if d.month < 7:
        start = d.year - 1
    else:
        start = d.year
    return int(f"{start}{start + 1}")
