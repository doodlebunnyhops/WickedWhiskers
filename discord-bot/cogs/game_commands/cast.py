"""Cauldron payouts are separate from potion perks and await their own rules."""
import discord
from discord import app_commands
from utils.checks import check_if_has_permission_or_role

cast_group = app_commands.Group(name="cast", description="Cast commands")

@cast_group.command(name="spell", description="Check cauldron event availability")
@check_if_has_permission_or_role()
async def cast_spell(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Cauldron draws are not available yet. Potion purchases grant gameplay perks, not entries. "
        "The pool is preserved while independent eligibility and payout rules are completed.", ephemeral=True)
