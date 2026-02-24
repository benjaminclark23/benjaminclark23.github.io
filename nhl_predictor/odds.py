"""
Convert win probability to American odds (e.g. -150 favoured, +130 underdog).
"""


def probability_to_american_odds(prob: float) -> int:
    """
    Convert home win probability to American odds for the home team.
    - Favoured (prob > 0.5): negative odds, e.g. -150
    - Underdog (prob < 0.5): positive odds, e.g. +130
    - 50%: return 100 (evens) or -100 depending on convention; we use +100 for 50%
    """
    prob = max(0.001, min(0.999, prob))
    if prob >= 0.5:
        # Favoured: American = -(prob / (1 - prob)) * 100, rounded to sensible increment
        raw = (prob / (1 - prob)) * 100
        return -int(round(raw))
    else:
        # Underdog: American = ((1 - prob) / prob) * 100
        raw = ((1 - prob) / prob) * 100
        return int(round(raw))
