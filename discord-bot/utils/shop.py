"""Compatibility entry points: target members can never choose the buyer."""
from modals.shop import open_shop


async def buy_potion(interaction, user=None, amount=None):
    # Legacy callers now open the caller's own catalog; generic potions no longer exist.
    await open_shop(interaction)


async def view_prices(interaction):
    await open_shop(interaction)
