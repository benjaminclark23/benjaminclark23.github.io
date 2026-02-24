"""
Daily runner: fetch upcoming games, gather 5 factors, predict American odds, write JSON.
Run before game day (e.g. morning). Output is app-friendly predictions.json.
"""

import json
import os
from datetime import date, timedelta

from . import config
from .nhl_api import (
    get_schedule,
    get_standings,
    get_team_stats_season,
    get_goalie_save_pct,
    search_player_id,
    get_h2h_win_pct,
)
from .model import predict_game


def load_starting_goalies() -> dict:
    """Load starting_goalies.json. Format: { "YYYY-MM-DD": [ { "gameId"?: id, "homeAbbrev", "awayAbbrev", "homeGoalieId"?: id, "awayGoalieId"?: id, "homeGoalieName"?: "Name", "awayGoalieName"?: "Name" } ] }."""
    if not os.path.isfile(config.STARTING_GOALIES_PATH):
        return {}
    with open(config.STARTING_GOALIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_injuries() -> dict:
    """
    Load injuries.json if present.
    Format: { "YYYY-MM-DD": [ { "team": "COL", "player": "Name", "isTopScorer": true } ] }
    """
    if not os.path.isfile(config.INJURIES_PATH):
        return {}
    with open(config.INJURIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_goalie_sv_for_game(
    game_date: str,
    home_abbrev: str,
    away_abbrev: str,
    game_id: int,
    starting_goalies: dict,
) -> tuple[float | None, float | None]:
    """Return (home_goalie_sv_pct, away_goalie_sv_pct) from starting goalies + NHL API."""
    by_date = starting_goalies.get(game_date) or []
    home_sv = None
    away_sv = None
    for g in by_date:
        match_id = g.get("gameId") == game_id
        match_teams = (g.get("homeAbbrev") == home_abbrev and g.get("awayAbbrev") == away_abbrev)
        if not (match_id or match_teams):
            continue
        hid = g.get("homeGoalieId")
        aid = g.get("awayGoalieId")
        if hid is None and g.get("homeGoalieName"):
            hid = search_player_id(g["homeGoalieName"])
        if aid is None and g.get("awayGoalieName"):
            aid = search_player_id(g["awayGoalieName"])
        if hid is not None:
            home_sv = get_goalie_save_pct(hid)
        if aid is not None:
            away_sv = get_goalie_save_pct(aid)
        break
    return home_sv, away_sv




def run_predictions(for_date: date | None = None) -> dict:
    """
    Fetch games for a specific date, compute odds, return payload for JSON.

    - If `for_date` is provided, use it exactly (no auto-jumping to another date).
    - If `for_date` is None, default to tomorrow.
    """
    if for_date is None:
        for_date = date.today() + timedelta(days=1)
    date_str = for_date.isoformat()
    games = get_schedule(for_date)
    if not games:
        return {"date": date_str, "games": [], "message": "No upcoming games for this date."}

    standings = get_standings()
    team_stats = get_team_stats_season()
    starting_goalies = load_starting_goalies()
    injuries = load_injuries()

    results = []
    for g in games:
        home_abbrev = g.get("homeAbbrev") or ""
        away_abbrev = g.get("awayAbbrev") or ""
        game_id = g.get("id")
        by_date_inj = injuries.get(date_str) or []
        home_injury = 0.0
        away_injury = 0.0
        for inj in by_date_inj:
            team = inj.get("team")
            if team == home_abbrev:
                home_injury = max(home_injury, 1.0 if inj.get("isTopScorer") else 0.5)
            elif team == away_abbrev:
                away_injury = max(away_injury, 1.0 if inj.get("isTopScorer") else 0.5)
        home_sv, away_sv = get_goalie_sv_for_game(
            date_str, home_abbrev, away_abbrev, game_id, starting_goalies
        )
        h2h_win_pct, h2h_games = get_h2h_win_pct(home_abbrev, away_abbrev)
        prob, home_odds, away_odds = predict_game(
            home_abbrev, away_abbrev, standings, team_stats, home_sv, away_sv,
            h2h_home_win_pct=h2h_win_pct, h2h_games=h2h_games,
            home_injury=home_injury, away_injury=away_injury,
        )
        results.append({
            "gameId": game_id,
            "date": date_str,
            "homeTeam": home_abbrev,
            "awayTeam": away_abbrev,
            "homeWinProb": round(prob, 3),
            "homeAmericanOdds": home_odds,
            "awayAmericanOdds": away_odds,
        })
    return {"date": date_str, "games": results}


def write_predictions(payload: dict) -> str:
    """Write payload to config.PREDICTIONS_PATH. Return path."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    path = config.PREDICTIONS_PATH
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def main() -> None:
    """Run predictions for tomorrow and write predictions.json."""
    import sys
    for_date = None
    if len(sys.argv) > 1:
        try:
            for_date = date.fromisoformat(sys.argv[1])
        except ValueError:
            print("Usage: python -m nhl_predictor.main [YYYY-MM-DD]")
            sys.exit(1)
    payload = run_predictions(for_date)
    path = write_predictions(payload)
    print(f"Wrote {len(payload.get('games', []))} game(s) to {path}")
    for g in payload.get("games", []):
        print(f"  {g['awayTeam']} @ {g['homeTeam']}: Home {g['homeAmericanOdds']}, Away {g['awayAmericanOdds']}")


if __name__ == "__main__":
    main()
