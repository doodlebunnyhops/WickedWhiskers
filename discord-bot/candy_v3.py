# -----------------------------------------------------------------------------
# Author: doodlebunnyhops
# Date: 10-07-2024
# Description: Discord Bot command logic, bot that plays trick or treat, lottery, and gambling.
# License: This file is part of a project licensed under the MIT License.
# Attribution: If you reuse or modify this code, please attribute the original
# creator, doodlebunnyhops, by referencing the source repository at 
# https://github.com/doodlebunnyhops.
# -----------------------------------------------------------------------------

import discord
from discord import app_commands
from discord.ext import commands
import random
import db_utils
import utils


# Intents to read messages from users in the server
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Remove the default help command immediately after bot instantiation
bot.remove_command('help')

# # Initialize the database when the bot starts
db_utils.initialize_database()

conn = db_utils.get_db_connection()
cursor = conn.cursor()


# Command to get all roles assigned for restricted commands in the current guild
@bot.tree.command(name="get_role_access", description="Get all roles assigned for restricted commands")
@utils.requires_permission_or_role()
async def get_role_access(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    # Query the database for all roles assigned to restricted commands in the current guild
    cursor.execute("SELECT role_id FROM role_access WHERE guild_id = ?", (guild_id,))
    role_ids = [row[0] for row in cursor.fetchall()]

    if not role_ids:
        await interaction.response.send_message("No roles have been assigned access to restricted commands.", ephemeral=True)
        return

    # Get the role names from the guild and format them
    roles = [interaction.guild.get_role(role_id) for role_id in role_ids]
    valid_roles = [role.name for role in roles if role is not None]  # Filter out any roles that might have been deleted

    if not valid_roles:
        await interaction.response.send_message("None of the assigned roles exist in this guild anymore.", ephemeral=True)
        return

    role_names = ", ".join(valid_roles)
    await interaction.response.send_message(f"The following roles have access to restricted commands: {role_names}")

# Command to set role access for restricted commands (single role input)
@bot.tree.command(name="set_role_access", description="Set moderator command access for a role.")
@app_commands.checks.has_permissions(manage_guild=True)  # Ensure only users with Manage Guild can use this
async def set_role_access(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild.id

    # Validate that the role belongs to the current guild
    if role.guild.id != guild_id:
        await interaction.response.send_message(f"The role {role.name} is not valid in this guild.", ephemeral=True)
        return

    # Insert or replace the role access for the valid role
    cursor.execute("REPLACE INTO role_access (guild_id, role_id) VALUES (?, ?)", (guild_id, role.id))
    conn.commit()

    # Create a response message showing the added role
    await interaction.response.send_message(f"Role {role.name} can now access the restricted commands.")

# Slash Command to allow new players to join the candy game
@bot.tree.command(name="join", description="Join the candy game and start collecting candy.")
async def join_game(interaction: discord.Interaction):
    player_id = interaction.user.id
    guild_id = interaction.guild.id

    # Check if the player is already in the game
    cursor.execute('SELECT * FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    result = cursor.fetchone()

    if result:
        await interaction.response.send_message(f"{interaction.user.mention}, you are already in the game! Use /optin if you previously opted out.", ephemeral=True)
    else:
        # Insert the new player into the database with default values (50 candy and 0 tickets purchased)
        cursor.execute('INSERT INTO players (player_id, guild_id, candy_count, successful_steals, failed_steals, candy_given, active, tickets_purchased, frozen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                       (player_id, guild_id, 50, 0, 0, 0, 1, 0, 0))
        conn.commit()

        await interaction.response.send_message(f"Welcome {interaction.user.mention}! You have started with 50 candy. Will you trick or treat others :thinking:?", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload):
    # Ensure the event is from a guild
    if payload.guild_id is None:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    channel = bot.get_channel(payload.channel_id)
    
    # Define the emoji that will trigger joining the game
    join_emoji = '🎃'

    # Fetch the game invite message ID from the database for the current guild
    cursor.execute('SELECT game_invite_message_id FROM guild_settings WHERE guild_id = ?', (payload.guild_id,))
    result = cursor.fetchone()

    if result is None:
        return  # No invite message ID found, do nothing

    game_invite_message_id = result[0]  # Get the invite message ID

    # Check if the reaction is on the correct invite message and is the right emoji
    if payload.message_id == game_invite_message_id and str(payload.emoji) == join_emoji:
        player_id = member.id
        guild_id = guild.id

        # Check if the player is already in the game
        cursor.execute('SELECT * FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
        result = cursor.fetchone()

        if result:
            # Player is already in the game
            await channel.send(f"{member.mention}, you are already in the game! Use /return if you previously opted out.", delete_after=20)
        else:
            # Insert the new player into the database
            cursor.execute('INSERT INTO players (player_id, guild_id, candy_count, successful_steals, failed_steals, candy_given, active, tickets_purchased, frozen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                           (player_id, guild_id, 50, 0, 0, 0, 1, 0, 0))
            conn.commit()

            # Welcome the new player
            await channel.send(f"Welcome {member.mention}! You have joined the candy game with 50 candy. Get ready to trick or treat! 🎃", delete_after=10)

# Slash command to post message players react to join the game.
@bot.tree.command(name="game_invite", description="Creates a message inviting players to join the game by reacting with a 🎃.")
@utils.requires_permission_or_role()
async def game_invite(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    # Check if an invite message already exists for the guild
    cursor.execute('SELECT game_invite_message_id FROM guild_settings WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()

    if result and result[0] is not None:
        existing_message_id = result[0]
        # Check if the message still exists in the channel
        try:
            channel = interaction.channel
            existing_message = await channel.fetch_message(existing_message_id)
            # If the message exists, notify the moderator
            await interaction.response.send_message(
                f"An invite message already exists! Players can react to it to join. Here is the message: {existing_message.jump_url}",
                ephemeral=True
            )
            return
        except discord.NotFound:
            # If the message no longer exists, proceed to create a new one
            await interaction.response.send_message("Previous invite message not found, creating a new invite...", ephemeral=True)
        except discord.Forbidden:
            # The bot does not have permission to access the message
            await interaction.response.send_message("I do not have permission to access the previous invite message. Creating a new invite...", ephemeral=True)
        except discord.HTTPException:
            # A general HTTP error occurred
            await interaction.response.send_message("An error occurred while fetching the previous invite message. Creating a new invite...", ephemeral=True)
        except Exception as e:
            # Catch-all for any other exceptions
             await interaction.response.send_message(f"An unexpected error occurred: {str(e)}. Creating a new invite...", ephemeral=True)

    # Post the new invite message
    invite_message = await interaction.channel.send("React with 🎃 to join the candy game and start your trick-or-treat adventure!")
    game_invite_message_id = invite_message.id  # Get the new message ID

    # Save the new message ID to the guild_settings table without overwriting other columns
    cursor.execute('UPDATE guild_settings SET game_invite_message_id = ? WHERE guild_id = ?', 
                   (game_invite_message_id, guild_id))

    # If no rows were affected by the UPDATE, insert a new row
    if cursor.rowcount == 0:
        cursor.execute('INSERT INTO guild_settings (guild_id, game_invite_message_id) VALUES (?, ?)', 
                       (guild_id, game_invite_message_id))
    
    conn.commit()

    await interaction.response.send_message(f"Invite message sent! Players can now react to join.", ephemeral=True)


# Slash Command to freeze a player (make them inactive)
@bot.tree.command(name="freeze", description="Freeze a player, making them inactive in the game. Restricted to mods.")
@app_commands.describe(user="The user to freeze")
@utils.requires_permission_or_role()
async def freeze_player(interaction: discord.Interaction, user: discord.Member):
    guild_id = interaction.guild.id
    player_id = user.id

    # Set the player as frozen in the database
    cursor.execute('UPDATE players SET frozen = 1, active = 0 WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    conn.commit()

    await interaction.response.send_message(f"{user.mention} has been frozen and can no longer participate in the game.", ephemeral=True)

# Slash Command to unfreeze a player (make them active again)
@bot.tree.command(name="unfreeze", description="Unfreeze a player, allowing them to participate in the game again. Restricted to mods.")
@app_commands.describe(user="The user to unfreeze")
@utils.requires_permission_or_role()
async def unfreeze_player(interaction: discord.Interaction, user: discord.Member):
    guild_id = interaction.guild.id
    player_id = user.id

    # Set the player as unfrozen and active in the database
    cursor.execute('UPDATE players SET frozen = 0, active = 1 WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    conn.commit()

    await interaction.response.send_message(f"{user.mention} has been unfrozen and can now participate in the game again.", ephemeral=True)

# Slash Command to allow players to opt-out of the game (guild-specific)
@bot.tree.command(name="escape", description="Opt out of the active game. Your progress will be saved for when you /return.")
async def opt_out_game(interaction: discord.Interaction):
    player_id = interaction.user.id
    guild_id = interaction.guild.id  # Get the guild ID

    if db_utils.is_player_frozen(player_id,guild_id):
        await interaction.response.send_message(f"I'm sorry , {interaction.user.mention}! Your game has been frozen by TheAgency :(. You'll have to approach them with caution to see if they'll unfreeze you... you cannot even escape it", ephemeral=True)
        return

    # Check if the player exists in the current guild
    cursor.execute('SELECT * FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    result = cursor.fetchone()

    if result:
        db_utils.set_player_inactive(player_id, guild_id)  # Make sure this function updates by guild
        await interaction.response.send_message(f"{interaction.user.mention}, you've chosen to leave the candy madness :( . The Halloween fun will miss you!", ephemeral=True)
    else:
        await interaction.response.send_message(f"{interaction.user.mention}, you are not currently in the game. Please use /join to start trick or treating :D.", ephemeral=True)

# Slash Command to allow players to opt back into the game (guild-specific)
@bot.tree.command(name="return", description="Rejoin the game and resume your progress.")
async def opt_in_game(interaction: discord.Interaction):
    player_id = interaction.user.id
    guild_id = interaction.guild.id  # Get the guild ID

    if db_utils.is_player_frozen(player_id,guild_id):
        await interaction.response.send_message(f"I'm sorry , {interaction.user.mention}! Your game has been frozen by TheAgency :(. You'll have to approach them with caution to see if they'll unfreeze you.", ephemeral=True)
        return

    # Check if the player is inactive in the current guild
    cursor.execute('SELECT active FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    result = cursor.fetchone()

    if result and result[0] == 0:
        db_utils.set_player_active(player_id, guild_id)  # Make sure this function updates by guild
        await interaction.response.send_message(f"Welcome back, {interaction.user.mention}! The candy-filled adventure awaits. Get ready for more spooky tricks and sweet treats!", ephemeral=True)
    elif result:
        await interaction.response.send_message(f"{interaction.user.mention}, you are already in the game silly, are you trying to trick me hehe.", ephemeral=True)
    else:
        await interaction.response.send_message(f"{interaction.user.mention}, please use /join to start trick or treating :D.", ephemeral=True)

# Slash Command for Help - Shows a list of available commands and extra ones for mods/admins
@bot.tree.command(name="help", description="Get a list of available commands and how to use them.")
async def help_command(interaction: discord.Interaction):
    help_message = f"Go to our readme [here](https://github.com/doodlebunnyhops/candy/blob/main/README.md)"

    await interaction.response.send_message(help_message,ephemeral= True)  # Send the first chunk

# Slash Command to show information about the bot
@bot.tree.command(name="about", description="Learn more about me!")
async def about_me(interaction: discord.Interaction):
    message = (
        "Boo! I'm here to spread spooky fun, and BloominDaisy made sure I'm filled with tricks and treats! 🎃\n\n"
        "In this candy-filled adventure, you can steal candy from others, give treats to your friends, and even join the candy lottery!\n"
        "Try your luck with these commands: `/trick` to try to nab candy, `/give_treat` to treat a friend, and `/buy_potion` to win big in the cauldron event!\n\n"
        "More haunted surprises are on the way, so keep your eyes peeled! Got any ghostly feedback or need help? Contact BloominDaisy if you dare! 👻"
    )
    await interaction.response.send_message(message, ephemeral=True)


# Slash Command to display the event, admin, and game invite channels set for the current guild
@bot.tree.command(name="spooky_channels", description="Show the event, admin, and game invite channels set for the server. Restricted to specific roles.")
@commands.cooldown(1, 600, commands.BucketType.guild)  # 10min cooldown per user
@utils.requires_permission_or_role()
async def show_channels(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    # Query the event, admin, and game invite message IDs from the database
    cursor.execute('SELECT event_channel_id, admin_channel_id, game_invite_message_id FROM guild_settings WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()

    if result:
        event_channel_id, admin_channel_id, game_invite_message_id = result
        event_channel = interaction.guild.get_channel(event_channel_id) if event_channel_id else None
        admin_channel = interaction.guild.get_channel(admin_channel_id) if admin_channel_id else None

        # Fetch the game invite message channel, if game_invite_message_id is set
        invite_channel = None
        await interaction.response.send_message("Looking for channel details...", delete_after=20, ephemeral= True)
        if game_invite_message_id:
            # Loop through all text channels to find where the message was posted
            for channel in interaction.guild.text_channels:
                try:
                    # Fetch the message and determine the channel
                    message = await channel.fetch_message(game_invite_message_id)
                    invite_channel = message.channel
                    break
                except discord.NotFound:
                    continue
                except discord.Forbidden:
                    # The bot does not have permission to access the message
                    # await interaction.followup.send("I do not have permission to access the previous invite message.", ephemeral=True)
                    continue
                except discord.HTTPException:
                    # A general HTTP error occurred
                    # await interaction.followup.send("An error occurred while fetching the previous invite message.", ephemeral=True)
                    continue
                # except discord.
                except Exception as e:
                    # Catch-all for any other exceptions
                    # await interaction.followup.send(f"An unexpected error occurred: {str(e)}.", ephemeral=True)
                    continue

        # Build the response message
        response_message = "Here are the channels set for this server:\n"
        response_message += f"**Event Channel:** {event_channel.mention if event_channel else 'Not Set'}\n"
        response_message += f"**Admin Channel:** {admin_channel.mention if admin_channel else 'Not Set'}\n"
        response_message += f"**Game Invite Channel:** {invite_channel.mention if invite_channel else 'Not Set'}\n"
    else:
        response_message = "No event, admin, or game invite channels have been set for this server yet."

    await utils.post_admin_message(bot, guild_id, response_message,interaction)

# Slash Command to set the admin/mod command channel
@bot.tree.command(name="set_lair", description="Set the channel where role based/admin commands will reply. Restricted to specific roles.")
@utils.requires_permission_or_role()
async def set_admin_channel_command(interaction: discord.Interaction, channel: discord.TextChannel):
    
    db_utils.set_admin_channel(interaction.guild_id, channel.id)
    await interaction.response.send_message(f"The admin/mod command channel has been set to {channel.mention}.", ephemeral=True)


# Slash Command to set the event channel
@bot.tree.command(name="set_crypt", description="Set the channel where event messages will be posted.")
@utils.requires_permission_or_role()
async def set_event_channel_command(interaction: discord.Interaction, channel: discord.TextChannel):

    db_utils.set_event_channel(interaction.guild.id, channel.id)
    await interaction.response.send_message(f"The Event channel has been set to {channel.mention}.", ephemeral=True)

# Slash Command for moderators to add candy to a user's balance
@bot.tree.command(name="give_ghoul_candy", description="Add candy to a player's stash.")
@app_commands.describe(user="The user to add candy to", amount="The amount of candy to add")
@utils.requires_permission_or_role()
async def add_candy(interaction: discord.Interaction, user: discord.Member, amount: int):
    guild_id = interaction.guild.id

    if db_utils.is_player_active(user.id, guild_id) == False:
        await interaction.response.send_message(f"{user.name} has paused their game and isn't active right now.", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("The amount must be positive!", ephemeral=True)
        return
    if user.id == interaction.user.id:
        await interaction.response.send_message("What ya dooooin, hmm? Trying to give yourself some candy eh?", ephemeral=True)
        return


    player_data = db_utils.get_player_data(user.id, guild_id)
    db_utils.update_player_field(user.id, guild_id,'candy_count', player_data[0] + amount)

    # await interaction.response.send_message(f"{amount} candy has been added to {user.mention}'s balance. They now have {player_data[0] + amount} candy.", ephemeral=True)
    await utils.post_admin_message(bot, guild_id, f"{amount} candy was added to {user.name}'s balance by {interaction.user.name}.",interaction)
    await utils.post_event_message(bot, guild_id, f"{amount} candy was added to {user.mention}'s balance by The Agency.",interaction)

# Slash Command for moderators to remove candy from a player's balance
@bot.tree.command(name="remove_ghoul_candy", description="Remove candy from a player's stash.")
@app_commands.describe(user="The user to remove candy from", amount="The amount of candy to remove")
@utils.requires_permission_or_role()
@utils.requires_active_player(check_target=True, param_name="user")
@utils.positive_number()
async def remove_candy(interaction: discord.Interaction, user: discord.Member, amount: int):
    guild_id = interaction.guild.id
    player_data = db_utils.get_player_data(user.id,guild_id)
    new_candy_count = max(0, player_data[0] - amount)  # Ensure balance doesn't go negative
    db_utils.update_player_field(user.id, guild_id, 'candy_count', new_candy_count)

    await interaction.response.send_message(f"{amount} candy has been removed from {user.name}. They now have {new_candy_count} candy.", ephemeral=True)
    await utils.post_event_message(bot, guild_id, f"{amount} candy was removed from {user.mention}'s balance by The Agency.")

# Slash Command to check a player's stats and whether they are active
@bot.tree.command(name="stats", description="Check a player's candy and stats.")
@app_commands.describe(user="The user whose stats you want to check. None Moderators can only check their own stats.")
@utils.requires_active_player(check_initiator=True, check_target=True, param_name="user")
@utils.requires_self_or_permission(param_name="user")  # Allow self-check, enforce permission for others
async def check_stats(interaction: discord.Interaction, user: discord.Member):
    caller = interaction.user
    guild_id = interaction.guild.id

    # If no user is provided, assume the caller wants to check their own stats
    if user is None:
        user = caller

    # Retrieve player data
    player_data = db_utils.get_player_data(user.id, guild_id)
    if player_data:
        # Display player stats
        candy_count, successful_steals, failed_steals, candy_given, tickets_purchased = player_data[:5]
        is_active = db_utils.is_player_active(user.id, guild_id)
        active_status = "Active" if is_active else "Inactive"

        await interaction.response.send_message(
            f"{user.name} has {candy_count} candy.\n"
            f"Potions In Stock: {tickets_purchased}\n"
            f"Successful steals: {successful_steals}\n"
            f"Failed steals: {failed_steals}\n"
            f"Candy given: {candy_given}\n"
            f"Status: {active_status}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(f"{user.name} has not joined the game yet.", ephemeral=True)

# RETHINK THIS
# Slash Command to check total candy for a role...this might be rather intense because it can call db_utils.get_player_data which creates new players...
# @bot.tree.command(name="candystash_by_role", description="Check the total candy for all users in a specific role. Restricted to specific roles.")
# @app_commands.describe(role="The role to check total candy for")
# async def role_candy(interaction: discord.Interaction, role: discord.Role):
#     guild_id = interaction.guild.id
#     if db_utils.has_role_or_permission(interaction.user,guild_id) == False:
#         await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
#         return
    
#     total_candy = 0
#     for member in role.members:
#         player_data = db_utils.get_player_data(member.id,guild_id)
#         total_candy += player_data[0] if player_data else 0

#     await interaction.response.send_message(f"The total amount of candy for the {role.name} role is {total_candy}.", ephemeral=True)


# Slash Command to give candy to another user
@bot.tree.command(name="give_treat", description="Give candy to another player.")
@app_commands.describe(user="The user to give candy to", amount="The amount of candy to give")
@utils.requires_active_player(check_initiator=True,check_target=True,param_name="user")
@utils.cannot_target_self(param_name="user")
@utils.positive_number(param_name="amount")
async def give(interaction: discord.Interaction, user: discord.Member, amount: int, **kwargs):
    guild_id = interaction.guild.id
    giver_id = interaction.user.id
    recipient_id = user.id

    giver_data = kwargs.get("_player_data_initiator")
    recipient_data = kwargs.get("_player_data_target")

    # Ensure the giver has enough candy
    if giver_data[0] < amount:
        await interaction.response.send_message(f"You do not have enough candy! You currently have {giver_data[0]} candy.", ephemeral=True)
        return
    
    # Gifting tier responses
    if amount == 0:
        message = f"{interaction.user.mention} what are you trying to pull?! {user.mention} was gifted an empty candy wrapper :cry: getting {amount} candy..."
        personal_message = f"thanks for giving {user.name} {amount} candy :heart:"
    elif amount == 1:
        message = f"{interaction.user.mention} didn't give much but it was the action that counts! {user.mention} eagerly munched on their {amount} candy..."
        personal_message = f"thanks for giving {user.name} {amount} candy :heart:"
    elif amount <= 3:
        message = f"{interaction.user.mention} is feeling sweet, giving {amount} candy to {user.mention}. A nice little haul!"
        personal_message = f"awe so sweet, thanks for giving {user.name} {amount} candy :wink:"
    elif amount <= 6:
        message = f"{interaction.user.mention} treated {user.mention} to {amount} pieces of candy! Sharing the sweetness of Halloween!"
        personal_message = f"That's the spirit! :eyes: wait where's the ghost?? Oh hehe I'm the ghost :P, thanks for giving {user.name} {amount} candy"
    elif amount <= 9:
        message = f"{interaction.user.mention} is feeling really kind :smile: giving {amount}, what will you do with that candy {user.mention}?"
        personal_message = f":stars: Look at you being a kind ghoul giver! Thanks for giving {user.name} {amount} candy"
    else:
        message = f"{interaction.user.mention} handed over a generous pile of {amount} candy to {user.mention}. Trick-or-treat spirit at its finest!"
        personal_message = f"o.O I have declared you the best of best spirits! Thanks for giving {user.name} {amount} candy"


    # Perform the candy transfer
    db_utils.update_player_field(giver_id, guild_id, 'candy_count', giver_data[0] - amount)
    db_utils.update_player_field(recipient_id, guild_id, 'candy_count', recipient_data[0] + amount)
    db_utils.update_player_field(giver_id, guild_id, 'candy_given', giver_data[3] + amount)

    await interaction.response.send_message(personal_message,ephemeral= True)
    await utils.post_event_message(bot, guild_id, message,interaction)

# Slash Command to attempt stealing candy from another user
@bot.tree.command(name="trick", description="Attempt to steal candy from another player by tricks!")
@app_commands.describe(target="The user you want to steal from")
@commands.cooldown(1, 60, commands.BucketType.user)  # 60 second cooldown per user
async def steal(interaction: discord.Interaction, target: discord.Member):
    thief_id = interaction.user.id
    target_id = target.id
    guild_id = interaction.guild.id

    await interaction.response.send_message(f"{interaction.user.name}, lets see how your trick plays out...", ephemeral=True,delete_after=20)
        
    if thief_id == target_id:
        await utils.post_event_message(bot, guild_id, f"You cannot steal from yourself {interaction.user.mention}, lol silly goober!",interaction)
        return

    if db_utils.is_player_active(thief_id, guild_id) == False:
        await interaction.followup.send(f"{interaction.user.name}, either you haven't /joined yet or you have opted out to play. You can re-activate gameplay with /return_haunt.", ephemeral=True)
        return

    if db_utils.is_player_active(target_id, guild_id) == False:
        await interaction.followup.send(f"{target.name} is inactive right now which means they cannot receive treats.", ephemeral=True)
        return
    
    thief_data = db_utils.get_player_data(thief_id, interaction.guild.id)
    target_data = db_utils.get_player_data(target_id, interaction.guild.id)

    #Scenarios where target has no candy to have stolen
    if target_data[0] == 0:
        # Target has no candy, special handling
        if thief_data[0] > 5 and random.random() < 0.05:  # 5% chance thief feels bad and gives some candy
            given_candy = random.randint(1, min(5, thief_data[0] - 5))  # Give between 1 and 5 candy
            db_utils.update_player_field(thief_id, guild_id, 'candy_count', thief_data[0] - given_candy)
            db_utils.update_player_field(target_id, guild_id, 'candy_count', target_data[0] + given_candy)
            message = f"{interaction.user.mention} felt so bad for {target.mention}'s empty stash that they gave {given_candy} candy out of sympathy!"
        elif random.random() < 0.03:  # 3% chance of ghastly duel and candy vanishes into the lottery
            duel_candy = random.randint(50, 1000)
            db_utils.update_lottery_pool(guild_id, duel_candy)
            message = f"{interaction.user.mention} and {target.mention} got into a ghastly duel over candy, but magically {duel_candy} candy appeared and vanished into the cauldron!"
        else:
            # No candy exchange, the target laughs at the thief
            message = f"{interaction.user.mention} tried to steal from {target.mention}, but {target.mention} laughed in their face because they have no candy!"
        await utils.post_event_message(bot, guild_id, message,interaction)
        return

    # Determine the success rate
    success_rate = 0.5  # Default success rate is 50%
    if thief_data[0] == 0:
        success_rate = 0.2  # Lower success rate if thief has no candy

    if random.random() < success_rate:
        # Successful steal
        stolen_amount = min(random.randint(1, 10), target_data[0])
        db_utils.update_player_field(thief_id, guild_id, 'candy_count', thief_data[0] + stolen_amount)
        db_utils.update_player_field(target_id, guild_id, 'candy_count', target_data[0] - stolen_amount)
        db_utils.update_player_field(thief_id, guild_id, 'successful_steals', thief_data[1] + 1)

        # Extra probability checks for successful steal
        if random.random() < 0.01:  # 1% chance of trick
            # Trick: both lose the candy, and it's added to the lottery
            db_utils.update_player_field(thief_id, guild_id, 'candy_count', max(0, thief_data[0] - stolen_amount))
            db_utils.update_player_field(target_id, guild_id, 'candy_count', max(0, target_data[0] - stolen_amount))
            # Add the lost candy to a lottery
            lottery_pool = stolen_amount * 2  # both lose the candy
            # Add the candy to the lottery pool
            db_utils.update_lottery_pool(interaction.guild.id, lottery_pool)

            message = f"{interaction.user.mention} was tricked by {target.mention}! Both lost {stolen_amount} candy, and it has been added to the lottery."
        elif random.random() < 0.03 and stolen_amount > 5:  # 3% chance target gets 1 candy back if more than 5 stolen
            db_utils.update_player_field(target_id, guild_id, 'candy_count', target_data[0] + 1)  # Target gets 1 candy back
            message = f"{interaction.user.mention} stole {stolen_amount} candy from {target.mention}, but {target.mention} got 1 candy back!"
        else:
            # Regular success
            if stolen_amount == 0:
                message = f"{interaction.user.mention}... tried to trick {target.mention} by hiding in a bush. The bush didn't hide {interaction.user.name} at all and {target.name} laughed. No candy was taken! "
            elif stolen_amount == 1:
                message = f"{interaction.user.mention} crept in the shadows and snatched 1 candy from {target.mention}! Every piece helps build your candy stash!"
            elif stolen_amount <= 3:
                message = f"{interaction.user.mention} quietly nabbed {stolen_amount} candy from {target.mention}. A nice little haul!"
            elif stolen_amount <= 6:
                message = f"Quick and nimble! {interaction.user.mention} just made off with {stolen_amount} candy from {target.mention}."
            elif stolen_amount <= 9:
                message = f"{interaction.user.mention} pulled off a perfect trick, swiping {stolen_amount} candy from {target.mention}! They never saw it coming!"
            else:
                message = f"{interaction.user.mention} hit the ultimate jackpot, tricking {target.mention} out of {stolen_amount} candy! What a spooky success!"

        await utils.post_event_message(bot, interaction.guild.id, message,interaction)
    else:
        # Failed steal
        penalty = random.randint(0, 5)
        db_utils.update_player_field(thief_id, guild_id, 'candy_count', max(0, thief_data[0] - penalty))
        db_utils.update_player_field(thief_id, guild_id,'failed_steals', thief_data[2] + 1)
        db_utils.update_player_field(target_id, guild_id, 'candy_count', target_data[0] + penalty)

        # Extra probability checks for failed steal
        if random.random() < 0.01:  # 1% chance both fumble and lose candy, added to the lottery
            db_utils.update_player_field(thief_id, guild_id, 'candy_count', max(0, thief_data[0] - penalty))
            db_utils.update_player_field(target_id, guild_id, 'candy_count', max(0, target_data[0] - penalty))
            lottery_pool = penalty * 2  # both lose the candy
            db_utils.update_lottery_pool(interaction.guild.id, lottery_pool)
            message = f"{interaction.user.mention} tried to steal from {target.mention}, but both fumbled and lost {penalty} candy, added to the lottery."
        elif random.random() < 0.03:  # 3% chance thief tries again and gets half candy
            stolen_again = max(1, stolen_amount // 2)  # Half the candy, rounded up
            db_utils.update_player_field(thief_id, guild_id, 'candy_count', thief_data[0] + stolen_again)
            db_utils.update_player_field(target_id, guild_id, 'candy_count', target_data[0] - stolen_again)
            message = f"{interaction.user.mention} initially failed, but managed to steal {stolen_again} candy from {target.mention} on a second attempt!"
        else:
            # Regular failure
            if penalty == 0:
                message = f"{interaction.user.mention} tried to steal but failed! Fortunately, {target.mention} didn't take any candy."
            elif penalty <= 2:
                message = f"Ouch! {interaction.user.mention} failed to grab candy, and {target.mention} swiped {penalty} candy from you. Not too bad!"
            elif penalty == 5:
                message = f"{interaction.user.mention} botched the steal! {target.mention} cleaned you out for {penalty} candy. Better luck next time!"
            else:
                message = f"{interaction.user.mention} failed miserably and {target.mention} got {penalty} candy from your misfortune!"

        await utils.post_event_message(bot, interaction.guild.id, message,interaction)


# Slash Command to check player's balance of candy
@bot.tree.command(name="candy_stash", description="Check how much candy you have.")
async def balance(interaction: discord.Interaction):
    player_id = interaction.user.id
    player_data = db_utils.get_player_data(player_id, interaction.user.guild.id)

    if player_data:
        await interaction.response.send_message(f"{interaction.user.mention}, you currently have {player_data[0]} candy!", ephemeral=True)
    else:
        await interaction.response.send_message(f"{interaction.user.mention}, you haven't joined the fun yet!", ephemeral=True)


# Slash Command to check the leaderboard of top players who are active
@bot.tree.command(name="top_ghouls", description="See the top players with the most candy. Restricted to specific roles.")
@utils.requires_permission_or_role()
@utils.positive_number(param_name="amount")
async def leaderboard(interaction: discord.Interaction, amount: int):
    guild_id = interaction.guild.id

    # Fetch the top players from the database using the db_utils function
    top_players = db_utils.get_top_active_players(guild_id,amount)

    if not top_players:
        await interaction.response.send_message("No active players in the leaderboard yet.", ephemeral=True)
        return

    # Construct the leaderboard message
    leaderboard_message = f"**Top {amount} Ghouls (Active Players Only):**\n"
    for rank, (player_id, candy_count) in enumerate(top_players, start=1):
        member = interaction.guild.get_member(player_id)
        if member:
            leaderboard_message += f"{rank}. {member.mention} - {candy_count} candy\n"

    # Use the post_event_message function to send the leaderboard
    await utils.post_event_message(bot, guild_id, leaderboard_message, interaction)

    # Let the user know the message was posted
    await interaction.response.send_message("The leaderboard has been posted!", ephemeral=True)



# Slash Command to allow mods to reset a player's stats by guild
@bot.tree.command(name="delete_ghoul", description="Delete a player from the game.")
@app_commands.describe(user="The user to delete")
@utils.requires_permission_or_role()
async def reset_player(interaction: discord.Interaction, user: discord.Member):
    guild_id = interaction.guild.id
    player_id = user.id
    db_utils.delete_player_data(player_id,guild_id)

    await interaction.response.send_message(f"{user.name}'s stats and candy have been deleted for this server.", ephemeral=True)
    await utils.post_admin_message(bot,guild_id,f"{user.name}'s stats and candy have been deleted for this server by {interaction.user.name}. This means the player will have to /join to come back!",interaction)

# Slash Command to allow mods to reset a player's stats by guild
@bot.tree.command(name="reset_ghoul", description="Reset a player's candy and stats to 0 and 50 candy pieces.")
@app_commands.describe(user="The user to reset")
@utils.requires_permission_or_role()
async def reset_player(interaction: discord.Interaction, user: discord.Member):
    guild_id = interaction.guild.id
    db_utils.reset_player_data(user.id,guild_id)

    await interaction.response.send_message(f"{user.name}'s stats and candy have been reset for this server.", ephemeral=True)
    await utils.post_admin_message(bot,guild_id,f"{user.name}'s stats and candy have been reset for this server by {interaction.user.name}",interaction)

# Slash Command for gambling candy
@bot.tree.command(name="risk_treats", description="Gamble some of your candy.")
@app_commands.describe(amount="The amount of candy you want to gamble")
@utils.requires_active_player(check_initiator=True)
@utils.positive_number()
async def gamble(interaction: discord.Interaction, amount: int):
    guild_id = interaction.guild.id
    player_id = interaction.user.id
    player_data = db_utils.get_player_data(player_id, guild_id)
    candy_count, successful_steals, failed_steals, candy_given = player_data[:4]

    # Ensure the player has enough candy to gamble
    if candy_count < amount:
        await interaction.response.send_message(f"You don't have enough candy to gamble! You only have {candy_count}.", ephemeral=True)
        return

    # Determine success rate based on candy and behavior
    base_success_rate = 0.5  # Start with 50% success rate

    # Adjust the success rate based on how much candy the player has
    if candy_count > 50:
        base_success_rate -= (candy_count / 200)  # More candy, lower chance (max reduction of 0.25 for 100+ candy)

    # Adjust for gifting and stealing behavior
    base_success_rate += (candy_given / 100)  # Gifts increase chances (each gift adds 0.01 to success rate)
    base_success_rate -= ((successful_steals + failed_steals) / 50)  # Stealing decreases chances (each steal reduces by 0.02)

    # Ensure the success rate is between 5% and 95%
    success_rate = min(max(base_success_rate, 0.05), 0.95)

    # Gambling result based on adjusted success rate
    if random.random() < success_rate:
        # Win case
        winnings = max(1, amount * 2)  # Ensure they win at least 1 candy

        # Break-even case (0 winnings or loss)
        if winnings == amount:
            await interaction.response.send_message(
                f"🎃 It's a tie, {interaction.user.mention}! The spirits couldn't decide... You neither won nor lost candy this time.", ephemeral=True
            )
            return

        db_utils.update_player_field(player_id, guild_id, 'candy_count', candy_count + winnings)

        # Halloween-themed win response based on the amount won
        if winnings == 1:
            win_message = f"🎃 {interaction.user.mention}, the spirits have gifted you a single, lonely candy. 🍬 Every little bit counts!"
        elif winnings < 10:
            win_message = f"🎃 Not a bad haul, {interaction.user.mention}! You won {winnings} candy. 🍬 Keep trick-or-treating!"
        elif winnings < 30:
            win_message = f"👻 Lucky night, {interaction.user.mention}! The spirits granted you {winnings} candy! 🍭"
        elif winnings < 50:
            win_message = f"🕸️ {interaction.user.mention}, the spirits smile on you tonight! You’ve earned {winnings} candy! 🎃"
        else:
            win_message = f"🕸️ Incredible luck, {interaction.user.mention}! You struck the jackpot and won {winnings} candy! The spirits are truly on your side tonight! 🎉"

        await interaction.response.send_message(win_message, ephemeral=True)
        await utils.post_event_message(bot, guild_id, f"{interaction.user.mention} won {winnings} candy from gambling!", interaction)

    else:
        # Lose case
        lost_candy = max(1, amount)  # Ensure they lose at least 1 candy
        db_utils.update_player_field(player_id, guild_id, 'candy_count', candy_count - lost_candy)

        # Add the lost amount to the lottery pool
        db_utils.update_lottery_pool(guild_id, lost_candy)

        # Halloween-themed lose response based on the amount lost
        if lost_candy == 1:
            lose_message = f"💀 Oh no, {interaction.user.mention}, you lost just 1 candy... A small price to pay to the Halloween spirits. 🎃"
        elif lost_candy < 10:
            lose_message = f"💀 The ghouls were sneaky, {interaction.user.mention}! You lost {lost_candy} candy to the shadows. 🎃"
        elif lost_candy < 30:
            lose_message = f"🕸️ A rough night, {interaction.user.mention}. You lost {lost_candy} candy to the dark forces. The cauldron grows stronger... 🍬"
        elif lost_candy < 50:
            lose_message = f"👻 A chilling loss, {interaction.user.mention}! {lost_candy} candy has vanished into the abyss, claimed by the spirits... 🕸️"
        else:
            lose_message = f"💀 A haunting misfortune, {interaction.user.mention}! The spirits have taken {lost_candy} candy, and it will fuel the cauldron's mysterious power... 🍬"

        await interaction.response.send_message(lose_message, ephemeral=True)
        await utils.post_event_message(bot, guild_id, f"{interaction.user.mention} lost {lost_candy} candy from gambling, now added to the lottery pool!", interaction)

# Slash Command for buying lottery tickets
@bot.tree.command(name="buy_potion", description="Buy a potion for 10 candy pieces each for the cauldron event.")
@app_commands.describe(amount="The number of potions you want to buy.")
async def buyticket(interaction: discord.Interaction, amount: int):
    player_id = interaction.user.id
    guild_id = interaction.guild.id
    player_data = db_utils.get_player_data(player_id, guild_id)

    ticket_cost = amount * 10  # 10 candy per ticket
    
    if db_utils.is_player_active(player_id, guild_id) == False:
        await interaction.response.send_message(f"{interaction.user.name}, either you haven't /joined yet or you have opted out to play. You can re-activate gameplay with /return_haunt.", ephemeral=True)
        return
    
    # Check if the player has enough candy
    if player_data[0] < ticket_cost:
        await interaction.response.send_message(f"You don't have enough candy to buy {amount} potions. You need {ticket_cost} candy.", ephemeral=True)
        return

    # Deduct the candy from the player's account
    db_utils.update_player_field(player_id, guild_id, 'candy_count', player_data[0] - ticket_cost)

    # Update the player's tickets purchased
    cursor.execute('SELECT tickets_purchased FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    current_tickets = cursor.fetchone()[0]
    new_ticket_count = current_tickets + amount
    cursor.execute('UPDATE players SET tickets_purchased = ? WHERE player_id = ? AND guild_id = ?', (new_ticket_count, player_id, guild_id))
    conn.commit()

    # Add the candy to the lottery pool
    db_utils.update_lottery_pool(guild_id, ticket_cost)

    await interaction.response.send_message(f"{interaction.user.mention}, you have bought {amount} potion(s)! The pot is now larger.", ephemeral=True)

# Slash Command to allow mods to check the lottery pool
@bot.tree.command(name="cauldron", description="Check how much candy is in the lottery cauldron. Restricted to specific roles.")
async def check_lottery_pool(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    # Check if the user has the necessary role or permission to reset player stats
    if db_utils.has_role_or_permission(interaction.user, guild_id) == False:
        await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
        return

    # Get the current lottery pool for the guild
    lottery_pool = db_utils.get_lottery_pool(guild_id)

    await interaction.response.send_message(f"The candy cauldron holds {lottery_pool} sweet pieces. Who will be the next lucky trickster to claim it?",ephemeral= False)


# Slash Command to draw a lottery winner or distribute to a random X number of players (for mods)
@bot.tree.command(name="cast_spell", description="Cast a spell to find the winner of the cauldron.")
@app_commands.describe(mode="Choose between 'single' or 'many' winners.")
@app_commands.describe(spirit="Choose 'fair' for higher chances based on tickets or 'evil' for something sinister.")
@app_commands.describe(num_winners="Specify the number of random winners for many mode")
async def drawlottery(interaction: discord.Interaction, mode: str, num_winners: int = 1, spirit: str = 'fair'):
    guild_id = interaction.guild.id

    # Check if the user has the necessary role or permission
    if not db_utils.has_role_or_permission(interaction.user, guild_id):
        await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
        return

    # Fetch eligible active players who have candy and their tickets purchased
    cursor.execute('SELECT player_id, tickets_purchased FROM players WHERE guild_id = ? AND active = 1', (guild_id,))
    eligible_players = cursor.fetchall()

    if not eligible_players:
        await interaction.response.send_message("There are no active players eligible for the lottery.", ephemeral=True)
        return

    # Get the current lottery pool
    lottery_pool = db_utils.get_lottery_pool(guild_id)

    if lottery_pool == 0:
        await interaction.response.send_message("There is no candy in the lottery pool.", ephemeral=True)
        return

    # Determine how winners will be chosen
    if spirit.lower() == 'fair':
        # Fair mode: Higher chances based on the number of tickets
        weighted_players = []
        for player_id, tickets in eligible_players:
            if tickets == 0:
                weighted_players.append((player_id, 1))  # At least 1 chance if they have no tickets
            else:
                weighted_players.extend([player_id] * tickets)  # More tickets means more chances

        eligible_players = weighted_players
    else:
        # Evil mode: All players have equal chance regardless of tickets
        eligible_players = [player_id for player_id, _ in eligible_players]

    num_players = len(set(eligible_players))

    if mode.lower() == "single":
        # Pick one random winner
        winner_id = random.choice(eligible_players)
        winner = interaction.guild.get_member(winner_id)

        if winner:
            # Add the entire pool to the winner's candy count
            cursor.execute('SELECT candy_count FROM players WHERE player_id = ? AND guild_id = ?', (winner_id, guild_id))
            winner_candy = cursor.fetchone()[0]
            new_candy_count = winner_candy + lottery_pool
            cursor.execute('UPDATE players SET candy_count = ? WHERE player_id = ? AND guild_id = ?', (new_candy_count, winner_id, guild_id))
            conn.commit()

            # Reset the lottery pool
            db_utils.reset_lottery_pool(guild_id)

            await interaction.response.send_message("Alright I've found a winner winner chicken dinner!", ephemeral=True)
            await utils.post_admin_message(bot, guild_id, f"{winner.name} has won the entire lottery pool of {lottery_pool} candy!",interaction)
            await utils.post_event_message(bot, guild_id, f"{winner.mention} has hit the candy motherload and won the spooky lottery! They’re swimming in sweets now!",interaction)
        else:
            await interaction.response.send_message("Lottery winner could not be found in the server.", ephemeral=True)

    elif mode.lower() == "many":
        # Ensure the number of winners doesn't exceed the number of eligible players
        if num_winners > num_players:
            await interaction.response.send_message(f"There are only {num_players} eligible players. Please choose a smaller number of winners.", ephemeral=True)
            return

        # Select random winners
        selected_winners = random.sample(eligible_players, num_winners)
        distributed_amount = lottery_pool // num_winners

        if distributed_amount == 0:
            await interaction.response.send_message(f"The lottery pool is too small to distribute among the chosen number of players.\nThere are {num_players} eligible players and you chose to distribute to {num_winners}.", ephemeral=True)
            return

        for player_id in selected_winners:
            cursor.execute('SELECT candy_count FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
            player_candy = cursor.fetchone()[0]
            new_candy_count = player_candy + distributed_amount
            cursor.execute('UPDATE players SET candy_count = ? WHERE player_id = ? AND guild_id = ?', (new_candy_count, player_id, guild_id))

        # Reset the lottery pool
        db_utils.reset_lottery_pool(guild_id)
        db_utils.reset_tickets_purchased(guild_id)

        winner_mentions = [interaction.guild.get_member(player_id).mention for player_id in selected_winners]
        winner_names = [interaction.guild.get_member(player_id).name for player_id in selected_winners]

        await interaction.response.send_message(f"Thanks! I've distributed the lottery candy :heart:", ephemeral=True)
        await utils.post_admin_message(bot, guild_id, f"The lottery pool of {lottery_pool} candy has been distributed among {num_winners} random players!\n Following Players received {distributed_amount} candy(s): {', '.join(winner_names)}",interaction)
        await utils.post_event_message(bot, guild_id,
            f"The Halloween spirits have smiled upon {num_winners} lucky players! Each received a share of the candy in the cauldron!\nCongrats to {', '.join(winner_mentions)}!",interaction)

    else:
        await interaction.response.send_message("Invalid mode. Please choose 'single' or 'distributed'.", ephemeral=True)



# Slash Command to allow mods to check the number of players in the game for the current guild
@bot.tree.command(name="ghoul_count", description="Check the total number of players and total of active players.")
async def check_player_count(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    # Check if the user has the necessary role or permission
    if not db_utils.has_role_or_permission(interaction.user, guild_id):
        await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
        return

    # Query the database to count the number of players in the current guild
    cursor.execute('SELECT COUNT(player_id) FROM players WHERE guild_id = ?', (guild_id,))
    player_count = cursor.fetchone()[0]
    
    # Query the database to count the number of players in the current guild
    cursor.execute('SELECT COUNT(player_id) FROM players WHERE guild_id = ? AND active = 1', (guild_id,))
    elegible_player_count = cursor.fetchone()[0]

    await interaction.response.send_message(f"There are a total of {player_count} spooky souls, out of those {elegible_player_count} are active and can trick or treat and participate in the cauldron event.\nBeware of the tricks!", ephemeral=True)


# Error handler responses
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    # Check if the error is due to the user missing the 'mod' role
    if isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    elif isinstance(error, commands.CommandOnCooldown):
        await interaction.response.send_message(f"This command is on cooldown. Try again in {round(error.retry_after, 1)} seconds.", ephemeral=True)
    elif isinstance(error, app_commands.MissingRequiredArgument):
        await interaction.response.send_message("Missing required arguments. Please provide all necessary information.", ephemeral=True)
    else:
        # For any other errors, you can handle them here or raise the default error
        await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)
        await utils.post_admin_message(bot, interaction.guild.id, f"An error occurred while processing:\n\tError: {error}.\n\tInvoked by: {interaction.user.name}\n\tAttempted: {interaction.command.name}")

# Delete Role used to verify db_utils.has_role_or_permission from DB if removed from guild.
@bot.event
async def on_guild_role_delete(role: discord.Role):
    guild_id = role.guild.id
    role_id = role.id

    # Remove the role from the role_access table if the role is deleted
    cursor.execute("DELETE FROM role_access WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
    conn.commit()

# Sync command tree to update the slash commands on the server
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync the commands to make sure they appear as slash commands
    print(f'Logged in as {bot.user}')

# Start the bot (replace 'YOUR_BOT_TOKEN' with your bot's token)
bot.run('YOUR_BOT_TOKEN')