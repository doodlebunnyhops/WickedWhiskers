import os
import requests
import time
from datetime import datetime

# Load environment variables
bot_token = os.getenv("DISCORD_BOT_TOKEN")
application_id = os.getenv("DISCORD_APPLICATION_ID")
guild_id = os.getenv("DISCORD_GUILD_ID")

print(f"DISCORD_BOT_TOKEN: {bot_token}")
print(f"DISCORD_APPLICATION_ID: {application_id}")
print(f"DISCORD_GUILD_ID: {guild_id}")

# Check if environment variables are set
if not bot_token or not application_id:
    raise ValueError("Environment variables DISCORD_BOT_TOKEN and DISCORD_APPLICATION_ID must be set")
if not guild_id:
    print("Warning: Guild ID not set, you will not be able to check guild-specific commands.")

# Define a function to check commands based on type (global or guild)
def check_commands(command_type='global'):
    # Add a timestamp for when the check starts
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{current_time}] Starting check for {command_type} commands...")

    if command_type == 'global':
        url = f"https://discord.com/api/v10/applications/{application_id}/commands"
    elif command_type == 'guild' and guild_id:
        url = f"https://discord.com/api/v10/applications/{application_id}/guilds/{guild_id}/commands"
    else:
        raise ValueError("Invalid command type or missing guild ID for guild-specific commands.")

    # Define the headers for authentication
    headers = {
        "Authorization": f"Bot {bot_token}"
    }

    # Make the request to Discord API
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # This will raise an exception for HTTP error responses
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch commands: {e}")
        return

    # Try to parse the response as JSON
    try:
        commands = response.json()
        print(f"RAW:\n{commands}")
    except ValueError:
        print("Error: Failed to parse JSON response")
        return

    # Print the length of the commands (number of commands)
    print(f"Number of commands found: {len(commands)}")

    # Pretty print the commands and subcommands
    for command in commands:
        print(f"Command: {command['name']}, Description: {command['description']}")
        
        # Check if the command has options (which could include subcommands or other inputs)
        if 'options' in command:
            for option in command['options']:
                # Check if it's a subcommand or subcommand group
                if option['type'] in [1, 2]:  # 1 is a subcommand, 2 is a subcommand group
                    print(f"  Subcommand: {option['name']}, Description: {option['description']}")
                    
                    # If it's a subcommand group, it may have subcommands as well
                    if option['type'] == 2 and 'options' in option:
                        for sub_option in option['options']:
                            if sub_option['type'] == 1:  # Subcommands within subcommand groups
                                print(f"    Sub-subcommand: {sub_option['name']}, Description: {sub_option['description']}")

# Choose between checking global or guild-specific commands at runtime
command_type = input("Enter 'global' to check global commands or 'guild' to check guild-specific commands: ").strip().lower()

# Run the check every 1 minute
while True:
    check_commands(command_type)
    time.sleep(300)  # Wait for 1 minute before checking again
