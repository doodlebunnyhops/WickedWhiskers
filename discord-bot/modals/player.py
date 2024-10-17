import discord
from discord.ext import commands

from db_utils import is_player_active
from utils.helper import give_treat
from utils.utils import post_to_target_channel


# Define the Modal with an input field for the points
class Treat(discord.ui.Modal, title="Amount"):
    amount = discord.ui.TextInput(label="How many peices will you give?", placeholder="e.g., 10", required=True)
    def __init__(self, target_user: discord.Member):
        super().__init__()
        self.target_user = target_user
        self.title = f"Treat {target_user.display_name} to some candy!"

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if amount < 0:
                await interaction.response.send_message(f"{interaction.user.mention}, you can't give negative candy!", ephemeral=True)
                return
            
            #get the event message and personal message responses
            event_message,personal_message = give_treat(interaction,self.target_user,amount)

            #check if event_message is None, this means there was an error
            if event_message is None:
                await interaction.response.send_message(personal_message, ephemeral=True)
            else:
                #Send responses
                await interaction.response.send_message(personal_message,ephemeral= True)
                await post_to_target_channel(channel_type="event", message=event_message, interaction=interaction)

        except ValueError:
             print("ValueError")
             await interaction.response.send_message("Please enter a valid number.", ephemeral=True)
