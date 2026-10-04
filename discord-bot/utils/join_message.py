"""Seed the join reaction while keeping the invitation usable on Discord failures."""
import discord

JOIN_EMOJI = '🎃'


async def seed_join_reaction(interaction, message):
    try:
        await message.add_reaction(JOIN_EMOJI)
    except discord.HTTPException:
        text = interaction.client.message_loader.get_message('join_reaction', 'failed', message_url=message.jump_url)
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)
        return False
    return True
