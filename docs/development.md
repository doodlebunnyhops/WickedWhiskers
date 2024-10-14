# Discord Bot Setup Guide

This document outlines the steps to set up and run this Discord bot on your own machine.

## Overview

1. [Prerequisites](#prerequisites)
   - Python Installation
   - Required Python Libraries
   - Discord Bot Setup
   - SQLite (optional)

2. [Environment Setup](#environment-setup)
   - Creating a `.env` File
   - Required Environment Variables

3. [Installing Dependencies](#installing-dependencies)
   - Installing Python Libraries

4. [Setting Up Discord Bot](#setting-up-discord-bot)
   - Creating a Discord Bot
   - Adding the Bot to a Server
   - Setting Permissions for the Bot

5. [Database Setup](#database-setup)
   - SQLite Configuration (if applicable)
   - Table Creation

6. [Running the Bot](#running-the-bot)
   - Executing the bot

7. [Error Handling](#error-handling)
   - Common Errors and Fixes

8. [Testing the Bot](#testing-the-bot)
   - Steps to test commands in a test server

9. [Contributing to the Project](#contributing-to-the-project)
   - Contribution Guidelines (optional)

---

## Prerequisites

### Python Installation
Ensure that Python (version 3.8 or higher) is installed on your machine. You can download it from [Python's official website](https://www.python.org/downloads/).

### Required Python Libraries
You will need the following Python libraries:
- `discord.py`
- `python-dotenv`

### Discord Bot Setup
You'll need a bot token from Discord to run this bot.

---

## Environment Setup

### Creating a `.env` File
You need to create a `.env` file in your project directory to store sensitive credentials, such as your bot token.

Example `.env` file:

**Important:** This `.env` file should be added to your `.gitignore` file to prevent exposing credentials in GitHub.

### Required Environment Variables
- `GUILD`: The Discord Server ID where the bot will operate (used for testing or production).
- `FEEDBACK_CH`: The Discord channel where logs or feedback will be posted.
- `DISCORD_API_TOKEN`: The token for your bot, obtained from the Discord Developer Portal.

---

## Installing Dependencies

Install the required Python libraries using the `requirements.txt` file or manually with pip:

```bash
pip install -r requirements.txt
```

or manually, refer to [requirements.txt](../requirements.txt)

```bash
pip install discord.py
pip install python-dotenv
```

## Setting Up Discord Bot

### Creating a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click on "New Application" to create a new bot.
3. Give your bot a name and click "Create."
4. In the left sidebar, go to "Bot" and click on "Add Bot."
5. Confirm by clicking "Yes, do it!" Your bot will be created.
6. Copy the bot token by clicking "Reset Token" and saving it to your `.env` file as `DISCORD_API_TOKEN`.

### Adding the Bot to a Server

1. In the Discord Developer Portal, go to the "OAuth2" tab and select "URL Generator."
2. Under "OAuth2 URL Generator," check the box for "bot" under scopes.
3. Under "Bot Permissions," select the required permissions your bot needs
    - `Send Messages` - for bot responses
    - `Presence` - for context_menu function
4. Copy the generated URL and paste it into your browser.
5. Select the server where you want to add the bot, and click "Authorize."

### Setting Permissions for the Bot

1. Once the bot is added to your server, go to your Discord server settings.
2. Go to "Roles" and find your bot's role.
3. Assign the required permissions for the bot, making sure it has permission to read and send messages, manage roles, and any other necessary permissions for your bot's functionality.
4. Save the settings.

## Database Setup

### SQLite Configuration (if applicable)

1. This bot uses an SQLite database by default to store player and guild information.
2. Ensure that your project has SQLite installed by running:

   ```bash
   pip install sqlite3
   ```

3. The bot will automatically create and manage the SQLite database (`candy_game.db`) if it does not already exist in the dir which `bot.py` was called.

### Table Creation

1. The bot will automatically create the required tables in the SQLite database.
2. The following tables are created:

   - **players**: Stores player-specific data like candy count, successful/failed steals, and active status.
   - **guild_settings**: Stores guild-specific settings such as event and admin channels.
   - **lottery_pool**: Stores the amount of candy available for the lottery event.
   - **role_access**: Stores which roles have access to restricted bot commands.

3. Ensure that the bot has write access to the directory where the SQLite database is stored.

## Running the Bot

1. Before running the bot, ensure all required libraries are installed:
   
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure that your `.env` file is correctly set up with the required environment variables:

   - `GUILD`: Discord Server ID used for testing
   - `FEEDBACK_CH`: Discord channel for additional logs (optional)
   - `DISCORD_API_TOKEN`: Your bot's API token

3. Execute the bot by running the following command in your terminal or command prompt:

   ```bash
   python bot.py
   ```

4. If the bot starts successfully, you should see a confirmation message in the terminal indicating that the bot is connected and ready to interact with the Discord server.

5. In the Discord server, you can now use the bot’s commands as specified.

## Error Handling

### Common Errors and Fixes

1. **Missing API Token Error**:
   - Error: "DISCORD_API_TOKEN not set"
   - Fix: Ensure that the `.env` file includes the correct `DISCORD_API_TOKEN` value and that it's loaded properly. Check the setup in `settings.py`.

2. **Invalid Discord API Token**:
   - Error: "401 Unauthorized"
   - Fix: Verify that your bot’s API token is correctly set and hasn’t been regenerated. If the token was regenerated in the Discord Developer Portal, make sure to update it in the `.env` file.

3. **Bot not responding to commands**:
   - Error: No interaction from the bot when commands are used.
   - Fix: Ensure the bot has the required permissions in your Discord server. Make sure the bot is added with the necessary scope (`bot` and `applications.commands`) and the necessary intents are enabled in the Discord Developer Portal.

4. **Database-related errors**:
   - Error: "SQLite database not found" or "Table not found."
   - Fix: Verify that the SQLite database is correctly configured and the required tables have been created. You can check the database setup section for help.


## Testing the Bot

### Steps to test commands in a test server:

1. **Create a Test Server**:
   - On Discord, create a new server to use as a test environment. You can add your bot to this server without affecting any live servers.
   
2. **Add the Bot to the Test Server**:
   - Use the OAuth2 URL generated in the Discord Developer Portal to invite the bot to your test server. Make sure to include the necessary permissions and intents.

3. **Use the Commands**:
   - Start interacting with the bot by running its commands. You can test commands like `/help` or `/join` to verify everything is functioning as expected.

4. **Check Logs**:
   - If you set up the `FEEDBACK_CH` environment variable for logging and it was been set in code, check the designated channel for log outputs. Alternatively, you can check the terminal for detailed debug logs.
   - look at `/logs` dir for output 
   - refer to terminal ouput


---

## Contributing to the Project

### Contribution Guidelines

1. **Fork the Repository**:
   - Start by forking the repository on GitHub. This will allow you to make changes to your version without affecting the main repository.

2. **Clone the Repository**:
   - Clone your forked repository locally using:
     ```bash
     git clone https://github.com/your-username/repository-name.git
     ```

3. **Create a New Branch**:
   - Before making changes, create a new branch to organize your contributions:
     ```bash
     git checkout -b feature-branch-name
     ```

4. **Write Code**:
   - Implement the new feature, bug fix, or improvement in your new branch. Make sure to follow the coding standards set by the project.

5. **Test Your Changes**:
   - Test your changes locally to ensure they work as expected. Be sure to test against a test Discord server, as outlined in the Testing section.

6. **Submit a Pull Request**:
   - Push your changes to your forked repository:
     ```bash
     git push origin feature-branch-name
     ```
   - Then, submit a pull request (PR) to the main repository.

7. **Review and Feedback**:
   - The repository maintainers will review your PR. They may provide feedback or request changes. Make sure to address any comments before your contribution is merged.

8. **Contributions Welcome**:
   - All contributions, including bug reports, feature requests, and code improvements, are welcome. Make sure to adhere to the code of conduct and contribution guidelines.

