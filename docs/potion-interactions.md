# Potion interactions

All seven potions appear automatically in `/shop browse`, `/shop manage`, `/inventory`, and `/use`. Prices below are defaults; per-server overrides and sale availability apply to every potion. Purchases grant bottles; activate them before play. Repeated active copies cannot stack.

| ID | Potion | Price | Effect |
| --- | --- | ---: | --- |
| ward | Witch’s Ward | 5 | Blocks one incoming trick. |
| cunning | Raven’s Cunning | 5 | +15 percentage points on three eligible initial rolls, capped at 95% without reducing a higher base rate. |
| luna | Luna’s Calling | 10 | Immediately gives 5 candy each to up to three other eligible members; shared 60-second cooldown. |
| mirror | Mirror Brew | 10 | Redirects one incoming attempt before rolling. |
| sticky | Sticky Fingers | 8 | Adds 25% to one ordinary successful theft, rounded up and capped by available candy. |
| second_chance | Second Chance | 8 | Rerolls one failed initial trick roll once at the same effective success rate. |
| favor | Luna’s Favor | 5 | Adds half an ordinary treat, rounded down and capped at 5 candy, to the recipient’s bucket. |

## Mirror Brew

Validation occurs first: game enabled, different original attacker/target, both active and unfrozen. Ward and Mirror cannot be activated together; the rejected activation preserves its bottle. Mirror protects the original target and redirects the attempt uniformly among other eligible current non-bot members, including the attacker. The holder is excluded. Member caches are filled before resolution when necessary; a failed verification spends nothing.

The original Mirror is consumed when it redirects. A Ward on the new target blocks the attempt. A second Mirror blocks it and is consumed, but cannot redirect again. No success roll or attacking potion charge is used when protection blocks the attempt. A reflected attack can hit the caster’s own Ward or Mirror. With only the attacker and holder eligible, reflection always targets the attacker.

An unprotected redirected target with candy gets an ordinary trick attempt, using the attacker’s existing success-rate formula and Cunning/Second Chance when active. A miss moves no candy. A hit against a third player transfers candy to the attacker, with normal theft/loss counters; Sticky Fingers can add its bonus. A hit against the attacker moves their candy into the cauldron, capped by their balance. This counts as a failed trick and a candy loss for the attacker, and records their cauldron contribution. Sticky Fingers is preserved on self-reflection because no theft occurs.

Redirected attempts do not run the legacy magical trick scenarios. An empty redirected bucket ends the attempt without a roll or candy movement; Mirror remains consumed, while Cunning, Second Chance and Sticky Fingers remain available. If no verified eligible target exists, Mirror stays active and no candy moves. Active database records from another server, inactive/frozen players, bots and members no longer present cannot become redirection targets.

## Offensive potion combinations

Cunning, Second Chance and Sticky Fingers can coexist. Cunning consumes one charge for an eligible initial roll. Second Chance triggers only if that roll fails, rerolls once at the same boosted rate, and does not consume another Cunning charge. A successful first roll preserves Second Chance. Neither can bypass Ward/Mirror protection.

Sticky Fingers triggers only in the ordinary successful-transfer branch (including an ordinary redirected theft). The bonus is rounded up: a 7-candy theft gets up to 2 extra candy. If no extra candy is available, Sticky Fingers stays active. Special trick scenarios, blocked/empty attempts, failed attempts and self-reflection preserve it. The recorded transfer and theft/loss statistics include the actual bonus. The ordinary trick’s existing special outcomes still apply after a Second Chance success; the reroll does not guarantee an eventual ordinary theft.

## Luna’s Favor

The giver pays only their requested gift; Luna creates the bonus. A gift of 2 grants 1 extra candy, a gift of 5 grants 2, and gifts of 10 or more grant the maximum 5. Zero/one-candy gifts preserve Favor. Magical treat branches preserve it as well. Ordinary generous gifts qualify. The giver’s treats-given and candy-given stats count their own gift, not Luna’s bonus. Frozen participants do not trigger Favor.

The shared treat resolver is transactional and deduplicates interaction IDs for both slash commands and the Treat Player modal. A repeated request cannot transfer candy or consume Favor twice.

## Messages and persistence

Customize new narration under `potion_events` in `discord-bot/utils/messages.json`. The existing `utils/messages.py` loader handles strings, randomized lists and placeholders. Restart after editing JSON.

| Keys | Extra placeholders beyond `{user}` |
| --- | --- |
| `ward` | `{target}` |
| `cunning` | `{chance}` |
| `second_success`, `second_failure` | None |
| `sticky` | `{target}`, `{amount}` (bonus), `{total}` (full theft) |
| `favor` | `{target}`, `{amount}` (bonus) |
| `mirror_redirect` | `{original}` (protected holder), `{target}` (new target) |
| `mirror_stop`, `mirror_no_target` | `{target}` |
| `mirror_blocked`, `mirror_empty`, `mirror_failed`, `mirror_self`, `mirror_success` | `{original}`, `{target}`, `{amount}` (where applicable) |
| `mirror_title`, `mirror_members_unavailable`, `treat_replayed` | None |
| `activated` | `{potion}`, `{charges}` |

Potion-trigger narration is included in the event message alongside the trick/treat result. Cunning and Ward also now use these JSON entries when triggered. Effect charges, candy transfers, statistics and action history commit together before Discord announcements. A failed announcement cannot consume another charge. Bottles and effects persist across restarts in the existing potion tables; no database migration is needed for the four new catalog entries.
