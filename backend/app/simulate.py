"""Scoring + tournament simulation engine.

Pure, dependency-light functions so this can be unit tested without the
FastAPI app or any data files. Works for any group-stage tournament shape:
N groups of 4 teams, top 2 per group qualify directly, plus the best
third-place teams fill the bracket out to the next power of two (matching
both the 16-team mock (4 groups -> 8, no thirds needed) and the real
48-team 2026 format (12 groups -> 24 direct + 8 best thirds -> 32)).

Every group-stage and knockout match is scored (home_goals/away_goals),
not just won/lost/drawn, so the response can drive a full fixture list.
Goals are drawn from a binomial distribution (SCORING_CHANCES chances, each
converted independently) whose conversion rate is derived from the two
teams' power scores -- a higher power-score gap means a higher expected
goal difference. This has the same mean as a Poisson model but a hard
ceiling and lower variance, so big underdogs only very rarely blow out a
big favourite. Knockout draws go to a penalty shootout.
"""

import math
import random
from typing import Dict, List, Tuple

LOGISTIC_K = 6.0

# Average goals a team scores against an equal opponent, and how strongly
# the power-score gap shifts that average (higher GOAL_SCALE = more goals
# for the stronger side, fewer for the weaker one).
BASE_GOALS = 1.35
GOAL_SCALE = 2.2
MAX_EXPECTED_GOALS = 6.0

# Goals are sampled as "successes out of SCORING_CHANCES chances", each
# converted independently with probability expected_goals / SCORING_CHANCES.
# This binomial model has the same mean as a Poisson(expected_goals) draw
# but a hard ceiling and lower variance, so a team with a low expected-goals
# value only very rarely scores a large number of goals (vs. Poisson, whose
# tail is unbounded and proportionally heavier for small means).
SCORING_CHANCES = int(MAX_EXPECTED_GOALS)

# Round-robin matchday assignment for a 4-team group, keyed by the (i, j)
# index pair within `members` (i < j). World Cup groups are always 4 teams.
MATCHDAY_FOR_PAIR_N4 = {
    (0, 1): 1, (2, 3): 1,
    (0, 2): 2, (1, 3): 2,
    (0, 3): 3, (1, 2): 3,
}

ROUND_NAMES = {
    32: "Round of 32",
    16: "Round of 16",
    8: "Quarterfinals",
    4: "Semifinals",
    2: "Final",
}


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        n = len(weights) or 1
        return {k: 1 / n for k in weights}
    return {k: v / total for k, v in weights.items()}


def compute_power_scores(teams: List[dict], weights: Dict[str, float]) -> Dict[str, float]:
    norm_weights = normalize_weights(weights)
    scores = {}
    for team in teams:
        factors = team["factors"]
        scores[team["id"]] = sum(
            w * factors.get(factor_id, 0.0) for factor_id, w in norm_weights.items()
        )
    return scores


def _expected_win_prob(score_a: float, score_b: float) -> float:
    diff = score_a - score_b
    return 1 / (1 + 10 ** (-diff * LOGISTIC_K))


def _expected_goals(score_for: float, score_against: float) -> float:
    diff = score_for - score_against
    return min(BASE_GOALS * math.exp(GOAL_SCALE * diff), MAX_EXPECTED_GOALS)


def _binomial_sample(rng: random.Random, n: int, p: float) -> int:
    """n independent chances, each converted with probability p."""
    return sum(1 for _ in range(n) if rng.random() < p)


def _simulate_score(score_a: float, score_b: float, rng: random.Random) -> Tuple[int, int]:
    p_a = _expected_goals(score_a, score_b) / SCORING_CHANCES
    p_b = _expected_goals(score_b, score_a) / SCORING_CHANCES
    goals_a = _binomial_sample(rng, SCORING_CHANCES, p_a)
    goals_b = _binomial_sample(rng, SCORING_CHANCES, p_b)
    return goals_a, goals_b


def _simulate_score_deterministic(score_a: float, score_b: float, rng: random.Random) -> Tuple[int, int]:
    """Each side's expected goals, rounded to the nearest whole number.

    No randomness: the same weights always produce the same scoreline, and
    it always agrees with the power-score gap. Ties are real ties. `rng` is
    unused -- kept so this is interchangeable with `_simulate_score`.
    """
    goals_a = int(_expected_goals(score_a, score_b) + 0.5)
    goals_b = int(_expected_goals(score_b, score_a) + 0.5)
    return goals_a, goals_b


def _next_power_of_two(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p


def _new_standing_row() -> dict:
    return {"played": 0, "won": 0, "drawn": 0, "lost": 0, "goals_for": 0, "goals_against": 0}


def _record_result(standings: Dict[str, dict], home: str, away: str, home_goals: int, away_goals: int) -> None:
    h, a = standings[home], standings[away]
    h["played"] += 1
    a["played"] += 1
    h["goals_for"] += home_goals
    h["goals_against"] += away_goals
    a["goals_for"] += away_goals
    a["goals_against"] += home_goals

    if home_goals > away_goals:
        h["won"] += 1
        a["lost"] += 1
    elif home_goals < away_goals:
        a["won"] += 1
        h["lost"] += 1
    else:
        h["drawn"] += 1
        a["drawn"] += 1


def _standing_sort_key(tid: str, standings: Dict[str, dict], scores: Dict[str, float]):
    s = standings[tid]
    points = s["won"] * 3 + s["drawn"]
    goal_difference = s["goals_for"] - s["goals_against"]
    return (-points, -goal_difference, -s["goals_for"], -scores[tid])


def _split_into_halves(qualifiers: List[str], team_to_group: Dict[str, str], rng: random.Random) -> Tuple[List[str], List[str]]:
    """Split qualifiers into two bracket halves, keeping group-mates apart.

    Group winners/runners-up (and best-thirds) from the same group are
    distributed across the two halves so they can only meet again in the
    Final -- mirroring how real World Cup brackets are seeded. A
    greedy "smaller half first" assignment keeps the two halves equal in
    size for an even qualifier count.
    """
    by_group: Dict[str, List[str]] = {}
    for tid in qualifiers:
        by_group.setdefault(team_to_group[tid], []).append(tid)

    groups_list = list(by_group.values())
    rng.shuffle(groups_list)

    half_a: List[str] = []
    half_b: List[str] = []
    for group_teams in groups_list:
        rng.shuffle(group_teams)
        for tid in group_teams:
            if len(half_a) <= len(half_b):
                half_a.append(tid)
            else:
                half_b.append(tid)
    return half_a, half_b


def _order_avoiding_group_pairs(teams: List[str], team_to_group: Dict[str, str], rng: random.Random) -> List[str]:
    """Order teams so consecutive pairs (0,1), (2,3), ... never share a group."""
    pool = list(teams)
    rng.shuffle(pool)
    ordered: List[str] = []
    while pool:
        a = pool.pop(0)
        ordered.append(a)
        for idx, b in enumerate(pool):
            if team_to_group[b] != team_to_group[a]:
                pool.pop(idx)
                ordered.append(b)
                break
        else:
            # Every remaining team shares a's group -- only possible for the
            # final pair, when a and b are the last two same-group teams left.
            # Swap b into the previous pair (whose teams are guaranteed to be
            # from different groups than a and b) to break up both pairs
            # validly: (X, Y) + (a) -> (X, b) + (Y, a).
            b = pool.pop(0)
            if len(ordered) >= 2:
                y = ordered[-2]
                ordered[-2] = b
                ordered.append(y)
            else:
                ordered.append(b)
    return ordered


def _play_knockout_match(home: str, away: str, scores: Dict[str, float], rng: random.Random) -> dict:
    home_goals, away_goals = _simulate_score(scores[home], scores[away], rng)
    penalties = None
    if home_goals == away_goals:
        p_home = _expected_win_prob(scores[home], scores[away])
        home_wins = rng.random() < p_home
        winner_pens = rng.randint(3, 5)
        loser_pens = rng.randint(0, winner_pens - 1)
        penalties = {
            "home": winner_pens if home_wins else loser_pens,
            "away": loser_pens if home_wins else winner_pens,
        }
        winner = home if home_wins else away
    else:
        winner = home if home_goals > away_goals else away

    return {
        "home": home,
        "away": away,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "winner": winner,
        "penalties": penalties,
    }


def _play_knockout_match_deterministic(home: str, away: str, scores: Dict[str, float], rng: random.Random) -> dict:
    """Deterministic counterpart to `_play_knockout_match`.

    A drawn scoreline is settled by whichever side has the higher power
    score (ties broken in the home side's favour), with a fixed penalty
    scoreline -- there's no real-world calculation for a shootout, so this
    just needs to produce *a* winner. `rng` is unused -- kept so this is
    interchangeable with `_play_knockout_match`.
    """
    home_goals, away_goals = _simulate_score_deterministic(scores[home], scores[away], rng)
    penalties = None
    if home_goals == away_goals:
        home_wins = scores[home] >= scores[away]
        penalties = {"home": 4 if home_wins else 3, "away": 3 if home_wins else 4}
        winner = home if home_wins else away
    else:
        winner = home if home_goals > away_goals else away

    return {
        "home": home,
        "away": away,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "winner": winner,
        "penalties": penalties,
    }


def _simulate_once(
    teams_by_id: Dict[str, dict],
    groups: Dict[str, List[str]],
    scores: Dict[str, float],
    rng: random.Random,
    score_fn=_simulate_score,
    knockout_fn=_play_knockout_match,
) -> Tuple[List[dict], List[dict], str]:
    standings: Dict[str, dict] = {tid: _new_standing_row() for tid in teams_by_id}
    group_matches: Dict[str, List[dict]] = {g: [] for g in groups}

    for group_name, members in groups.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                home, away = members[i], members[j]
                home_goals, away_goals = score_fn(scores[home], scores[away], rng)
                _record_result(standings, home, away, home_goals, away_goals)
                matchday = MATCHDAY_FOR_PAIR_N4.get((i, j), 1) if len(members) == 4 else 1
                group_matches[group_name].append({
                    "matchday": matchday,
                    "home": home,
                    "away": away,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                })

    group_results = []
    direct_qualifiers: List[str] = []
    third_place: List[str] = []
    for group_name, members in groups.items():
        ranked = sorted(members, key=lambda tid: _standing_sort_key(tid, standings, scores))
        direct_qualifiers.extend(ranked[:2])
        if len(ranked) > 2:
            third_place.append(ranked[2])
        group_results.append({
            "group": group_name,
            "matches": sorted(group_matches[group_name], key=lambda m: m["matchday"]),
            "ranked": ranked,
        })

    target_size = _next_power_of_two(len(direct_qualifiers))
    extra_needed = target_size - len(direct_qualifiers)
    qualifiers = list(direct_qualifiers)
    if extra_needed > 0 and third_place:
        best_thirds = sorted(third_place, key=lambda tid: _standing_sort_key(tid, standings, scores))[:extra_needed]
        qualifiers.extend(best_thirds)

    qualified_set = set(qualifiers)
    final_group_results = [
        {
            "group": g["group"],
            "matches": g["matches"],
            "standings": [
                {
                    "id": tid,
                    "name": teams_by_id[tid]["name"],
                    "played": standings[tid]["played"],
                    "won": standings[tid]["won"],
                    "drawn": standings[tid]["drawn"],
                    "lost": standings[tid]["lost"],
                    "goals_for": standings[tid]["goals_for"],
                    "goals_against": standings[tid]["goals_against"],
                    "goal_difference": standings[tid]["goals_for"] - standings[tid]["goals_against"],
                    "points": standings[tid]["won"] * 3 + standings[tid]["drawn"],
                    "qualified": tid in qualified_set,
                }
                for tid in g["ranked"]
            ],
        }
        for g in group_results
    ]

    team_to_group = {tid: g for g, members in groups.items() for tid in members}
    half_a, half_b = _split_into_halves(qualifiers, team_to_group, rng)
    current = (
        _order_avoiding_group_pairs(half_a, team_to_group, rng)
        + _order_avoiding_group_pairs(half_b, team_to_group, rng)
    )

    bracket_rounds = []
    while len(current) > 1:
        name = ROUND_NAMES.get(len(current), f"Round of {len(current)}")
        matches = []
        next_round = []
        for i in range(0, len(current), 2):
            match = knockout_fn(current[i], current[i + 1], scores, rng)
            matches.append(match)
            next_round.append(match["winner"])
        bracket_rounds.append({"name": name, "matches": matches})
        current = next_round

    return final_group_results, bracket_rounds, current[0]


def run_simulation(
    teams: List[dict],
    groups: Dict[str, List[str]],
    weights: Dict[str, float],
    trials: int = 2000,
    seed: int = 42,
) -> dict:
    teams_by_id = {t["id"]: t for t in teams}
    scores = compute_power_scores(teams, weights)
    norm_weights = normalize_weights(weights)

    rng = random.Random(seed)
    champion_counts = {tid: 0 for tid in teams_by_id}
    for _ in range(trials):
        _, _, champion = _simulate_once(teams_by_id, groups, scores, rng)
        champion_counts[champion] += 1

    # The displayed group stage and bracket use rounded expected goals --
    # no randomness, so the same weights always produce the same result and
    # it always agrees with the power-score ranking. The bracket *draw*
    # (which qualifiers land in which half/match) still uses a seeded RNG,
    # mirroring the random draw that decides real-world bracket pairings.
    draw_rng = random.Random(seed)
    rep_group_results, rep_bracket_rounds, _ = _simulate_once(
        teams_by_id, groups, scores, draw_rng,
        score_fn=_simulate_score_deterministic,
        knockout_fn=_play_knockout_match_deterministic,
    )

    champion_probabilities = sorted(
        (
            {"id": tid, "name": teams_by_id[tid]["name"], "probability": round(count / trials, 4)}
            for tid, count in champion_counts.items()
            if count > 0
        ),
        key=lambda x: -x["probability"],
    )

    team_scores = sorted(
        (
            {"id": tid, "name": teams_by_id[tid]["name"], "power_score": round(score, 4)}
            for tid, score in scores.items()
        ),
        key=lambda x: -x["power_score"],
    )
    for rank, entry in enumerate(team_scores, start=1):
        entry["rank"] = rank

    top = champion_probabilities[0]
    explanation = (
        f"{top['name']} tops your bracket ({round(top['probability'] * 100, 1)}% of "
        f"simulations) under the current weight mix."
    )

    return {
        "weights_used": {k: round(v, 4) for k, v in norm_weights.items()},
        "team_scores": team_scores,
        "champion_probabilities": champion_probabilities,
        "group_stage": rep_group_results,
        "bracket": {"rounds": rep_bracket_rounds, "champion": rep_bracket_rounds[-1]["matches"][0]["winner"]},
        "explanation": explanation,
    }
