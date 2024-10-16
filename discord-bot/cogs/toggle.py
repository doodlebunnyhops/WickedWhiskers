import discord
from discord.ext import commands
from discord import app_commands

from db_utils import get_game_settings, set_game_disabled

class CommandToggler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Define the list of commands to disable (e.g., player-related commands)
        self.commands_to_toggle = ["join", "trick", "treat"]

    @app_commands.command(name="set_game_state", description="Enable or disable the game commands.")
    @app_commands.choices(state=[
        app_commands.Choice(name="Enable", value="enable"),
        app_commands.Choice(name="Disable", value="disable")
    ])
    @commands.has_permissions(administrator=True)  # Restrict to administrators
    async def set_game_state(self, interaction: discord.Interaction, state: app_commands.Choice[str]):
        guild_id = interaction.guild.id

        # Fetch current settings from the db using db_utils
        game_disabled, _, _ = get_game_settings(guild_id)

        # Logic based on the selected option and current game state
        if state.value == "enable":
            if not game_disabled:
                await interaction.response.send_message("The game commands are already enabled for this guild.", ephemeral=True)
                return
            # Enable the specific set of commands
            for command in self.bot.tree.get_commands():
                if command.name in self.commands_to_toggle:
                    command.enabled = True
            set_game_disabled(guild_id, False)
            await interaction.response.send_message("The game commands have been enabled for this guild.", ephemeral=True)

        elif state.value == "disable":
            if game_disabled:
                await interaction.response.send_message("The game commands are already disabled for this guild.", ephemeral=True)
                return
            # Disable the specific set of commands
            self.bot.tree.get_commands()
            for command in self.bot.tree.get_commands():
                if command.name in self.commands_to_toggle:
                    command.enabled = False
            set_game_disabled(guild_id, True)
            await interaction.response.send_message("The game commands have been disabled for this guild.", ephemeral=True)

# Setup the cog
async def setup(bot):
    await bot.add_cog(CommandToggler(bot))
