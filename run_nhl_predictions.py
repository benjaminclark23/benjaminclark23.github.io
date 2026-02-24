#!/usr/bin/env python3
"""
Run NHL game predictions and show odds for the next game day (or a given date).
Writes nhl_data/predictions.json and prints odds for every game that night.

  python run_nhl_predictions.py              # next date that has games
  python run_nhl_predictions.py 2026-02-25   # specific date
"""

from datetime import date
import sys

from nhl_predictor.main import run_predictions, write_predictions

# Simple ANSI colors per team (approximate primary colors)
RESET = "\033[0m"
BOLD = "\033[1m"

TEAM_COLORS: dict[str, str] = {
    # Eastern
    "BOS": "\033[33m",  # yellow
    "BUF": "\033[34m",
    "DET": "\033[31m",
    "FLA": "\033[31m",
    "MTL": "\033[31m",
    "OTT": "\033[31m",
    "TBL": "\033[36m",
    "TOR": "\033[34m",
    "CAR": "\033[31m",
    "CBJ": "\033[34m",
    "NJD": "\033[31m",
    "NYI": "\033[34m",
    "NYR": "\033[34m",
    "PHI": "\033[33m",
    "PIT": "\033[33m",
    "WSH": "\033[31m",
    # Western
    "ANA": "\033[33m",
    "ARI": "\033[31m",
    "CGY": "\033[31m",
    "CHI": "\033[31m",
    "COL": "\033[35m",
    "DAL": "\033[32m",
    "EDM": "\033[34m",
    "LAK": "\033[37m",
    "MIN": "\033[32m",
    "NSH": "\033[33m",
    "SEA": "\033[36m",
    "SJS": "\033[36m",
    "STL": "\033[34m",
    "VAN": "\033[32m",
    "VGK": "\033[33m",
    "WPG": "\033[36m",
}


def color_team(abbrev: str) -> str:
    code = TEAM_COLORS.get(abbrev.upper(), "\033[37m")
    return f"{BOLD}{code}{abbrev}{RESET}"


if __name__ == "__main__":
    for_date = None
    if len(sys.argv) > 1:
        try:
            for_date = date.fromisoformat(sys.argv[1])
        except ValueError:
            print("Usage: python run_nhl_predictions.py [YYYY-MM-DD]")
            sys.exit(1)

    payload = run_predictions(for_date)
    path = write_predictions(payload)
    games = payload.get("games", [])
    game_date = payload.get("date", "")

    # Show odds for all games on this game day
    print()
    print("=" * 72)
    title = f"NHL PREDICTED ODDS — {game_date}"
    print(f"{BOLD}{title:^{72}}{RESET}")
    print("=" * 72)
    if not games:
        print("  No games scheduled for this date.")
        print("  (Predictions file written with empty games.)")
    else:
        for i, g in enumerate(games, 1):
            away = g["awayTeam"]
            home = g["homeTeam"]
            home_odds = g["homeAmericanOdds"]
            away_odds = g["awayAmericanOdds"]

            away_label = color_team(away)
            home_label = color_team(home)

            print(f"  {i:2d}. {away_label} @ {home_label}")
            print(
                f"       Home: {home_odds:+5d}   "
                f"Away: {away_odds:+5d}"
            )
            print()
    print("=" * 72)
    print(f"  Wrote {len(games)} game(s) to {path}")
    print("=" * 72)
    print()
