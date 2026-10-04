"""Artwork stays local metadata; private responses preserve ownership and purchases."""
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit

from utils.artwork import image_url, icon_embed, POTION_ART
from utils.messages import default_messages
from utils.utils import create_invite_embed, create_character_embed
from modals.shop import Checkout, show_inventory
import potions


def test_catalog_aliases_and_cached_lookup():
    loader = default_messages()
    assert len(loader.messages['artwork']) == 26
    for key, url in loader.messages['artwork'].items():
        parsed = urlsplit(url)
        assert parsed.scheme == 'https' and parsed.netloc == 'cdn.discordapp.com'
        assert parsed.path.startswith('/attachments/') and not parsed.query
        assert image_url(key) == url
    assert set(POTION_ART) == set(potions.CATALOG) | {'veil'}
    # Lookups must not reopen messages.json on every interaction.
    with patch('builtins.open', side_effect=AssertionError('Unexpected file read')):
        for _ in range(10):
            assert default_messages() is loader
            assert loader.get_message('who_is_luna', 'image_url') == image_url('luna_portrait')
            assert icon_embed('Private balance', 'candy_bucket').description == 'Private balance'
    for witch in ('Luna', 'Raven'):
        embed = create_character_embed(loader, witch)
        assert embed.image.url == image_url(witch.lower() + '_banner')
        assert embed.thumbnail.url == image_url(witch.lower() + '_portrait')
    assert create_invite_embed(loader).image.url == image_url('welcome_luna_and_raven')


def test_inventory_private_and_checkout_ownership(database):
    async def scenario():
        caller = NS(guild_id=1, user=NS(id=10), response=NS(send_message=AsyncMock(), edit_message=AsyncMock(), is_done=lambda:False))
        await show_inventory(caller)
        kwargs = caller.response.send_message.call_args.kwargs
        assert kwargs['ephemeral'] is True
        assert kwargs['embed'].thumbnail.url == image_url('inventory')
        kwargs['view'].stop()
        checkout = Checkout(10, 1, 'ward', 1, 5, 'artwork-order')
        outsider = NS(guild_id=1, user=NS(id=20), response=NS(send_message=AsyncMock(), is_done=lambda:False))
        before = list(database.iterdump())
        assert not await checkout.interaction_check(outsider)
        assert list(database.iterdump()) == before
        await checkout.cancel.callback(caller)
        assert list(database.iterdump()) == before
        assert caller.response.edit_message.call_args.kwargs['embed'] is None
    asyncio.run(scenario())
