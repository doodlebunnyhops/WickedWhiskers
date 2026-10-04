"""Shared cauldron eligibility, weighting and distinct-player selection."""
import random

OUTCOMES = {
    'luna': [('normal', 76.5), ('fumble', 15), ('special', 8.5)],
    'raven': [('normal', 76.5), ('explosion', 15), ('rage', 8.5)],
}


def candidates(players, witch, outcome):
    """All supplied active players retain baseline weight 1, including newcomers."""
    if witch not in OUTCOMES or outcome not in dict(OUTCOMES[witch]):
        raise ValueError('Unknown cauldron outcome')
    result = {}
    for uid, candy, purchased, treats, given, successes, failures, stolen in players:
        treats, successes = max(0, treats), max(0, successes)
        preferred, other = (treats, successes) if witch == 'luna' else (successes, treats)
        bonus = max(0, preferred - other) if outcome in ('special', 'rage') else preferred
        result[uid] = 1 + bonus
    return list(result.items())


def roll_outcome(witch):
    if witch not in OUTCOMES:
        raise ValueError('Unknown witch')
    outcomes = OUTCOMES[witch]
    if random.random() < 0.15:
        return outcomes[1][0]
    if random.random() < 0.10:
        return outcomes[2][0]
    return 'normal'


def select_winners(weighted_players, mode):
    """Weighted sampling without replacement; never expand weights into tickets."""
    remaining = dict(weighted_players)
    if not remaining:
        return []
    count = random.randint(1, len(remaining)) if mode == 'many' else 1
    selected = []
    for _ in range(count):
        uid = random.choices(list(remaining), weights=list(remaining.values()), k=1)[0]
        selected.append(uid)
        del remaining[uid]
    return selected


def eligibility_report(players):
    report = {}
    for witch, outcomes in OUTCOMES.items():
        preferred, other = ('treats given', 'successful tricks') if witch == 'luna' else ('successful tricks', 'treats given')
        for outcome, chance in outcomes:
            rule = f'Weight: 1 + {preferred}.'
            if outcome in ('special', 'rage'):
                rule = f'Weight: 1 + max(0, {preferred} minus {other}). Equal weight 1 when nobody has a positive difference.'
            report[f'{witch.title()} {outcome} ({chance:g}%)'] = {
                'rule': rule,
                'players': candidates(players, witch, outcome),
            }
    return report
