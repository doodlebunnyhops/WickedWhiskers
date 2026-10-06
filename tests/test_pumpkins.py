import asyncio
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import sqlite3
import pytest
import db_utils as db
from utils import pumpkins, player
from utils.messages import MessageLoader


class Rolls:
    def __init__(self, *values):
        self.values = iter(values)
    def random(self):
        return next(self.values)


def settle(roll, wager=10, magic=.99, action='smash', guild=1):
    return pumpkins.smash(guild, 10, wager, action, Rolls(roll, magic))[0]


@pytest.mark.parametrize('roll,delta', [(0,10),(.099,10),(.1,5),(.399,5),(.4,0),(.599,0),(.6,-5),(.899,-5),(.9,-20),(.999,-20)])
def test_net_outcomes_and_boundaries(database, roll, delta):
    result = settle(roll)
    data = db.get_player_data(10,1)
    assert result['delta'] == delta
    assert data['candy_in_bucket'] == 50+delta
    assert data['pumpkins_smashed'] == 1
    assert data['total_candy_spent_on_pumpkins'] == 10
    assert data['total_candy_won_from_pumpkins'] == max(delta,0)
    assert data['total_candy_lost_on_pumpkins'] == max(-delta,0)


@pytest.mark.parametrize('wager', [1,3,5])
def test_small_reward_matches_normal_loss(database,wager):
    assert settle(.2,wager,action='win')['delta'] == (wager+1)//2
    assert settle(.7,wager,action='loss')['delta'] == -(wager+1)//2
    assert db.get_player_data(10,1)['candy_in_bucket'] == 50


@pytest.mark.parametrize('balance,wager,roll', [(15,10,.95),(20,10,.95),(1,1,.7)])
def test_entire_bucket_and_actual_cauldron_contribution(database,balance,wager,roll):
    database.execute('UPDATE players SET candy_in_bucket=? WHERE guild_id=1 AND player_id=10',(balance,))
    database.commit()
    result = settle(roll,wager,magic=0)
    assert result['balance'] == 0
    assert result['delta'] == -balance
    assert result['message_key'] == 'lose_all'
    assert db.get_cauldron_pool(1) == balance
    assert db.get_cauldron_contribution(10,1) == balance


@pytest.mark.parametrize('roll,magic,contribution', [(.2,.299,5),(.2,.30,0),(.7,.899,5),(.7,.90,0),(.5,0,0)])
def test_magic_thresholds(database,roll,magic,contribution):
    result = settle(roll,magic=magic)
    assert result['contribution'] == contribution
    assert db.get_cauldron_pool(1) == contribution
    assert db.get_player_data(10,1)['candy_in_bucket'] == 50+result['delta']


def test_replay_and_guild_isolation(database):
    first = settle(.2,magic=0)
    result,repeated = pumpkins.smash(1,10,10,'smash',Rolls())
    assert repeated and result == first
    assert db.get_player_data(10,1)['candy_in_bucket'] == 55
    assert db.get_cauldron_pool(1) == 5
    assert settle(.7,guild=2)['balance'] == 45


def test_atomic_rollback(database):
    database.execute("CREATE TRIGGER reject_action BEFORE INSERT ON potion_actions BEGIN SELECT RAISE(ABORT, 'test'); END")
    database.commit()
    with pytest.raises(sqlite3.Error): settle(.2,magic=0)
    assert db.get_player_data(10,1)['candy_in_bucket'] == 50
    assert db.get_player_data(10,1)['pumpkins_smashed'] == 0
    assert db.get_cauldron_pool(1) == 0
    assert db.get_cauldron_contribution(10,1) == 0


@pytest.mark.parametrize('wager',[0,-1,51,True,1.5])
def test_invalid_wagers(database,wager):
    with pytest.raises(pumpkins.PumpkinError): settle(.2,wager)
    assert db.get_player_data(10,1)['candy_in_bucket'] == 50


@pytest.mark.parametrize('state',['paused','frozen','inactive'])
def test_ineligible_players(database,state):
    if state == 'paused': db.set_game_disabled(1,True)
    else:
        database.execute('UPDATE players SET '+('frozen=1' if state=='frozen' else 'active=0')+' WHERE guild_id=1 AND player_id=10')
        database.commit()
    with pytest.raises(pumpkins.PumpkinError): settle(.2)
    assert db.get_player_data(10,1)['candy_in_bucket'] == 50


def test_wipeout_announcement_and_replay(database,monkeypatch):
    loader = MessageLoader(str(Path(__file__).resolve().parents[1]/'discord-bot/utils/messages.json'))
    caller = NS(id=987,user=NS(id=10,mention='<@10>',display_name='Player'),guild=NS(id=1),client=NS(message_loader=loader),delete_original_response=AsyncMock(),edit_original_response=AsyncMock(),response=NS(defer=AsyncMock()),followup=NS(send=AsyncMock()))
    post = AsyncMock()
    monkeypatch.setattr(player,'post_to_target_channel',post)
    rolls=Rolls(.99,0)
    monkeypatch.setattr(pumpkins.random,'random',rolls.random)
    asyncio.run(player.smash_pumpkin(caller,30))
    embed = post.call_args.args[1]
    assert '50' in embed.description and 'Raven' in embed.description
    assert 'cauldron' in embed.description and 'Bucket:' not in embed.description
    assert 'Net change: -50' in embed.description
    assert post.call_args.kwargs['channel_type'] == 'event'
    caller.followup.send.assert_not_awaited()
    caller.delete_original_response.assert_awaited_once()
    asyncio.run(player.smash_pumpkin(caller,30))
    assert post.await_count == 1
    assert db.get_cauldron_pool(1) == 50
