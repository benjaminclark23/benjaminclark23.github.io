# NHL Game Predictor

Predicts each NHL game with a **single gambling-style probability** in American odds: **negative** = favoured (e.g. **-150**), **positive** = underdog (e.g. **+130**). Run it **every game day** to refresh predictions.

## The 7 factors

1. **Home vs away** – home-ice advantage.
2. **Last 10 games** – wins/losses (W–L–OTL) from NHL standings.
3. **Season wins vs losses** – current-season win % from standings only.
4. **Starting goalie** – save % for that night’s starters (Daily Faceoff + NHL player API; optional, falls back to no goalie factor if missing).
5. **Special teams** – average of team power-play % and penalty-kill % from NHL stats API.
6. **Head-to-head this season** – past performance against that specific opponent this year (from NHL schedule/results).
7. **Shots on goal** – shots for per game (proxy for shots/60) from NHL stats API.

