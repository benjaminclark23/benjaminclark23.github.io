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

@app.get("/api/predictions")
def predictions(date_str: str = Query(default=None, alias="date")):
    """Return predictions for a specific date.

    - If `date` is provided (YYYY-MM-DD), run predictions for that date.
    - If not provided, default to tomorrow.

    This endpoint should NOT auto-skip forward to the next game day; the caller/UI
    controls which date to request.
    """
    if not date_str:
        for_date = date.today() + timedelta(days=1)
    else:
        try:
            for_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Date must be YYYY-MM-DD")

    return run_predictions(for_date)

# Optional quick sanity check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}