import os
import requests
import time

# Prompt for application_id and whether to delete from global or guild
APPLICATION_ID = input("Please enter your application ID: ")
DELETE_SCOPE = input("Do you want to delete the commands globally or for a specific guild? (Type 'global' or 'guild'): ").strip().lower()

# Load environment variables for bot token and guild ID if needed
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = None

if DELETE_SCOPE == "guild":
    GUILD_ID = os.getenv("DISCORD_GUILD_ID")
    if not GUILD_ID:
        GUILD_ID = input("Please enter your Guild ID: ")

# Set up the headers for Discord API requests
headers = {
    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
    "Content-Type": "application/json"
}

# Function to get commands and return them
def get_commands(scope):
    if scope == "global":
        url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands"
    else:  # guild-specific
        url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/guilds/{GUILD_ID}/commands"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        commands = response.json()
        return commands
    else:
        print(f"Failed to fetch commands. Status code: {response.status_code}")
        print("Error response:", response.text)
        return []

# Function to delete a specific command by its ID, with rate limit handling
def delete_command(command_id, scope):
    if scope == "global":
        url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands/{command_id}"
    else:  # guild-specific
        url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/guilds/{GUILD_ID}/commands/{command_id}"
    
    response = requests.delete(url, headers=headers)
    
    # Handle rate limiting
    if response.status_code == 429:
        retry_after = response.json().get('retry_after', 1)
        print(f"Rate limited! Retrying after {retry_after} seconds.")
        time.sleep(retry_after)
        delete_command(command_id, scope)  # Retry after delay
    elif response.status_code == 204:
        print(f"Successfully deleted command with ID: {command_id}")
    else:
        print(f"Failed to delete command. Status code: {response.status_code}")
        print("Error response:", response.text)

# Get the list of commands based on the scope (global or guild)
commands = get_commands(DELETE_SCOPE)

# Iterate through the commands and print their names and IDs
if commands:
    print("\nCommands found:")
    command_choices = {}
    for index, command in enumerate(commands, start=1):
        print(f"{index}: {command['name']} (ID: {command['id']})")
        command_choices[index] = command

    # Ask the user which commands to delete
    to_delete = input("\nEnter the numbers of the commands you want to delete (comma-separated, e.g., '1,3,5'), or type 'all' to delete all commands: ").strip()

    if to_delete.lower() == 'all':
        # Delete all commands
        for command in commands:
            delete_command(command["id"], DELETE_SCOPE)
    else:
        # Delete only selected commands
        command_numbers = to_delete.split(',')
        for num in command_numbers:
            try:
                num = int(num.strip())
                if num in command_choices:
                    delete_command(command_choices[num]["id"], DELETE_SCOPE)
                else:
                    print(f"Invalid choice: {num}")
            except ValueError:
                print(f"Invalid input: {num}")
else:
    print("No commands found to delete.")
