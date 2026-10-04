"""Read-only explanation of the restored pumpkin cauldron selection rules."""
from utils.player import calculate_evilness, calculate_sweetness


def eligibility_report(players):
    # Keep these formulas aligned with cogs/game_commands/cast.py.
    report = {
        "Luna normal (76.5%)": {"rule": "Weight: legacy potion purchases.", "players": []},
        "Luna fumble (15%)": {"rule": "Requires legacy purchases; weight: sweetness + purchases.", "players": []},
        "Luna special (8.5%)": {"rule": "Requires sweetness > evilness; weight: difference.", "players": []},
        "Raven normal (76.5%)": {"rule": "Weight: successful tricks.", "players": []},
        "Raven explosion (15%)": {"rule": "Requires successful tricks; weight: legacy evilness.", "players": []},
        "Raven rage (8.5%)": {"rule": "Requires evilness > sweetness; weight: difference.", "players": []},
    }
    groups = list(report.values())
    for uid, candy, purchased, treats, given, successes, failures, stolen in players:
        sweet = max(calculate_sweetness(given, treats), 1)
        luna_evil = max(calculate_evilness(stolen, failures), 1)
        raven_explosion = max(calculate_evilness(stolen, successes), 1)
        raven_rage = max(calculate_evilness(stolen, successes - failures), 1)
        weights = [
            purchased,
            sweet + purchased if purchased > 0 else 0,
            sweet - luna_evil if sweet > luna_evil else 0,
            successes if successes > 0 else 0,
            raven_explosion if successes > 0 else 0,
            raven_rage - sweet if raven_rage > sweet else 0,
        ]
        for group, weight in zip(groups, weights):
            if weight > 0:
                group["players"].append((uid, weight))
    return report
