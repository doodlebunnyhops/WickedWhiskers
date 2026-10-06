# Gameplay announcements

Completed tricks, treats (including the context-menu modal), and pumpkin smashes
produce one public result. The bot temporarily defers the invoking interaction
privately and removes that acknowledgement after the public post succeeds.
Rejected actions remain private. If public delivery fails, a private notice states
that the result was saved; it does not replay the gameplay transaction.

The configured event channel is used, with the invoking channel as the existing
fallback. There are no webhook, intent, membership, or database optimization changes
in this update. Discord client appearance has not been verified by an automated live test.

Player mentions are normalized after assembling the full announcement, including
potion notes and embed fields. Each user ID is mentioned once, followed by escaped
display names on repeat references. Equal display names include their IDs on repeats;
unknown names fall back to IDs. Mirror redirects are narrated before their outcome.

Public text states actual gains/losses and destinations. A lost pumpkin amount that
feeds the cauldron is the same loss, not another charge. Special Luna treats retain
their existing magical candy creation, with exact rewards and gifted Ward bottles
stated publicly. Remaining balances are omitted except for genuine full-bucket drains.
The compact pumpkin wager/net-change summary is retained.

Luna encourages kindness and sharing. Raven celebrates mischief and reacts with
sarcasm and theatrical indignation. Veiled players receive neutral bucket narration
and pumpkin variants where neither witch notices them.

Bucket response tiers:

- Empty: 0 candy.
- Small: 1–49 candy.
- Growing: 50–499 candy.
- Large: 500+ candy.

The private bucket screen always displays the exact candy amount and inventory bottle
count independently. Shop/activation confirmations, inventory, and moderator screens
remain private. Luna's Calling cooldown errors use a Discord relative timestamp and
explicitly state the potion was not consumed.

Active message templates are in `utils/messages.json`, read through `MessageLoader`.
Old private outcome templates remain for compatibility but are not sent as duplicate
gameplay results.
