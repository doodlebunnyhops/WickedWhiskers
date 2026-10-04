# Customizing cauldron messages

Edit `discord-bot/utils/messages.json`, under the top-level `cauldron` key. All cauldron command responses use the bot's existing `MessageLoader` in `utils/messages.py`. Restart the bot after editing; it loads the file at startup.

## Event announcements

Six independent lists are available:

- `cauldron.draw.luna.normal`
- `cauldron.draw.luna.fumble`
- `cauldron.draw.luna.special`
- `cauldron.draw.raven.normal`
- `cauldron.draw.raven.explosion`
- `cauldron.draw.raven.rage`

Add as many strings as you like to each list; the existing loader randomly chooses one. Keep at least one entry in each list. A single string is also supported. Changing these messages does not change event probabilities or rewards.

For example, replace the value of `cauldron.draw.luna.normal` with:

```json
[
    "🌙 Luna stirs the cauldron and smiles. The chosen players are {winners}!",
    "✨ A swirl of silver sparks reveals {winner_count} name(s): {winners}."
]
```

| Placeholder | Value |
| --- | --- |
| `{witch}` | Display name from `cauldron.witches`, e.g. Luna |
| `{outcome}` | Display label from `cauldron.outcomes`, e.g. fumble |
| `{winners}` | Comma-separated selected display names; player IDs when not cached |
| `{winner_count}` | Number of distinct selected players |
| `{user}` | Invoking moderator's mention text |

Announcements suppress Discord mentions. Display names are escaped for Markdown. These are selection announcements: candy payouts are still unfinished, so avoid wording that says candy has been paid.

Messages longer than 1,900 characters are preserved in an attachment along with the winner IDs. `cauldron.long_announcement` provides the short summary and supports the same placeholders; keep it brief (at most 1,900 characters).

## Other cauldron responses

| JSON path (under `cauldron`) | Placeholders |
| --- | --- |
| `no_players` | None |
| `missing_member` | `{player_id}` |
| `pool.get`, `pool.set` | `{amount}` |
| `pool.invalid` | None |
| `eligibility.title`, `eligibility.notes_title`, `eligibility.notes` | None |
| `eligibility.description` | `{player_count}`, `{amount}` |
| `eligibility.outcome_title` | `{witch}`, `{outcome}`, `{chance:g}`, `{count}` |
| `eligibility.candidate` | `{player_id}`, `{weight:g}` |
| `eligibility.none` | None |
| `eligibility.more` | `{count}` (additional candidates) |
| `eligibility.field` | `{rule}`, `{candidates}` |
| `eligibility.rules.<witch>.<outcome>` | None; editable explanation of each weighting rule |

The eligibility report and draw share selection logic; JSON only supplies wording. Keep rule descriptions accurate when customizing. Discord embed limits still apply: title 256 characters, description 4,096, field names 256, field values 1,024 and 6,000 characters across the embed.

Use valid JSON: double quotes, commas between entries, no trailing commas, and `\n` for line breaks. Preserve placeholders exactly; escape literal braces as `{{` and `}}`. Other bot/shop responses have not been globally migrated in this change.
