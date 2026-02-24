# NHL Game Predictor

Predicts each NHL game with a **single gambling-style probability** in American odds: **negative** = favoured (e.g. **-150**), **positive** = underdog (e.g. **+130**). Run it **every game day** (e.g. each morning) to refresh predictions; it writes `nhl_data/predictions.json` so another app or AI agent can consume it easily.

## The 7 factors

1. **Home vs away** – home-ice advantage.
2. **Last 10 games** – wins/losses (W–L–OTL) from NHL standings.
3. **Season wins vs losses** – current-season win % from standings only.
4. **Starting goalie** – save % for that night’s starters (Daily Faceoff + NHL player API; optional, falls back to no goalie factor if missing).
5. **Special teams** – average of team power-play % and penalty-kill % from NHL stats API.
6. **Head-to-head this season** – past performance against that specific opponent this year (from NHL schedule/results).
7. **Shots on goal** – shots for per game (proxy for shots/60) from NHL stats API.

## Run locally

```bash
cd /path/to/NHL-odds-predictor
python run_nhl_predictions.py
# or for a specific date:
python run_nhl_predictions.py 2026-02-25
```

- Uses **tomorrow’s date** by default (run each game day, e.g. morning before games).
- Fetches schedule and standings from `api-web.nhle.com`, team stats from `api.nhle.com`. **No API key required**; you can set `NHL_API_KEY` in the environment if you have one for rate limits or alternate sources.
- Reads starting goalies from `nhl_data/starting_goalies.json` (see below).
- Writes **`nhl_data/predictions.json`** with one object per game: `gameId`, `date`, `homeTeam`, `awayTeam`, `homeWinProb`, `homeAmericanOdds`, `awayAmericanOdds` — ready for an app or another agent to consume.

## Starting goalies (Daily Faceoff)

Daily Faceoff does **not** provide a public API. You have two options:

### Option A: Manual (or another agent) update

1. Open [Daily Faceoff – Starting Goalies](https://www.dailyfaceoff.com/starting-goalies/) for the date you care about.
2. For each game, copy the confirmed starters into `nhl_data/starting_goalies.json`.

Format:

```json
{
  "YYYY-MM-DD": [
    {
      "homeAbbrev": "WSH",
      "awayAbbrev": "PHI",
      "homeGoalieName": "Charlie Lindgren",
      "awayGoalieName": "Samuel Ersson"
    }
  ]
}
```

- You can use **`gameId`** (from schedule) or **`homeAbbrev`/`awayAbbrev`** to match games.
- Use **`homeGoalieName` / `awayGoalieName`** (the code will look up NHL player ID and then save %) or **`homeGoalieId` / `awayGoalieId`** (NHL player ID) if you have them.

If a game has no entry, the model still runs but does not use the goalie factor for that game.

### Option B: Scraper / separate automation

- Another script or AI agent can scrape Daily Faceoff (respect their terms of use) and write the same JSON structure to `starting_goalies.json`.
- Or you can build a small Cloud Function that you (or a cron) call after you paste the goalie list somewhere; that function writes this file (e.g. in Cloud Storage) and then triggers the predictor.

## What to do on Google Cloud

You don’t need Google Cloud to **get** NHL or Daily Faceoff data; the NHL APIs are public. Use Google Cloud only if you want to **run this predictor on a schedule** and/or **store results** for your app.

### 1. Run the predictor on a schedule (daily before game day)

- **Cloud Scheduler** + **Cloud Functions** (or **Cloud Run**):
  - Create a Cloud Function (or Run service) that runs `python -m nhl_predictor.main` (or an HTTP handler that calls `run_predictions()` and then stores the result – see below).
  - In Cloud Scheduler, create a job that triggers that function once per day (e.g. 8:00 AM ET) so predictions are ready before that night’s games.
- You’ll need:
  - A **GCP project**.
  - **Cloud Scheduler API** and **Cloud Functions** (or **Cloud Run**) API enabled.
  - The function’s code and dependencies deployed (e.g. with a `requirements.txt` and the `nhl_predictor` package). No secrets are required for the NHL APIs.

### 2. Store predictions so your app can read them

- **Cloud Storage**: After `run_predictions()`, upload the JSON to a bucket (e.g. `gs://your-bucket/nhl_data/predictions.json`). Your app (or another agent) reads from that URL or via the Storage API.
- **Firestore**: Write each game (or the whole payload) into a collection/document (e.g. `predictions/2026-02-25`) so the app can query by date.
- **BigQuery**: Append a row per game (date, gameId, homeTeam, awayTeam, homeAmericanOdds, awayAmericanOdds, homeWinProb) for analytics and backtesting.

### 3. Getting “info for the games” (schedule, etc.)

- **You do not need any special GCP product to get NHL game info.** The code uses:
  - `https://api-web.nhle.com/v1/schedule/YYYY-MM-DD`
  - `https://api-web.nhle.com/v1/standings/now`
  - `https://api.nhle.com/stats/rest/en/team/summary?...`
  - `https://api-web.nhle.com/v1/player/{id}/landing`
- If you want to **cache** this data in GCP (e.g. to avoid rate limits or to share with other services), you can:
  - Store raw schedule/standings in **Cloud Storage** or **Firestore** and have your function read from there when appropriate, or
  - Use **Cloud Memorystore** only if you need a shared cache across instances; for a single daily job, writing to a file or Firestore is enough.

### Minimal “next steps” checklist for GCP

1. Create a GCP project and enable **Cloud Scheduler** and **Cloud Functions** (or **Cloud Run**).
2. Package the predictor (e.g. a single HTTP Cloud Function that calls `run_predictions()`, then uploads the result to Cloud Storage or writes to Firestore).
3. Create a **Cloud Scheduler** job that runs that function once per day (e.g. 8 AM ET).
4. Ensure **starting goalies** are in `starting_goalies.json` (or the equivalent stored in GCS/Firestore and loaded by the function) – either by hand from Daily Faceoff or via a separate scraper/agent.

Your app (or another AI agent) can then read predictions from Storage/Firestore/BigQuery and display the single American-odds line per game.

## App / agent integration

The predictor is built so another app or AI agent can use it without change:

- **Input**: Optional `nhl_data/starting_goalies.json`; everything else comes from public NHL APIs.
- **Output**: `nhl_data/predictions.json` (or your deployed path) with structure:
  - `date`: game date (YYYY-MM-DD)
  - `games`: array of `{ "gameId", "date", "homeTeam", "awayTeam", "homeWinProb", "homeAmericanOdds", "awayAmericanOdds" }`
- **Update cadence**: Run once per game day (e.g. cron at 8 AM ET) so odds reflect that day’s games and latest data.
