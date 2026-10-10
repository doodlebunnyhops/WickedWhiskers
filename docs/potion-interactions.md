# Potion interactions

All seven bottled potions appear automatically in `/shop browse`, `/shop manage`, `/inventory`, and `/use`. Prices below are defaults; per-server overrides and sale availability apply to every potion. Purchases grant bottles; activate them before play. Repeated active copies cannot stack.

| ID | Potion | Price | Effect |
| --- | --- | ---: | --- |
| ward | Witch’s Ward | 5 | Blocks one incoming trick. |
| cunning | Raven’s Cunning | 5 | +15 percentage points on three eligible initial rolls, capped at 95% without reducing a higher base rate. |
| luna | Luna’s Calling | 10 | Immediately gives 5 candy each to up to three other eligible members; shared 60-second cooldown. |
| mirror | Mirror Brew | 10 | Redirects one incoming attempt before rolling. |
| sticky | Sticky Fingers | 8 | Adds a random 25–50% of the stolen amount on the next 3 ordinary successful thefts, capped by available candy. |
| second_chance | Second Chance | 8 | Rerolls one failed initial trick roll once at the same effective success rate. |
| favor | Luna’s Favor | 5 | Adds half an ordinary treat, rounded down and capped at 5 candy, to the recipient’s bucket. |

## Mirror Brew

Validation occurs first: game enabled, different original attacker/target, both active and unfrozen. Ward and Mirror cannot be activated together; the rejected activation preserves its bottle. Mirror protects the original target and redirects the attempt uniformly among other eligible current non-bot members, including the attacker. The holder is excluded. Member caches are filled before resolution when necessary; a failed verification spends nothing.

The original Mirror is consumed when it redirects. A Ward on the new target blocks the attempt. A second Mirror blocks it and is consumed, but cannot redirect again. No success roll or attacking potion charge is used when protection blocks the attempt. A reflected attack can hit the caster’s own Ward or Mirror. With only the attacker and holder eligible, reflection always targets the attacker.

An unprotected redirected target with candy uses the same [percentage trick rules](tricking.md) as an original target, including special outcomes. The final target's bucket determines the amount and relative success chance. Third-player transfers update ordinary theft/loss counters. Self-reflection sends any resulting loss into the cauldron once, records a failed trick and contribution, and preserves Sticky Fingers. A normal reflected failure moves no candy.

An empty redirected bucket ends the attempt without a roll or candy movement; Mirror remains consumed, while Cunning, Second Chance and Sticky Fingers remain available. If no verified eligible target exists, Mirror stays active and no candy moves. Active database records from another server, inactive/frozen/protected players, bots and members no longer present cannot become redirection targets.

## Offensive potion combinations

Cunning, Second Chance and Sticky Fingers can coexist. Cunning consumes one charge for an eligible initial roll. Second Chance triggers only if that roll fails, rerolls once at the same boosted rate, and does not consume another Cunning charge. A successful first roll preserves Second Chance. Neither can bypass Ward/Mirror protection.

Sticky Fingers triggers only in the ordinary successful-transfer branch (including an ordinary redirected theft). Each new activation has 3 charges. A 200-candy theft gets 50–100 extra candy; one charge is consumed only when at least one extra candy is stolen. If no extra candy is available, Sticky Fingers stays active. Special trick scenarios, blocked/empty attempts, failed attempts and self-reflection preserve it. The recorded transfer and theft/loss statistics include the actual bonus. Existing active effects and bottles returned by a freeze retain their remaining charges; unused full bottles receive 3 charges when activated. The ordinary trick’s existing special outcomes still apply after a Second Chance success; the reroll does not guarantee an eventual ordinary theft.

## Luna’s Favor

The giver pays only their requested gift; Luna creates the bonus. A gift of 2 grants 1 extra candy, a gift of 5 grants 2, and gifts of 10 or more grant the maximum 5. Zero/one-candy gifts preserve Favor. Magical treat branches preserve it as well. Ordinary generous gifts qualify. The giver receives one kindness action; candy-given includes both their gift and Luna’s actual bonus. Favor does not add a second action. Frozen participants do not trigger Favor.

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

## Witch’s Veil and returned charges

Veil is a separate timed purchase available through the shop. It prevents all other potion activation and targeting, including Mirror redirection and Calling gifts. Existing charged effects wait without being consumed while protected. Moderation freezes return only unused charges; see [freeze and protection rules](freeze-and-protection.md).

Potion narration follows the shared [gameplay message rules](gameplay-messages.md): identify each player once, then use their escaped display name, including multi-player Mirror scenes.
