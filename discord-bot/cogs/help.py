"""Private, role-aware help; reading help never changes game state."""
import discord
from discord import app_commands
from discord.ext import commands
from utils.utils import has_role_or_permission

PLAYER_TOPICS = ('playing', 'potions')
MOD_TOPICS = ('setup', 'management', 'events')


def is_moderator(interaction):
    return interaction.guild is not None and has_role_or_permission(interaction.user, interaction.guild.id)


def make_embed(loader, topic):
    message = loader.get_message
    embed = discord.Embed(title=message('help', topic, 'title'), description=message('help', topic, 'description'), color=discord.Color.orange())
    fields = loader.get_message_block('help', topic, 'fields', default={})
    for key in fields:
        embed.add_field(name=message('help', topic, 'fields', key, 'name'), value=message('help', topic, 'fields', key, 'value'), inline=False)
    embed.set_footer(text=message('help', 'footer'))
    return embed


class HelpTopics(discord.ui.Select):
    def __init__(self, view, moderator):
        topics = PLAYER_TOPICS + (MOD_TOPICS if moderator else ())
        message = view.loader.get_message
        super().__init__(placeholder=message('help', 'choose_topic'), options=[discord.SelectOption(label=message('help', key, 'label'), description=message('help', key, 'hint'), value=key, default=key=='playing') for key in topics])

    async def callback(self, interaction):
        topic = self.values[0]
        # Recheck roles on navigation, including if access was removed after opening.
        if topic not in PLAYER_TOPICS + MOD_TOPICS or (topic in MOD_TOPICS and not is_moderator(interaction)):
            await interaction.response.send_message(self.view.loader.get_message('help', 'denied'), ephemeral=True)
            return
        for option in self.options:
            option.default = option.value == topic
        await interaction.response.edit_message(embed=make_embed(self.view.loader, topic), view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, interaction):
        super().__init__(timeout=600)
        self.owner_id = interaction.user.id
        self.loader = interaction.client.message_loader
        self.add_item(HelpTopics(self, is_moderator(interaction)))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(self.loader.get_message('help', 'not_owner'), ephemeral=True)
            return False
        return True


class Help(commands.Cog):
    @app_commands.command(name='help', description='Open your private player guide and available moderator help.')
    @app_commands.guild_only()
    async def help(self, interaction: discord.Interaction):
        view = HelpView(interaction)
        await interaction.response.send_message(embed=make_embed(view.loader, 'playing'), view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help())
