# Game artwork

All 26 Discord CDN URLs are in the `artwork` section of
`discord-bot/utils/messages.json`. Change a URL there and restart the bot.
The existing character `image_url` and `image_banner_url` entries use
`asset:<key>` aliases, resolved by `MessageLoader`, so each URL is stored once.

The catalog is loaded once into memory. Embed construction only looks up URL
strings: the bot does not download, resize, upload, poll, or refresh images.
There are no schema changes or database migrations.

Discord's documented embed behavior accepts attachment CDN URLs without query
parameters and renders and refreshes URLs itself. Store only the attachment path,
not temporary `ex`, `is`, `hm`, or `backend` parameters. These are embed URLs,
not guaranteed permanent direct-download URLs. Keep the original Discord
attachment messages available.

Reference: https://docs.discord.com/developers/reference#signed-attachment-cdn-urls

## Display mapping

| Artwork | Display |
| --- | --- |
| Luna/Raven portraits | Trick/treat thumbnails, character profiles, cauldron author icons |
| Luna/Raven banners | `/whois` main images |
| Shared welcome scene | Newly posted game join embeds |
| Luna/Raven cauldrons | Cauldron spell main images and existing special contribution scenes |
| Luna candy shower | Existing mass treat event and Luna's Calling announcement |
| Four pumpkin images | Existing pumpkin result thumbnails |
| Candy bucket | Private `/bucket` response |
| Inventory | Private inventory embed |
| Potion shop | Newly posted permanent shop entrance embed |
| Leaderboard | Leaderboard thumbnail |
| Frozen player | Public freeze announcement (not thaw) |
| Cooldown | Private rejected Luna's Calling activation |
| Seven regular potion icons | Private checkout, receipt, and activation response |
| Witch's Veil | Private protection overview, quote, and activation confirmation |

Privacy, persistent button IDs, pricing, ownership checks, and gameplay remain
unchanged. Image URLs do not go inside modal controls; the selected potion's
art appears in the private checkout embed after the modal is submitted.

Existing Discord messages are not rewritten by a restart. Repost the shop
entrance with `/shop post`; use the normal join-message setup command to post
an updated invite. New responses immediately use the new artwork.
