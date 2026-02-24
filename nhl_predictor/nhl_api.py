"""
Fetch NHL data from public APIs. No API key required (optional NHL_API_KEY in env).
- Schedule: api-web.nhle.com
- Standings: api-web.nhle.com (includes last-10 and season W-L)
- Team stats (PP/PK, shots/game): api.nhle.com/stats
- Goalie save %: api-web.nhle.com player landing
- Head-to-head: api-web.nhle.com club-schedule-season
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

import certifi

from . import config

# Use certifi's certificate bundle so HTTPS works on macOS (avoids CERTIFICATE_VERIFY_FAILED)
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def _iso_utc_to_local_label(start_time_utc: str | None) -> str:
    """Convert ISO UTC like '2026-02-25T00:30:00Z' to local '7:30 PM'."""
    if not start_time_utc:
        return "TBD"
    s = start_time_utc.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s).astimezone()  # system local tz
    try:
        return dt.strftime("%-I:%M %p")  # mac/linux
    except ValueError:
        return dt.strftime("%I:%M %p").lstrip("0")  # fallback

def _get(url: str):
    headers = {"User-Agent": "NHL-Predictor/1.0"}
    if config.NHL_API_KEY:
        headers["Authorization"] = f"Bearer {config.NHL_API_KEY}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:
        return json.loads(resp.read().decode())

def get_schedule(for_date: date) -> list[dict]:
    """Return list of scheduled games for the given date (future/upcoming)."""
    url = f"{config.NHL_WEB_BASE}/schedule/{for_date.isoformat()}"
    data = _get(url)

    games: list[dict] = []
    target_date = for_date.isoformat()

    game_week = data.get("gameWeek") if isinstance(data, dict) else []
    for week in game_week or []:
        if week.get("date") != target_date:
            continue

        for g in week.get("games", []):
            # Far-future games sometimes use different states than "FUT".
            # Keep only games that are not started/finished.
            state = (g.get("gameState") or "").upper()
            if state in ("OFF", "FINAL", "LIVE", "CRIT", "IN_PROGRESS"):
                continue

            home = g.get("homeTeam") or {}
            away = g.get("awayTeam") or {}

            # pull start time from common keys
            start_time_utc = (
                g.get("startTimeUTC")
                or g.get("startTimeUtc")
                or g.get("startTime")
                or g.get("gameDate")
                or (g.get("startTime") or {}).get("utc")
            )

            games.append({
                "id": g["id"],
                "date": week.get("date"),
                "homeAbbrev": home.get("abbrev") or (home.get("teamAbbrev") or {}).get("default"),
                "awayAbbrev": away.get("abbrev") or (away.get("teamAbbrev") or {}).get("default"),
                "homeId": home.get("id"),
                "awayId": away.get("id"),

                "startTimeUTC": start_time_utc,
                "gameTimeLocal": _iso_utc_to_local_label(start_time_utc),
            })

    return games


# Helper to fetch schedule for a date range (inclusive)
def get_schedule_range(start: date, end: date) -> list[dict]:
    """Return scheduled games between start and end (inclusive)."""
    if end < start:
        start, end = end, start

    all_games: list[dict] = []
    d = start
    while d <= end:
        all_games.extend(get_schedule(d))
        d += timedelta(days=1)

    # De-dup by game id while preserving order
    seen: set[int] = set()
    deduped: list[dict] = []
    for g in all_games:
        gid = g.get("id")
        if isinstance(gid, int) and gid in seen:
            continue
        if isinstance(gid, int):
            seen.add(gid)
        deduped.append(g)
    return deduped

def get_standings() -> dict:
    """Return standings with last-10 and season W-L. Keyed by team abbrev."""
    url = f"{config.NHL_WEB_BASE}/standings/now"
    data = _get(url)
    by_abbrev = {}
    for row in data.get("standings", []):
        abbrev = (row.get("teamAbbrev") or {}).get("default")
        if not abbrev:
            continue
        gp = row.get("gamesPlayed") or 1
        l10gp = row.get("l10GamesPlayed") or 10
        by_abbrev[abbrev] = {
            "wins": row.get("wins", 0),
            "losses": row.get("losses", 0),
            "otLosses": row.get("otLosses", 0),
            "gamesPlayed": gp,
            "seasonWinPct": (row.get("wins", 0) + 0.5 * row.get("otLosses", 0)) / gp if gp else 0.5,
            "l10Wins": row.get("l10Wins", 0),
            "l10Losses": row.get("l10Losses", 0),
            "l10OtLosses": row.get("l10OtLosses", 0),
            "l10GamesPlayed": l10gp,
            "l10WinPct": (row.get("l10Wins", 0) + 0.5 * row.get("l10OtLosses", 0)) / l10gp if l10gp else 0.5,
        }
    return by_abbrev


def get_team_stats_season() -> dict:
    """Return team summary stats including powerPlayPct and penaltyKillPct. Keyed by team abbrev."""
    season_id = config.current_season_id()
    url = f"{config.NHL_STATS_BASE}/team/summary?limit=50&sort=gamesPlayed&order=desc&cayenneExp=gameTypeId=2%20and%20seasonId={season_id}"
    data = _get(url)
    # Build name -> abbrev from standings (teamName.default = "Colorado Avalanche", teamAbbrev.default = "COL")
    standings_url = f"{config.NHL_WEB_BASE}/standings/now"
    stand_data = _get(standings_url)
    name_to_abbrev = {}
    for row in stand_data.get("standings", []):
        name = (row.get("teamName") or {}).get("default", "")
        abbrev = (row.get("teamAbbrev") or {}).get("default", "")
        if name and abbrev:
            name_to_abbrev[name] = abbrev
    by_abbrev = {}
    for row in data.get("data", []):
        full = row.get("teamFullName", "")
        abbrev = name_to_abbrev.get(full)
        if not abbrev:
            continue
        pp = row.get("powerPlayPct") or 0
        pk = row.get("penaltyKillPct") or 0
        shots_pg = row.get("shotsForPerGame")
        if shots_pg is not None:
            shots_pg = float(shots_pg)
        else:
            shots_pg = 30.0
        gf_pg = row.get("goalsForPerGame") or 0.0
        ga_pg = row.get("goalsAgainstPerGame") or 0.0
        goal_diff_pg = float(gf_pg) - float(ga_pg)
        by_abbrev[abbrev] = {
            "powerPlayPct": pp,
            "penaltyKillPct": pk,
            "specialTeamsAvg": (pp + pk) / 2.0,
            "shotsForPerGame": shots_pg,
            "goalsForPerGame": float(gf_pg),
            "goalsAgainstPerGame": float(ga_pg),
            "goalDiffPerGame": goal_diff_pg,
        }
    return by_abbrev


_club_schedule_cache: dict[str, list[dict]] = {}


def get_club_schedule_season(team_abbrev: str) -> list[dict]:
    """Return full season schedule for team. Cached per team for the run."""
    key = team_abbrev.upper()
    if key in _club_schedule_cache:
        return _club_schedule_cache[key]
    url = f"{config.NHL_WEB_BASE}/club-schedule-season/{key}/now"
    try:
        data = _get(url)
    except urllib.error.HTTPError:
        _club_schedule_cache[key] = []
        return []
    games = data.get("games") or []
    _club_schedule_cache[key] = games
    return games


def get_h2h_win_pct(home_abbrev: str, away_abbrev: str) -> tuple[float, int]:
    """
    Return (home_team_win_pct_in_matchup, num_games_played) for this season.
    Only completed regular-season games. If no games, return (0.5, 0).
    """
    games = get_club_schedule_season(home_abbrev)
    season_id = config.current_season_id()
    home_wins = 0
    total = 0
    for g in games:
        if g.get("gameType") != 2:
            continue
        if g.get("season") != season_id:
            continue
        state = (g.get("gameState") or "").upper()
        if state not in ("OFF", "FINAL"):
            continue
        h = (g.get("homeTeam") or {}).get("abbrev") or ""
        a = (g.get("awayTeam") or {}).get("abbrev") or ""
        if not (h and a):
            continue
        if (h == home_abbrev and a == away_abbrev) or (h == away_abbrev and a == home_abbrev):
            h_score = (g.get("homeTeam") or {}).get("score")
            a_score = (g.get("awayTeam") or {}).get("score")
            if h_score is None or a_score is None:
                continue
            total += 1
            if h == home_abbrev:
                if h_score > a_score:
                    home_wins += 1
            else:
                if a_score > h_score:
                    home_wins += 1
    if total == 0:
        return 0.5, 0
    return home_wins / total, total


def get_goalie_save_pct(player_id: int) -> float | None:
    """Return current season save percentage for goalie by NHL player ID, or None."""
    url = f"{config.NHL_WEB_BASE}/player/{player_id}/landing"
    try:
        data = _get(url)
    except urllib.error.HTTPError:
        return None
    featured = (data.get("featuredStats") or {}).get("regularSeason") or {}
    sub = featured.get("subSeason") or {}
    sv = sub.get("savePctg")
    if sv is not None:
        return float(sv)
    return None


def search_player_id(name: str) -> int | None:
    """Search NHL API by name; return first matching player id or None."""
    q = urllib.parse.quote(name.strip())
    url = f"{config.NHL_SEARCH_BASE}?culture=en-us&limit=5&q={q}"
    try:
        data = _get(url)
    except urllib.error.HTTPError:
        return None

    # API may return either {"data": [...]} or a bare list
    if isinstance(data, dict):
        players = data.get("data") or []
    elif isinstance(data, list):
        players = data
    else:
        return None

    if not isinstance(players, list):
        return None

    # Prefer goalies first
    for p in players[:3]:
        if isinstance(p, dict) and p.get("position") == "G":
            pid = p.get("playerId")
            if pid:
                return pid

    # Fallback: first player with an id
    for p in players[:5]:
        if isinstance(p, dict):
            pid = p.get("playerId")
            if pid:
                return pid
    return None
