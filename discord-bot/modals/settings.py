import discord
from discord import app_commands
from discord.ui import Modal, TextInput
import db_utils

class Bot(Modal):
    def __init__(self):
        super().__init__(title="Bot Settings Configuration")

        # Add input fields to the modal
        self.add_item(TextInput(label="Admin Channel Name", placeholder="Channel Name", required=True))
        self.add_item(TextInput(label="Event Channel Name", placeholder="Channel Name", required=True))
        self.add_item(TextInput(label="Invite Channel Name", placeholder="Channel Name", required=False))
        self.add_item(TextInput(label="Admin Role Name", placeholder="Role Name", required=False))

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        error_messages = []  # List to accumulate errors

        # Extract the values entered by the user
        admin_channel_name = self.children[0].value
        event_channel_name = self.children[1].value
        invite_channel_name = self.children[2].value
        admin_role_name = self.children[3].value

        # Validate Event Channel
        event_channel = discord.utils.get(guild.channels, name=event_channel_name)
        if not event_channel or not isinstance(event_channel, discord.TextChannel):
            error_messages.append(f"❌ Event Channel, `{event_channel_name}`, not found or is not a valid text channel.")

        # Validate Admin Channel
        admin_channel = discord.utils.get(guild.channels, name=admin_channel_name)
        if not admin_channel or not isinstance(admin_channel, discord.TextChannel):
            error_messages.append(f"❌ Admin Channel, `{admin_channel_name}`, not found or is not a valid text channel.")

        # Validate Invite Channel (optional)
        if invite_channel_name:
            invite_channel = discord.utils.get(guild.channels, name=invite_channel_name)
            if not invite_channel or not isinstance(invite_channel, discord.TextChannel):
                error_messages.append(f"❌ Invite, `{invite_channel_name}`, Channel not found or is not a valid text channel.")

        # Validate Admin Role
        admin_role = discord.utils.get(guild.roles, name=admin_role_name)
        if not admin_role:
            error_messages.append(f"❌ Admin Role, `{admin_role_name}`, not found.")


        # If there are any validation errors, display them all at once
        if error_messages:
            error_messages.insert(0, "⚠️ The following errors were found:\n")
            error_messages.append("\nPlease correct the errors and try again.")
            await interaction.response.send_message("\n".join(error_messages), ephemeral=True)
        else:
            # If all validations pass, proceed to update the settings
            db_utils.set_guild_settings(guild.id, event_channel_id=event_channel.id, admin_channel_id=admin_channel.id, 
                                        game_invite_channel_id=invite_channel.id if invite_channel else None, game_invite_message_id=None)
            if admin_role is not None:
                db_utils.set_role_by_guild(guild.id, admin_role.id)
            await interaction.response.send_message(f"Settings have been updated:\n"
                                                    f"Event Channel: {event_channel.mention}\n"
                                                    f"Admin Channel: {admin_channel.mention}\n"
                                                    f"Invite Channel: {invite_channel.name if invite_channel else 'Not Set'}\n"
                                                    f"Admin Role: {admin_role.mention}\n",
                                                    ephemeral=True)
            
class Game(Modal):
    def __init__(self):
        super().__init__(title="Game Settings Configuration")

        # Add input fields to the modal
        self.add_item(TextInput(label="Potion Price", placeholder="default 10", required=False,default="10"))
        self.add_item(TextInput(label="Candy Steal Success Rate", placeholder="default 100%", required=False ,default="100%"))

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        error_messages = []  # List to accumulate errors

        # Extract the values entered by the user
        potion_price = self.children[0].value
        trick_success_rate = self.children[1].value

        # Validate Potion Cost
        try:
            potion_price = int(potion_price)
            if potion_price <= 0:
                raise ValueError(f"Potion cost, `{potion_price}`, must be a positive integer.")
        except ValueError:
            error_messages.append("❌ Potion cost must be a valid positive integer.")

        # Validate Steal Success Rate
        try:
            trick_success_rate = trick_success_rate.strip('%')  # Remove the '%' sign if present
            trick_success_rate = float(trick_success_rate)
            if trick_success_rate <= 0 or trick_success_rate > 500:
                raise ValueError(f"Steal success rate must be a number between 1 and 100.\n\tProvided value: {trick_success_rate}")
        except ValueError:
            error_messages.append(f"❌ Steal success rate must be a valid percentage between 1 and 100.\n\t\tProvided value: {trick_success_rate}")

        # If there are any validation errors, display them all at once
        if error_messages:
            error_messages.insert(0, "⚠️ The following errors were found:\n")
            error_messages.append("\nPlease correct the errors and try again.")
            await interaction.response.send_message("\n".join(error_messages), ephemeral=True)
        else:
            # If all validations pass, proceed to update the settings
            db_utils.set_game_setting(guild.id, potion_price=potion_price, trick_success_rate=trick_success_rate)

            await interaction.response.send_message(f"Game Settings have been updated:\n"
                                                    f"Potion Cost: {potion_price}\n"
                                                    f"Steal Success Rate: {trick_success_rate}%",
                                                    ephemeral=True)