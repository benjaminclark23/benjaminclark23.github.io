from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import date, timedelta

from nhl_predictor.main import run_predictions

app = FastAPI(title="NHL Odds Predictor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static assets at /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the homepage explicitly
@app.get("/")
def home():
    return FileResponse("static/index.html")

def default_tomorrow_str() -> str:
    return (date.today() + timedelta(days=1)).isoformat()

from fastapi import HTTPException
from datetime import date

@app.get("/api/predictions")
def predictions(date_str: str = Query(default=None, alias="date")):
    # If no date provided, use tomorrow as a date object
    if not date_str:
        for_date = date.today() + timedelta(days=1)
    else:
        # Convert "YYYY-MM-DD" -> datetime.date
        try:
            for_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Date must be YYYY-MM-DD")

    return run_predictions(for_date)

# Optional quick sanity check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

from datetime import date, timedelta

def next_game_day(max_lookahead_days: int = 10) -> date:
    today = date.today()
    for i in range(1, max_lookahead_days + 1):
        d = today + timedelta(days=i)
        payload = run_predictions(d)
        if payload.get("games"):
            return d
    return today + timedelta(days=1)  # fallback

@app.get("/api/predictions")
def predictions(date_str: str = Query(default=None, alias="date")):
    if not date_str:
        for_date = next_game_day()
    else:
        try:
            for_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Date must be YYYY-MM-DD")

    return run_predictions(for_date)