
import discord
from discord import app_commands
import utils.checks as checks
from db_utils import get_game_settings, set_game_disabled,get_cauldron_pool,is_player_active,update_player_field,set_cauldron_pool,set_game_setting


# Subcommand group for setting (used within the server group)
set_group = app_commands.Group(name="set", description="Set commands")

@set_group.command(name="settings", description="Update the game settings.")
@checks.check_if_has_permission_or_role()
async def set_game_settings_cmd(interaction: discord.Interaction):
    import admin_settings as shared
    await interaction.response.send_message(shared.summary(interaction.guild_id), view=shared.GameSettingsView(interaction), ephemeral=True)

@set_group.command(name="cauldron", description="Set the amount of candy in the cauldron.")
@checks.check_if_has_permission_or_role()
async def set_cauldron_pool_amount(interaction: discord.Interaction, amount: int):
    guild_id = interaction.guild.id

    # Validate the input value
    if amount < 0:
        await interaction.response.send_message(interaction.client.message_loader.get_message("cauldron", "pool", "invalid"), ephemeral=True)
        return

    # Update the cauldron pool in the database
    import admin_settings as shared
    shared.set_pool(guild_id, amount)

    await interaction.response.send_message(interaction.client.message_loader.get_message("cauldron", "pool", "set", amount=amount), ephemeral=True)

@set_group.command(name="player_stat", description="Set Player stat")
@checks.check_if_has_permission_or_role()
@app_commands.choices(stat=[
    app_commands.Choice(name="Candy", value="candy_in_bucket"),
    app_commands.Choice(name="Successful Tricks", value="successful_tricks"),
    app_commands.Choice(name="Failed Tricks", value="failed_tricks"),
    app_commands.Choice(name="Treats Given", value="treats_given"),
])
@app_commands.describe(
    user="The player you want to modify",
    stat="The stat you want to change (e.g., candy_in_bucket)",
    number="The value you want to set for the stat"
)
async def set_player_stat(interaction: discord.Interaction, user: discord.Member, stat: str, number: int):    
    guild_id = interaction.guild.id

    #check if player exits
    if not is_player_active(user.id, guild_id):
        await interaction.response.send_message(f"{user.display_name} has not joined the game!", ephemeral=True)
        return
    else:
        # Update the player's stat in the database
        update_player_field(user.id,guild_id, stat, number)
        await interaction.response.send_message(f"{user.display_name}'s {stat.replace('_', ' ')} has been updated to {number}.", ephemeral=True)


@set_group.command(name="state", description="Enable or disable the game.")
@app_commands.describe(
    state="Enable or disable the game."
)
@app_commands.choices(state=[
    app_commands.Choice(name="Enable", value="enable"),
    app_commands.Choice(name="Disable", value="disable")
])
@checks.check_if_has_permission_or_role()
async def set_game_state( interaction: discord.Interaction, state: app_commands.Choice[str]):
    import admin_settings as shared
    shared.set_state(interaction.guild_id,state.value == 'enable')
    await interaction.response.send_message(shared.summary(interaction.guild_id),ephemeral=True)


@set_group.command(name="slowmode", description="Set separate player cooldowns in seconds; 0 disables. Omit values to view.")
@checks.check_if_has_permission_or_role()
@app_commands.guild_only()
@app_commands.describe(trick="Seconds between tricks (0 = off)",treat="Seconds between treats (0 = off)",smash="Seconds between pumpkin smashes (0 = off)")
async def set_slowmode(interaction: discord.Interaction,
                       trick: app_commands.Range[int,0,86400] = None,
                       treat: app_commands.Range[int,0,86400] = None,
                       smash: app_commands.Range[int,0,86400] = None):
    import slowmode
    updates={k:v for k,v in dict(trick=trick,treat=treat,smash=smash).items() if v is not None}
    values=slowmode.configure(interaction.guild_id,**updates) if updates else slowmode.settings(interaction.guild_id)
    shown={k:slowmode.text('off') if v==0 else slowmode.text('seconds',amount=v) for k,v in values.items()}
    await interaction.response.send_message(slowmode.text('settings',**shown),ephemeral=True)


@set_group.command(name='auto_cauldron',description='Configure automatic cauldron spells; disabled by default')
@checks.check_if_has_permission_or_role()
@app_commands.guild_only()
@app_commands.choices(trigger=[app_commands.Choice(name=x.title(),value=x) for x in ('interval','threshold','either')],
                      witch=[app_commands.Choice(name=x.title(),value=x) for x in ('luna','raven','random')],
                      winners=[app_commands.Choice(name=x.title(),value=x) for x in ('one','many','random')])
async def set_auto_cauldron(interaction:discord.Interaction,enabled:bool=None,trigger:str=None,
                           interval_minutes:app_commands.Range[int,1,2147483647]=None,
                           candy_threshold:app_commands.Range[int,1,2147483647]=None,
                           witch:str=None,winners:str=None,
                           minimum_gap_minutes:app_commands.Range[int,1,2147483647]=None):
    import auto_cauldron
    try:
        auto_cauldron.configure(interaction.guild_id,guild=interaction.guild,enabled=enabled,trigger=trigger,
                               interval_minutes=interval_minutes,candy_threshold=candy_threshold,
                               witch=witch,winners=winners,minimum_gap_minutes=minimum_gap_minutes)
    except ValueError as error:
        await interaction.response.send_message(str(error),ephemeral=True)
        return
    await interaction.response.send_message(auto_cauldron.describe(interaction.guild_id,interaction.guild),ephemeral=True)
