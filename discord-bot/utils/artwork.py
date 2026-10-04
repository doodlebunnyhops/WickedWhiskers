"""Embed-only CDN references. No image fetching, uploads, or database access."""
import discord
from utils.messages import default_messages

POTION_ART = {
    'ward': 'witchs_ward', 'cunning': 'ravens_cunning', 'mirror': 'mirror_brew',
    'sticky': 'sticky_fingers', 'second_chance': 'second_chance',
    'favor': 'lunas_favor', 'luna': 'lunas_calling', 'veil': 'witchs_veil',
}


def image_url(key):
    return default_messages().get_message('artwork', key, default='')


def icon_embed(description, key, *, title=None):
    embed = discord.Embed(title=title, description=description, color=discord.Color.purple())
    url = image_url(key)
    if url:
        embed.set_thumbnail(url=url)
    return embed
