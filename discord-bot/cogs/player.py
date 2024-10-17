from discord import app_commands
from discord.ext import commands
import discord
from utils import helper
from utils.utils import create_character_embed
from db_utils import get_game_settings
# from slashcmds.subgroup import subgroup
# from cogs.subgroup import subgroup

class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    buy_group = app_commands.Group(name="buy",description="Buy items from the shop")
    # subgroup = app_commands.Group(name="subgroup",description="...")
    # group.add_command(subgroup)

    @buy_group.command(name="potion", description="Buy Potion for a chance to win a prize from the cauldron!")
    async def potion(self, interaction: discord.Interaction):
        await interaction.response.send_message("You have bought a potion! Use it to get a prize from the cauldron!", ephemeral=True)
        # await helper.player_join(interaction,None)

    @app_commands.command(name="join", description="Join the game!")
    async def join(self, interaction: discord.Interaction):
        await helper.player_join(interaction,None)

    @app_commands.command(name="trick", description="Trick a player into giving you candy!")
    @app_commands.describe(
        member="The player to trick"
    )
    async def trick(self, interaction: discord.Interaction, member: discord.Member):
        await helper.player_trick(interaction,member)

    @app_commands.command(name="treat", description="Treat a player with some candy!")
    @app_commands.describe(
        member="The player to treat with candy",
        amount="The amount of candy to give"
    )
    async def treat(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        await helper.player_treat(interaction,member,amount)

    @app_commands.command(name="whois", description="Learn about the Characters in the game!")
    @app_commands.choices(character=[
        app_commands.Choice(name="Luna", value="Luna"),
        app_commands.Choice(name="Raven", value="Raven")
    ])
    async def whois(self, interaction: discord.Interaction, character: app_commands.Choice[str]):
        guild_id = interaction.guild.id
        game_disabled, _,_ = get_game_settings(guild_id)
        if game_disabled:
            print(f"Game is disabled for guild {guild_id}")
            await interaction.response.send_message("The game is currently paused.", ephemeral=True)
            return
        embed = create_character_embed(interaction.client.message_loader, character.value)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bucket", description="See how much candy you have!")
    async def bucket(self, interaction: discord.Interaction):
        await helper.player_bucket(interaction)
        

async def setup(bot):
    await bot.add_cog(Player(bot))