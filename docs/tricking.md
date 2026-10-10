# Trick rules

Ordinary theft takes a uniformly sampled 2–6% of the final target's pre-action bucket. There is no fixed candy ceiling. Amounts round to the nearest candy (halves up), minimum 1 for a positive bucket, never exceeding available candy.

Initial success probability is `0.10 + 0.80 × target / (attacker + target)`: equal buckets give 50%; poorer attackers approach 90%, richer attackers approach 10%. Cunning adds 15 percentage points, capped at 95%, for one charge. Second Chance rerolls a failed initial roll once at the same rate.

After initial success, check in order:

1. If the final target has **more than 100 candy**, a 0.1% roll steals the entire bucket.
2. Otherwise, a 10% roll makes both lose the same amount: 1–3% of the smaller bucket. Each loss goes to the cauldron. If either bucket is empty, the amount is zero.
3. Otherwise, a 15% roll lets the target reclaim one candy if the sampled theft exceeds 5.
4. Otherwise, ordinary theft occurs. Sticky Fingers adds a fresh random 25–50% of that theft, rounded half up with minimum 1, capped by remaining target candy. It consumes one of three charges only when extra candy is taken.

After initial failure: a 10% roll invokes the shared loss; otherwise another 10% roll gives a consolation theft of half the sampled theft (rounded half up). Otherwise the attacker transfers 1–3% of their own bucket to the target. These are sequential conditional probabilities, not additive overall chances.

Ward and Mirror are resolved before rolling. Redirects use the **new target** for both probability and amounts, including special outcomes. Another Mirror blocks rather than redirecting again. Self-reflection uses the attacker's own bucket (50% base success); any resulting loss goes to the cauldron **once**, including a rare full drain. An ordinary reflected failure moves nothing. Self-reflection counts as a failed trick, preserves Sticky Fingers, and records the actual candy loss/contribution. Cunning and Second Chance can still trigger.

Blocked attempts preserve attacking potion charges. Empty redirected buckets end without a roll. Original empty targets retain their sympathy/duel/no-candy scenarios; these do not consume attacking potions. Freeze and Veil checks remain server-specific.

All balance updates, potion charges, statistics and the interaction receipt commit together. Repeated requests cannot settle twice. Special outcomes preserve Sticky Fingers. Receivers never pay an additional entry fee. The default Sticky Fingers price remains 8 candy; existing active effects keep their remaining charges.

Public narration uses `scaled_tricks` in `messages.json`, loaded through `messages.py`. It shows actual candy moved, not remaining balances; a full drain can explicitly announce the entire loss. Player stats show the equal-bucket reference chance rather than claiming a fixed chance against everyone.

Attempts against a player under Witch’s Veil receive a private, randomly selected Raven message for tricks or Luna message for treats. These responses do not disclose the timer or remaining candy; frozen/inactive targets retain the generic unavailable response.
