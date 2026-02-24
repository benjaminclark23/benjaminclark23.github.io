"""
Combine 7 factors into a single home-win probability, then to American odds.
Factors: (1) home/away, (2) last 10 W-L, (3) season W-L, (4) goalie save %, (5) special teams avg,
         (6) head-to-head this season, (7) shots on goal per game (proxy for shots/60).
"""

from .odds import probability_to_american_odds

# ========= TUNING PANEL =========
# Adjust these integer weights to change how important each factor is.
# The model internally divides by 100, so "10" means 0.10, "3" means 0.03, etc.
WEIGHT_CONFIG = {
    "home_ice": 2,         # base home advantage (~52% win rate)
    "last_10": 10,         # form over last 10 games
    "season_record": 12,   # full-season win/loss record
    "goalie": 6,           # starting goalie save %
    "special_teams": 3,    # power play + penalty kill
    "head_to_head": 8,     # vs this specific opponent this season
    "shots": 4,            # shots for per game (proxy for pace)
    "goal_diff": 6,        # goal differential per game
    "xg": 4,               # simple xG proxy from shots
    "injury": 3,           # tiny flag for key injuries
}

# Overround / vig: scale fair probabilities by (1 + margin) before converting to odds
BOOK_MARGIN = 0.03  # 3% total margin (tune to taste)

# Derived floats actually used in the formula
HOME_ICE = WEIGHT_CONFIG["home_ice"] / 100.0
WEIGHT_L10 = WEIGHT_CONFIG["last_10"] / 100.0
WEIGHT_SEASON = WEIGHT_CONFIG["season_record"] / 100.0
WEIGHT_GOALIE = WEIGHT_CONFIG["goalie"] / 100.0
WEIGHT_SPECIAL = WEIGHT_CONFIG["special_teams"] / 100.0
WEIGHT_H2H = WEIGHT_CONFIG["head_to_head"] / 100.0
WEIGHT_SHOTS = WEIGHT_CONFIG["shots"] / 100.0
WEIGHT_GOAL_DIFF = WEIGHT_CONFIG["goal_diff"] / 100.0
WEIGHT_XG = WEIGHT_CONFIG["xg"] / 100.0
WEIGHT_INJURY = WEIGHT_CONFIG["injury"] / 100.0

# Simple league-average shooting percentage used as an xG proxy
LEAGUE_AVG_SHOT_PCT = 0.095


def _norm(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def predict_home_win_prob(
    home_l10_win_pct: float,
    away_l10_win_pct: float,
    home_season_win_pct: float,
    away_season_win_pct: float,
    home_goalie_sv_pct: float | None,
    away_goalie_sv_pct: float | None,
    home_special_avg: float,
    away_special_avg: float,
    h2h_home_win_pct: float = 0.5,
    h2h_games: int = 0,
    home_shots_per_game: float = 30.0,
    away_shots_per_game: float = 30.0,
    home_goal_diff_pg: float = 0.0,
    away_goal_diff_pg: float = 0.0,
    home_xg_per_game: float = 0.0,
    away_xg_per_game: float = 0.0,
    home_injury: float = 0.0,
    away_injury: float = 0.0,
) -> float:
    """
    Return probability that the home team wins (any format: regulation, OT, SO).
    All win percentages in 0..1; save percentages in 0..1 (e.g. .915).
    h2h_home_win_pct: home's win % in H2H games this season; use 0.5 if h2h_games==0.
    Shots per game: team shots for per game (proxy for shots/60).
    """
    prob = 0.5 + HOME_ICE

    # Last 10: delta
    prob += WEIGHT_L10 * (home_l10_win_pct - away_l10_win_pct)

    # Season W-L
    prob += WEIGHT_SEASON * (home_season_win_pct - away_season_win_pct)

    # Goalie save %
    if home_goalie_sv_pct is not None and away_goalie_sv_pct is not None:
        prob += WEIGHT_GOALIE * (home_goalie_sv_pct - away_goalie_sv_pct) * 10  # .01 diff -> 0.1 prob shift

    # Special teams (already in 0..1 range typically; scale diff)
    prob += WEIGHT_SPECIAL * (home_special_avg - away_special_avg) * 5

    # Head-to-head this season (only if they've played)
    if h2h_games > 0:
        prob += WEIGHT_H2H * (h2h_home_win_pct - 0.5) * 2  # scale so 1.0 -> +0.08, 0 -> -0.08

    # Goal differential per game
    prob += WEIGHT_GOAL_DIFF * (home_goal_diff_pg - away_goal_diff_pg)

    # Shots per game (normalize diff to ~-1..1: typical range ~22–35)
    shot_diff = (home_shots_per_game - away_shots_per_game) / 15.0 if (home_shots_per_game or away_shots_per_game) else 0
    prob += WEIGHT_SHOTS * _norm(shot_diff, -1, 1)

    # Simple xG proxy based on shots (higher-volume teams get a small bump)
    xg_diff = home_xg_per_game - away_xg_per_game
    prob += WEIGHT_XG * xg_diff

    # Injury flag: missing key players reduces that team's edge slightly
    injury_delta = away_injury - home_injury  # if home is more injured, this is negative
    prob += WEIGHT_INJURY * injury_delta

    return _norm(prob, 0.01, 0.99)


def predict_game(
    home_abbrev: str,
    away_abbrev: str,
    standings: dict,
    team_stats: dict,
    home_goalie_sv_pct: float | None,
    away_goalie_sv_pct: float | None,
    h2h_home_win_pct: float = 0.5,
    h2h_games: int = 0,
    home_injury: float = 0.0,
    away_injury: float = 0.0,
) -> tuple[float, int, int]:
    """
    Return (home_win_prob, home_american_odds, away_american_odds).
    standings and team_stats are keyed by team abbrev.
    """
    home_stand = standings.get(home_abbrev) or {}
    away_stand = standings.get(away_abbrev) or {}
    home_team = team_stats.get(home_abbrev) or {}
    away_team = team_stats.get(away_abbrev) or {}

    def _float(v, default: float) -> float:
        if isinstance(v, (int, float)):
            return float(v)
        return default

    home_shots_pg = _float(home_team.get("shotsForPerGame"), 30.0)
    away_shots_pg = _float(away_team.get("shotsForPerGame"), 30.0)

    home_xg_pg = home_shots_pg * LEAGUE_AVG_SHOT_PCT
    away_xg_pg = away_shots_pg * LEAGUE_AVG_SHOT_PCT

    prob = predict_home_win_prob(
        home_l10_win_pct=home_stand.get("l10WinPct", 0.5),
        away_l10_win_pct=away_stand.get("l10WinPct", 0.5),
        home_season_win_pct=home_stand.get("seasonWinPct", 0.5),
        away_season_win_pct=away_stand.get("seasonWinPct", 0.5),
        home_goalie_sv_pct=home_goalie_sv_pct,
        away_goalie_sv_pct=away_goalie_sv_pct,
        home_special_avg=_float(home_team.get("specialTeamsAvg"), 0.5),
        away_special_avg=_float(away_team.get("specialTeamsAvg"), 0.5),
        h2h_home_win_pct=h2h_home_win_pct,
        h2h_games=h2h_games,
        home_shots_per_game=home_shots_pg,
        away_shots_per_game=away_shots_pg,
        home_goal_diff_pg=_float(home_team.get("goalDiffPerGame"), 0.0),
        away_goal_diff_pg=_float(away_team.get("goalDiffPerGame"), 0.0),
        home_xg_per_game=home_xg_pg,
        away_xg_per_game=away_xg_pg,
        home_injury=home_injury,
        away_injury=away_injury,
    )
    # Apply bookmaker-style margin before converting to American odds
    fair_home = prob
    fair_away = 1.0 - prob
    scale = 1.0 + BOOK_MARGIN
    home_with_vig = fair_home * scale
    away_with_vig = fair_away * scale

    home_odds = probability_to_american_odds(home_with_vig)
    away_odds = probability_to_american_odds(away_with_vig)
    return prob, home_odds, away_odds
