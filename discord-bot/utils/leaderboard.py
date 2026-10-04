"""Leaderboard presentation. Each page stays within Discord's embed limits."""
import discord
from utils.artwork import image_url

CATEGORIES = (
    'top_tricksters', 'top_treaters', 'top_thieves', 'most_generous',
    'most_evil', 'most_sweet', 'highest_risk_takers', 'candy_hoarders',
)


def make_embed(interaction, key, rows, page=None):
    message = interaction.client.message_loader.get_message
    name = message('leaderboard', 'categories', key, 'name')
    unit = message('leaderboard', 'categories', key, 'unit')
    lines = []
    for rank, (uid, score) in enumerate(rows[:10], 1):
        member = interaction.guild.get_member(uid)
        player = discord.utils.escape_mentions(discord.utils.escape_markdown(member.display_name[:64])) if member else message('leaderboard', 'missing_member', player_id=uid)
        lines.append(message('leaderboard', 'entry', rank=rank, player=player, score=f'{score * 100:.2f}%' if key in ('most_evil', 'most_sweet') else f'{score:,}', unit=unit))
    embed = discord.Embed(
        title=message('leaderboard', 'title', category=name),
        description='\n'.join(lines) if lines else message('leaderboard', 'empty', category=name),
        color=discord.Color.gold(),
    )
    if page is not None:
        embed.set_footer(text=message('leaderboard', 'page', current=page+1, total=len(CATEGORIES)))
    embed.set_thumbnail(url=image_url('leaderboard'))
    return embed


class LeaderboardView(discord.ui.View):
    def __init__(self, interaction, boards):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.boards = boards
        self.index = 0
        message = interaction.client.message_loader.get_message
        self.selector = discord.ui.Select(placeholder=message('leaderboard', 'choose'), options=[discord.SelectOption(label=message('leaderboard', 'categories', key, 'name'), value=key, default=index==0) for index,key in enumerate(CATEGORIES)])
        self.selector.callback = self.choose
        self.previous_button = discord.ui.Button(label=message('leaderboard', 'previous'), disabled=True)
        self.next_button = discord.ui.Button(label=message('leaderboard', 'next'))
        self.previous_button.callback = self.previous
        self.next_button.callback = self.next
        for item in (self.selector, self.previous_button, self.next_button):
            self.add_item(item)

    def embed(self):
        key = CATEGORIES[self.index]
        return make_embed(self.interaction, key, self.boards[key], self.index)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message(self.interaction.client.message_loader.get_message('leaderboard', 'owner_only'), ephemeral=True)
            return False
        return True

    async def refresh(self, interaction):
        self.previous_button.disabled = self.index == 0
        self.next_button.disabled = self.index == len(CATEGORIES)-1
        for option in self.selector.options:
            option.default = option.value == CATEGORIES[self.index]
        await interaction.response.edit_message(embed=self.embed(), view=self, allowed_mentions=discord.AllowedMentions.none())

    async def previous(self, interaction):
        self.index = max(0, self.index-1)
        await self.refresh(interaction)

    async def next(self, interaction):
        self.index = min(len(CATEGORIES)-1, self.index+1)
        await self.refresh(interaction)

    async def choose(self, interaction):
        self.index = CATEGORIES.index(self.selector.values[0])
        await self.refresh(interaction)

    async def on_timeout(self):
        try:
            await self.interaction.edit_original_response(view=None)
        except discord.HTTPException:
            pass
