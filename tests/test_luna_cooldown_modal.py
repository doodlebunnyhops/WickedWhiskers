"""Regression coverage for buying two bottles then using one during cooldown."""
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
import potions
from modals.shop import UsePotionModal


@pytest.mark.parametrize('prior_summoner',[10,20])
def test_two_purchased_bottles_survive_cooldown_modal(database,monkeypatch,prior_summoner):
    # A previous summon by this player or another player starts the shared cooldown.
    potions.purchase(1,prior_summoner,'luna',1,10,'old-purchase')
    potions.use(1,prior_summoner,'luna','old-use',{10,20,30,40,50},now=100)
    potions.purchase(1,10,'luna',2,10,'buy-two')
    assert potions.inventory(1,10)[0]['luna']==2
    before=list(database.iterdump())
    monkeypatch.setattr(potions.time,'time',lambda:101)
    async def scenario():
        modal=UsePotionModal(10,1)
        modal.potion._values=['luna']
        interaction=NS(id=999,guild_id=1,user=NS(id=10),guild=NS(chunked=True,members=[NS(id=uid,bot=False) for uid in (10,20,30,40,50)]),response=NS(defer=AsyncMock(),is_done=lambda:True),followup=NS(send=AsyncMock()))
        await modal.on_submit(interaction)
        message=interaction.followup.send.call_args.kwargs["embed"].description
        assert interaction.followup.send.call_args.kwargs["ephemeral"]
        assert interaction.followup.send.call_args.kwargs["embed"].thumbnail.url.endswith("/cooldown.png")
        assert 'Luna is resting' in message and 'potion is safe' in message
        # A second rejected submission also must not change inventory or counters.
        interaction.id=1000
        await modal.on_submit(interaction)
    asyncio.run(scenario())
    assert list(database.iterdump())==before
    assert potions.inventory(1,10)[0]['luna']==2
    # Once the cooldown ends, precisely one bottle is consumed.
    potions.use(1,10,'luna','after-cooldown',{10,20},now=160)
    assert potions.inventory(1,10)[0]['luna']==1
