import asyncio
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
from discord import app_commands
import db_utils as db
from cogs.game_commands.get import get_leaderboard
from utils.leaderboard import CATEGORIES, make_embed
from utils.messages import MessageLoader
from utils.player import calculate_evilness, calculate_sweetness


def interaction(guild=1):
    return NS(user=NS(id=10),guild=NS(id=guild,get_member=lambda uid: None),client=NS(message_loader=MessageLoader(str(Path(__file__).resolve().parents[1]/'discord-bot/utils/messages.json'))),response=NS(send_message=AsyncMock(),edit_message=AsyncMock()),edit_original_response=AsyncMock())


def test_sweet_evil_match_existing_player_formulas(database):
    database.execute('UPDATE players SET total_candy_given=30,total_candy_stolen=10,treats_given=100 WHERE guild_id=1 AND player_id=10')
    database.execute('UPDATE players SET total_candy_given=0,total_candy_stolen=20,successful_tricks=1 WHERE guild_id=1 AND player_id=20')
    database.execute('UPDATE players SET total_candy_given=10,total_candy_stolen=0,treats_given=1 WHERE guild_id=1 AND player_id=30')
    database.commit()
    sweet=db.get_leaderboard_query('most_sweet',1)
    evil=db.get_leaderboard_query('most_evil',1)
    assert [row[0] for row in sweet[:2]]==[30,10]
    assert [row[0] for row in evil[:2]]==[20,10]
    for uid,given,stolen in [(10,30,10),(20,0,20),(30,10,0),(40,0,0)]:
        assert dict(sweet)[uid]==pytest.approx(calculate_sweetness(given,stolen))
        assert dict(evil)[uid]==pytest.approx(calculate_evilness(given,stolen))
    assert all(value==0 for uid,value in db.get_leaderboard_query('most_evil',2))
    assert '75.00% sweetness' in make_embed(interaction(),'most_sweet',[(10,.75)]).description


def test_all_pages_and_single_category_queries(database,monkeypatch):
    original=db.get_leaderboard_query
    requested=[]
    def query(key,guild):
        requested.append(key)
        assert key!='all'
        return original(key,guild)
    monkeypatch.setattr(db,'get_leaderboard_query',query)
    async def run():
        caller=interaction()
        await get_leaderboard.callback(caller,app_commands.Choice(name='All',value='all'))
        view=caller.response.send_message.call_args.kwargs['view']
        assert requested==list(CATEGORIES)
        assert view.previous_button.disabled
        assert len(view.selector.options)==8
        for index in range(8):
            assert view.index==index
            assert f'Category {index+1} of 8' in view.embed().footer.text
            assert len(view.embed())<6000
            if index<7:await view.next(caller)
        assert view.next_button.disabled
        await view.previous(caller)
        assert view.index==6
        view.selector._values=['most_sweet']
        await view.choose(caller)
        assert view.index==5
        other=interaction();other.user.id=999
        assert not await view.interaction_check(other)
        assert other.response.send_message.call_args.kwargs['ephemeral']
        await view.on_timeout()
        caller.edit_original_response.assert_awaited_once_with(view=None)
        view.stop()
    asyncio.run(run())


@pytest.mark.parametrize('key',CATEGORIES)
def test_individual_and_empty_category(database,key):
    caller=interaction()
    asyncio.run(get_leaderboard.callback(caller,app_commands.Choice(name=key,value=key)))
    result=caller.response.send_message.call_args.kwargs
    assert 'view' not in result
    assert result['embed'].description
    assert result['ephemeral'] is False
    empty=interaction(999)
    asyncio.run(get_leaderboard.callback(empty,app_commands.Choice(name=key,value=key)))
    assert empty.response.send_message.call_args.kwargs['ephemeral'] is True


def test_all_empty_guild_is_private(database):
    caller=interaction(999)
    asyncio.run(get_leaderboard.callback(caller,app_commands.Choice(name='All',value='all')))
    assert caller.response.send_message.call_args.kwargs['ephemeral']
    assert 'view' not in caller.response.send_message.call_args.kwargs


def test_ten_long_names_stay_within_embed_limit():
    caller=interaction()
    caller.guild.get_member=lambda uid:NS(display_name='*' * 64)
    embed=make_embed(caller,'candy_hoarders',[(i,2**63-1) for i in range(15)])
    assert len(embed.description)<4096
    assert len(embed.description.splitlines())==10
