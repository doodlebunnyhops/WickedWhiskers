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

## Event-channel delivery and themed variants

Each draw outcome now has three themed variants (18 total). Luna’s normal draw is gentle and encouraging; her fumble is a clumsy magical accident; her special draw celebrates kindness. Raven’s normal draw is sly and teasing; her explosion is theatrical chaos; her rage is a temper tantrum favoring mischief. Every variant names the selected winners without claiming candy was paid.

Successful `/game cast spell` announcements and any long-message attachments are posted to the configured Event channel. The invoking moderator receives a private confirmation with a link. Configure it with `/bot set channel channel_type:Event channel:<channel>`; use `/bot update channel` to replace a setting. No configured/resolvable channel or missing View Channel/Send Messages permissions stops the draw before selection. Discord delivery errors are reported privately, without automatic retries or public fallback to the command channel. Attach Files is needed for long announcements.

Additional editable response keys under `cauldron`:

| Key | Placeholders |
| --- | --- |
| `event_channel_missing`, `event_channel_denied` | None |
| `event_post_failed` | `{channel}` |
| `event_posted` | `{channel}`, `{message_url}` |
