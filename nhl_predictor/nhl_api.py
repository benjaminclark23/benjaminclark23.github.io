from datetime import date, timedelta

from . import model, nhl_api, team_stats


def run_predictions(for_date: date | None = None) -> dict:
    """Run predictions for the given date (default tomorrow)."""
    if for_date is None:
        for_date = date.today() + timedelta(days=1)

    games = nhl_api.get_schedule(for_date)
    if not games:
        return {"error": f"No games found for {for_date.isoformat()}"}

    payload_date = for_date.isoformat()
    payload = {"date": payload_date, "games": []}

    standings = nhl_api.get_standings()
    stats = nhl_api.get_team_stats_season()

    for game in games:
        home = game["homeAbbrev"]
        away = game["awayAbbrev"]
        if not home or not away:
            continue

        home_stats = stats.get(home, {})
        away_stats = stats.get(away, {})
        home_stand = standings.get(home, {})
        away_stand = standings.get(away, {})

        prediction = model.predict_game(home, away, home_stats, away_stats, home_stand, away_stand)
        payload["games"].append({
            "gameId": game["id"],
            "home": home,
            "away": away,
            "startTimeUTC": game["startTimeUTC"],
            "gameTimeLocal": game["gameTimeLocal"],
            "prediction": prediction,
        })

    return payload
