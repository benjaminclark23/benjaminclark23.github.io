#!/usr/bin/env python3
""" 
Run NHL game predictions and write odds for multiple upcoming dates.

- By default, builds predictions for the next 14 days starting tomorrow.
- If you pass a date (YYYY-MM-DD), it builds predictions starting from that date.

Writes `nhl_data/predictions.json` in a multi-day format so the static site can
show odds for dates a week+ out.

Examples:
  python run_nhl_predictions.py
  python run_nhl_predictions.py 2026-02-25
  python run_nhl_predictions.py 2026-02-25 --days 21
"""

from datetime import date, timedelta
import sys
import json
import argparse
from pathlib import Path

from nhl_predictor.main import run_predictions

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


def write_predictions_multi(predictions: list[dict]) -> str:
    """Write predictions in a multi-day JSON format for the static site."""
    out_path = Path(__file__).resolve().parent / "nhl_data" / "predictions.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generatedAt": date.today().isoformat(),
        "predictions": predictions,
    }

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("date", nargs="?", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=14, help="How many days to generate (default: 14)")
    args, _ = parser.parse_known_args()

    # Determine start date
    if args.date:
        try:
            start_date = date.fromisoformat(args.date)
        except ValueError:
            print("Usage: python run_nhl_predictions.py [YYYY-MM-DD] [--days N]")
            sys.exit(1)
    else:
        start_date = date.today() + timedelta(days=1)

    days = max(1, min(int(args.days), 60))  # cap to keep runtime reasonable

    predictions: list[dict] = []
    total_games = 0

    for i in range(days):
        d = start_date + timedelta(days=i)
        payload = run_predictions(d)

        # Normalize structure
        games = payload.get("games", []) or []
        game_date = payload.get("date") or d.isoformat()

        predictions.append({
            "date": game_date,
            "games": games,
        })
        total_games += len(games)

    path = write_predictions_multi(predictions)

    # Print a compact summary
    print()
    print("=" * 72)
    title = f"NHL PREDICTED ODDS — {start_date.isoformat()} (+{days-1} days)"
    print(f"{BOLD}{title:^{72}}{RESET}")
    print("=" * 72)

    non_empty = [p for p in predictions if p.get("games")]
    if not non_empty:
        print("  No games scheduled in this window.")
    else:
        for block in non_empty:
            game_date = block.get("date", "")
            games = block.get("games", [])
            print(f"\n  {BOLD}{game_date}{RESET} — {len(games)} game(s)")
            for j, g in enumerate(games, 1):
                away = g.get("awayTeam")
                home = g.get("homeTeam")
                home_odds = g.get("homeAmericanOdds")
                away_odds = g.get("awayAmericanOdds")

                away_label = color_team(away) if away else "?"
                home_label = color_team(home) if home else "?"

                # Odds may be missing for far-future games if your pipeline can’t compute them yet
                home_str = f"{home_odds:+5d}" if isinstance(home_odds, int) else "  N/A"
                away_str = f"{away_odds:+5d}" if isinstance(away_odds, int) else "  N/A"

                print(f"    {j:2d}. {away_label} @ {home_label}   Home: {home_str}  Away: {away_str}")

    print("\n" + "=" * 72)
    print(f"  Wrote {len(predictions)} day(s), {total_games} total game(s) to {path}")
    print("=" * 72)
    print()
