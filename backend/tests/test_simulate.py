import random

from app import data_loader, simulate


def test_run_simulation_shapes():
    teams = data_loader.load_teams()
    factors = data_loader.load_factors()
    groups = data_loader.build_groups(teams)
    weights = {f["id"]: f["default_weight"] for f in factors}

    result = simulate.run_simulation(teams, groups, weights, trials=200, seed=1)

    team_ids = {t["id"] for t in teams}

    assert len(result["team_scores"]) == len(teams)
    assert {ts["id"] for ts in result["team_scores"]} == team_ids
    assert result["team_scores"][0]["rank"] == 1

    # weights_used values are individually rounded to 4dp, so their sum can
    # be off from 1.0 by a small multiple of that rounding error.
    assert abs(sum(result["weights_used"].values()) - 1.0) < 1e-3

    assert sum(cp["probability"] for cp in result["champion_probabilities"]) <= 1.0001

    assert len(result["group_stage"]) == len(groups)
    total_qualified = 0
    for group in result["group_stage"]:
        members = groups[group["group"]]

        assert len(group["matches"]) == len(members) * (len(members) - 1) // 2
        for match in group["matches"]:
            assert match["home_goals"] >= 0
            assert match["away_goals"] >= 0

        for standing in group["standings"]:
            assert standing["points"] == standing["won"] * 3 + standing["drawn"]
            assert standing["goal_difference"] == standing["goals_for"] - standing["goals_against"]
            assert standing["played"] == len(members) - 1

        qualified = [s for s in group["standings"] if s["qualified"]]
        assert len(qualified) in (2, 3)
        total_qualified += len(qualified)

    assert total_qualified == simulate._next_power_of_two(2 * len(groups))

    rounds = result["bracket"]["rounds"]
    assert rounds[0]["name"] in ("Quarterfinals", "Round of 16", "Round of 32")
    assert rounds[-1]["name"] == "Final"
    assert result["bracket"]["champion"] in team_ids

    for round_ in rounds:
        for match in round_["matches"]:
            assert match["winner"] in (match["home"], match["away"])
            if match["home_goals"] == match["away_goals"]:
                assert match["penalties"] is not None
                assert match["penalties"]["home"] != match["penalties"]["away"]
            else:
                assert match["penalties"] is None


def test_normalize_weights_handles_zero_total():
    weights = {"a": 0, "b": 0}
    norm = simulate.normalize_weights(weights)
    assert norm == {"a": 0.5, "b": 0.5}


def test_first_knockout_round_never_repeats_a_group_stage_pairing():
    teams = data_loader.load_teams()
    factors = data_loader.load_factors()
    groups = data_loader.build_groups(teams)
    weights = {f["id"]: f["default_weight"] for f in factors}

    teams_by_id = {t["id"]: t for t in teams}
    scores = simulate.compute_power_scores(teams, weights)
    team_to_group = {tid: g for g, members in groups.items() for tid in members}

    rng = random.Random(7)
    for _ in range(200):
        _, bracket_rounds, _ = simulate._simulate_once(teams_by_id, groups, scores, rng)
        first_round = bracket_rounds[0]
        for match in first_round["matches"]:
            assert team_to_group[match["home"]] != team_to_group[match["away"]]
