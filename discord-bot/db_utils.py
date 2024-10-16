# -----------------------------------------------------------------------------
# Author: doodlebunnyhops
# Date: 10-07-2024
# Description: Database Utility to support Discord bot.
# License: This file is part of a project licensed under the MIT License.
# Attribution: If you reuse or modify this code, please attribute the original
# creator, doodlebunnyhops, by referencing the source repository at 
# https://github.com/doodlebunnyhops.
# -----------------------------------------------------------------------------
import sqlite3
import settings

logger = settings.logging.getLogger("bot")
# Persistent connection
conn = None

def get_db_connection():
    global conn
    if conn is None:
        conn = sqlite3.connect('candy_game.db')
    return conn

def close_db_connection():
    global conn
    if conn:
        conn.close()
        conn = None

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create table to store player data (per guild)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        player_id INTEGER,
        guild_id INTEGER,
        candy_count INTEGER DEFAULT 50,
        successful_steals INTEGER DEFAULT 0,
        failed_steals INTEGER DEFAULT 0,
        candy_given INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1,
        tickets_purchased INTEGER DEFAULT 0,
        frozen INTEGER DEFAULT 0,
        PRIMARY KEY (player_id, guild_id)
    )
    ''')

    # Create table for guild settings (for event/admin channel per guild)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            event_channel_id INTEGER DEFAULT NULL,
            admin_channel_id INTEGER DEFAULT NULL,
            game_invite_message_id INTEGER DEFAULT NULL,
            game_invite_channel_id INTEGER DEFAULT NULL  -- New column for the channel ID
        )
    ''')

    #Create table for for game settings (per guild)
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_settings (
                guild_id INTEGER PRIMARY KEY,
                game_disabled BOOLEAN DEFAULT TRUE,
                potion_price INTEGER DEFAULT 10,
                steal_success_rate INTEGER DEFAULT 100
            )
        ''')

    # Create table for lottery_pool (per guild)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lottery_pool (
        guild_id INTEGER PRIMARY KEY,
        candy_pool INTEGER DEFAULT 0
    )
    ''')

    # Create table for role restrictions (per guild)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS role_access (
        guild_id INTEGER,
        role_id INTEGER,
        PRIMARY KEY (guild_id, role_id)
    )
    ''')

    conn.commit()

# Close connection on shutdown
def shutdown():
    close_db_connection()

# Helper function to get guild settings from the database
def get_game_settings(guild_id):
    """
    Fetches all game settings for requested guild.
    
    Args: 
        guild_id (int): The unique identifier of the guild.
    
    Returns:
        tuple: A tuple containing the game settings for the guild with the following elements:
            - game_disabled (bool): The state of the game (True for disabled, False for enabled).
            - potion_price (int): The price of the potion in candies.
            - steal_success_rate (int): The success rate of stealing candies from other players.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT game_disabled, potion_price, steal_success_rate FROM game_settings WHERE guild_id = ?', (guild_id,))
    row = cursor.fetchone()
    if row:
        game_disabled, potion_price, steal_success_rate = row
    else:
        # Insert default values if guild is not in the table
        cursor.execute('INSERT INTO game_settings (guild_id) VALUES (?)', (guild_id,))
        conn.commit()
        game_disabled, potion_price, steal_success_rate = False, 10, 100
    return game_disabled, potion_price, steal_success_rate

# Helper function to update the game_disabled state in the database
def set_game_disabled( guild_id, disabled):
    """
    Update the game_disabled state in the database for the specified guild.
    
    Args:
        guild_id (int): The unique identifier of the guild.
        disabled (bool): The new state of the game (True for disabled, False for enabled).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE game_settings SET game_disabled = ? WHERE guild_id = ?', (disabled, guild_id))
    conn.commit()

def get_game_join_msg_settings(guild_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the message ID and channel ID
    cursor.execute('''
        SELECT game_invite_message_id, game_invite_channel_id
        FROM guild_settings
        WHERE guild_id = ?
    ''', (guild_id,))
    
    return cursor.fetchone()  # Returns (message_id, channel_id)

def set_game_join_msg_settings(guild_id: int, message_id: int, channel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # First, check if a row for this guild_id already exists
    cursor.execute('SELECT guild_id FROM guild_settings WHERE guild_id = ?', (guild_id,))
    exists = cursor.fetchone()

    if exists:
        # Update only the game_invite_message_id and game_invite_channel_id if the row exists
        cursor.execute('''
            UPDATE guild_settings
            SET game_invite_message_id = ?, game_invite_channel_id = ?
            WHERE guild_id = ?
        ''', (message_id, channel_id, guild_id))
    else:
        # Insert a new row if no row exists for this guild_id
        cursor.execute('''
            INSERT INTO guild_settings (guild_id, game_invite_message_id, game_invite_channel_id)
            VALUES (?, ?, ?)
        ''', (guild_id, message_id, channel_id))

    conn.commit()

# def set_game_join_msg_id(join_msg_id: int, guild_id: int):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     # Save the new message ID to the guild_settings table without overwriting other columns
#     cursor.execute('UPDATE guild_settings SET game_invite_message_id = ? WHERE guild_id = ?', (join_msg_id, guild_id))

#     # If no rows were affected by the UPDATE, insert a new row
#     if cursor.rowcount == 0:
#         cursor.execute('INSERT INTO guild_settings (guild_id, game_invite_message_id) VALUES (?, ?)', 
#                        (guild_id, join_msg_id))
    
#     conn.commit()

def fetch_roles_by_guild(guild_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role_id FROM role_access WHERE guild_id = ?", (guild_id,))
    role_ids = [row[0] for row in cursor.fetchall()]

    return role_ids

def set_role_by_guild(role_id: int, guild_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO role_access (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
    conn.commit()

def delete_role_by_guild(role_id: int, guild_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM role_access WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
    conn.commit()

# Get players with most candy that are in active status
def get_top_active_players(guild_id, limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    """
    Fetch the top active players based on candy count for a specific guild.
    :param guild_id: The ID of the guild
    :param limit: The number of top players to fetch (default is 10)
    :return: A list of tuples with player_id and candy_count
    """
    cursor.execute(
        'SELECT player_id, candy_count FROM players WHERE guild_id = ? AND active = 1 ORDER BY candy_count DESC LIMIT ?',
        (guild_id, limit)
    )
    return cursor.fetchall()

# Fetch all player data
def fetch_player_data(player_id, guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    result = cursor.fetchone()
    return result

# Function to get a player's candy count, stats, and tickets purchased
def get_player_data(player_id, guild_id):
    """
    Fetches a player's data from the database based on their player ID and guild ID.

    Args:
        player_id (int): The unique identifier of the player.
        guild_id (int): The unique identifier of the guild.

    Returns:
        dict: A dictionary containing the player's data with the following keys:
            - 'candy_count' (int): The number of candies the player has.
            - 'successful_steals' (int): The number of successful steals by the player.
            - 'failed_steals' (int): The number of failed steals by the player.
            - 'candy_given' (int): The amount of candy the player has given to others.
            - 'tickets_purchased' (int): The number of lottery tickets (potions) purchased by the player.
            - 'active' (int): The player's active status (1 for active, 0 for inactive).
        None: If no player data is found in the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT candy_count, successful_steals, failed_steals, candy_given, tickets_purchased, active FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    result = cursor.fetchone()

    if result:  # Check if player exists
        # Return a PlayerData dataclass instance
        player_data = {
            "candy_count": result[0],
            "successful_steals": result[1],
            "failed_steals": result[2],
            "candy_given": result[3],
            "tickets_purchased": result[4],
            "active": result[5]
        }
        return player_data
    return None

def create_player_data(player_id: int, guild_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO players (player_id, guild_id, candy_count, successful_steals, failed_steals, candy_given, active, tickets_purchased, frozen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                    (player_id, guild_id, 50, 0, 0, 0, 1, 0, 0))
    conn.commit()


# Delete a player's data.
def delete_player_data(player_id, guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    conn.commit()

# Reset a players data to default values.
def reset_player_data(player_id, guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE players
        SET candy_count = 50,      -- Reset candy count to 50
            successful_steals = 0,  -- Reset successful steals
            failed_steals = 0,      -- Reset failed steals
            candy_given = 0,        -- Reset candy given
            tickets_purchased = 0,  -- Reset lottery tickets purchased
            active = 1              -- Keep the player active after the reset
        WHERE player_id = ? AND guild_id = ?
    ''', (player_id, guild_id))
    conn.commit()

# Opt-out function to mark a player as inactive
def set_player_inactive(player_id, guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE players SET active = 0 WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    conn.commit()

# Opt-in function to mark a player as active
def set_player_active(player_id, guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE players SET active = 1 WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    conn.commit()

# Function to update player data by any field dynamically
def update_player_field(player_id, guild_id, field, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    logger.debug(f'UPDATE players SET {field} = {value} WHERE player_id = {player_id} AND guild_id = {guild_id}')
    cursor.execute(f'UPDATE players SET {field} = ? WHERE player_id = ? AND guild_id = ?', (value, player_id, guild_id))
    conn.commit()

# Boolean is player exists
def is_player_exists(player_id: int, guild_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT player_id FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    result = cursor.fetchone()

    # Return True if the player is found, otherwise return False
    if result:
        return True
    return False

# Boolean is player actively playing
def is_player_active(player_id: int, guild_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    # Query to check the player's active status in the specified guild
    cursor.execute('SELECT active FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    result = cursor.fetchone()

    # Return True if the player is found and active, otherwise return False
    if result and result[0] == 1:
        return True
    return False

# Boolean is player frozen playing
def is_player_frozen(player_id: int, guild_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    # Query to check the player's active status in the specified guild
    cursor.execute('SELECT frozen FROM players WHERE player_id = ? AND guild_id = ?', (player_id, guild_id))
    is_frozen = cursor.fetchone()

    # Return True if the player is found and active, otherwise return False
    if is_frozen and is_frozen[0] == 1:
        return True
    return False

# Function to set event channel for a guild
def set_event_channel(guild_id: int, channel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the row already exists for this guild
    cursor.execute('SELECT guild_id FROM guild_settings WHERE guild_id = ?', (guild_id,))
    exists = cursor.fetchone()

    if exists:
        # If the row exists, update the event channel
        cursor.execute('''
            UPDATE guild_settings
            SET event_channel_id = ?
            WHERE guild_id = ?
        ''', (channel_id, guild_id))
    else:
        # If the row does not exist, insert a new row
        cursor.execute('''
            INSERT INTO guild_settings (guild_id, event_channel_id)
            VALUES (?, ?)
        ''', (guild_id, channel_id))

    conn.commit()

# Function to get event channel for a guild
def get_event_channel(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT event_channel_id FROM guild_settings WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

def delete_event_channel(guild_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Remove the event channel ID from the database
    cursor.execute('''
        UPDATE guild_settings
        SET event_channel_id = NULL
        WHERE guild_id = ?
    ''', (guild_id,))

    conn.commit()


# Function to set admin channel for a guild
def set_admin_channel(guild_id: int, channel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the row already exists for this guild
    cursor.execute('SELECT guild_id FROM guild_settings WHERE guild_id = ?', (guild_id,))
    exists = cursor.fetchone()

    if exists:
        # If the row exists, update the admin channel
        cursor.execute('''
            UPDATE guild_settings
            SET admin_channel_id = ?
            WHERE guild_id = ?
        ''', (channel_id, guild_id))
    else:
        # If the row does not exist, insert a new row
        cursor.execute('''
            INSERT INTO guild_settings (guild_id, admin_channel_id)
            VALUES (?, ?)
        ''', (guild_id, channel_id))

    conn.commit()

# Function to get admin channel for a guild
def get_admin_channel(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT admin_channel_id FROM guild_settings WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

def delete_admin_channel(guild_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Remove the admin channel ID from the database
    cursor.execute('''
        UPDATE guild_settings
        SET admin_channel_id = NULL
        WHERE guild_id = ?
    ''', (guild_id,))

    conn.commit()

# Function to update player data by any field dynamically
def update_guild_setting_field(guild_id, field, value):
    """
    Update specified guild settings field for requested guild.

    Args:
        guild_id (int): The unique identifier of the guild.
        field (str): Field name to update.
        value (any): value to insert.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'UPDATE guild_settings SET {field} = ? WHERE guild_id = ?', (value, guild_id))
    conn.commit()

def get_guild_settings(guild_id):
    """
    Fetches all guild settings for requested guild.

    Args:
        guild_id (int): The unique identifier of the guild.

    Returns:
        dict: A dictionary containing the player's data with the following keys:
            - 'guild_id' (int): Unique ID of Guild.
            - 'event_channel_id' (int): Unique ID of channel where event messages will be posted.
            - 'admin_channel_id' (int): Unique ID of channel where admin messages will be posted.
            - 'game_invite_message_id' (int): Unique ID of Message for react join.
        None: If no guild settings data is found in the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM guild_settings WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    if result:  # Check if player exists
    # Return a PlayerData dataclass instance
        guild_settings_data = {
            "guild_id": result[0],
            "event_channel_id": result[1],
            "admin_channel_id": result[2],
            "game_invite_message_id": result[3]
        }
        return guild_settings_data
    return None


# Function to get the current lottery pool for a guild
def get_lottery_pool(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT candy_pool FROM lottery_pool WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        # If no pool exists for the guild, initialize it with 0
        cursor.execute('INSERT INTO lottery_pool (guild_id, candy_pool) VALUES (?, ?)', (guild_id, 0))
        conn.commit()
        return 0

# Function to update the lottery pool
def update_lottery_pool(guild_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_pool = get_lottery_pool(guild_id)
    new_pool = current_pool + amount
    cursor.execute('UPDATE lottery_pool SET candy_pool = ? WHERE guild_id = ?', (new_pool, guild_id))
    conn.commit()
    
# Function to update the lottery pool
def reset_lottery_pool(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE lottery_pool SET candy_pool = 0 WHERE guild_id = ?', (guild_id,))
    conn.commit()

# Resets the tickets_purchased field for all players in the given guild after the cast_spell event.
def reset_tickets_purchased(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE players SET tickets_purchased = 0 WHERE guild_id = ?', (guild_id,))
    conn.commit()