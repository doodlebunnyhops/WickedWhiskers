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


def settle(roll, wager=10, magic=.99, action='smash', guild=1, size=.5):
    return pumpkins.smash(guild, 10, wager, action, Rolls(roll, size, magic))[0]


@pytest.mark.parametrize('roll,delta', [(0,10),(.099,10),(.1,5),(.399,5),(.4,0),(.599,0),(.6,-5),(.899,-5),(.9,-10),(.999,-10)])
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


@pytest.mark.parametrize('balance,wager,roll', [(15,15,.95),(50,50,.95),(1,1,.7)])
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
    rolls=Rolls(.99,.99,0)
    monkeypatch.setattr(pumpkins.random,'random',rolls.random)
    asyncio.run(player.smash_pumpkin(caller,50))
    embed = post.call_args.args[1]
    assert '50' in embed.description and 'Raven' in embed.description
    assert 'cauldron' in embed.description and 'Bucket:' not in embed.description
    assert 'Net change: -50' in embed.description
    assert post.call_args.kwargs['channel_type'] == 'event'
    caller.followup.send.assert_not_awaited()
    caller.delete_original_response.assert_awaited_once()
    asyncio.run(player.smash_pumpkin(caller,50))
    assert post.await_count == 1
    assert db.get_cauldron_pool(1) == 50


def test_small_server_threshold_zero_inactive_frozen_and_veil(database):
    # Exactly three positive eligible buckets: 10, 50, 100; median 50.
    database.execute('UPDATE players SET candy_in_bucket=0 WHERE guild_id=1')
    for uid,balance in [(10,10),(20,50),(30,100)]:
        database.execute('UPDATE players SET candy_in_bucket=? WHERE guild_id=1 AND player_id=?',(balance,uid))
    database.commit()
    assert pumpkins.smaller_bucket_boost(database,1,10,100)==(.04,3)
    assert pumpkins.smaller_bucket_boost(database,1,100,100)==(0,3)
    database.execute('INSERT INTO player_protection VALUES(1,20,0,99999,\'fixed\',5,20,600)')
    assert pumpkins.smaller_bucket_boost(database,1,10,100)==(.04,3) # Veil can smash
    database.execute('UPDATE players SET frozen=1 WHERE guild_id=1 AND player_id=20')
    assert pumpkins.smaller_bucket_boost(database,1,10,100)==(0,2)
    database.execute("INSERT INTO player_freezes VALUES(1,20,50,'old',30)")
    assert pumpkins.smaller_bucket_boost(database,1,10,100)==(.04,3) # Expired freeze
    database.execute('UPDATE players SET active=0 WHERE guild_id=1 AND player_id=30')
    assert pumpkins.smaller_bucket_boost(database,1,10,100)==(0,2)
    database.commit()


def test_even_median_and_other_guilds_are_not_counted(database):
    database.execute('UPDATE players SET candy_in_bucket=0 WHERE guild_id=1')
    for uid,balance in [(10,10),(20,30),(30,50),(40,1000)]:
        database.execute('UPDATE players SET candy_in_bucket=? WHERE guild_id=1 AND player_id=?',(balance,uid))
    database.commit()
    assert pumpkins.smaller_bucket_boost(database,1,10)==(.0375,4)


@pytest.mark.parametrize('roll,outcome',[(.4,'win'),(.439999,'win'),(.44,'break_even'),(.59999,'break_even'),(.6,'lose'),(.9,'lose_double')])
def test_boost_takes_only_break_even_probability(database,roll,outcome):
    database.execute('UPDATE players SET candy_in_bucket=10 WHERE guild_id=1 AND player_id=10');database.commit()
    result=settle(roll,wager=1)
    assert result['outcome']==outcome and result['win_boost']==.04


@pytest.mark.parametrize('outcome,low,high',[('win',10,40),('lose',10,40),('win_extra',25,75),('lose_double',50,100)])
def test_allin_amount_range(outcome,low,high):
    assert pumpkins.roll_amount(50,50,outcome,Rolls(0))==low
    assert pumpkins.roll_amount(50,50,outcome,Rolls(.999999))==high


def test_large_integer_rounding_and_small_wagers():
    maxint=2**63-1
    assert pumpkins.roll_amount(maxint,maxint,'win_extra',Rolls(.5))==maxint
    for bucket in (1,2,50,10000):
        for outcome in ('win','lose','win_extra','lose_double'):
            assert pumpkins.roll_amount(1,bucket,outcome,Rolls(0))>=1


def test_actual_amount_controls_narration_and_wipeout(database):
    low_win=settle(0,wager=50,size=0)
    assert low_win['outcome']=='win_extra' and low_win['message_key']=='win' and low_win['delta']==25
    # All-in losses are capped even for a very large rolled amount.
    result=settle(.99,wager=75,size=.999999,action='loss')
    assert result['delta']==-75 and result['message_key']=='lose_all'


@pytest.mark.parametrize('balance,wager', [(10000,2500),(50,10),(50,49),(1,1),(2**63-1,2500)])
@pytest.mark.parametrize('roll', [.7,.95])
@pytest.mark.parametrize('size', [0,.5,.999999])
def test_losses_never_exceed_wager(database,balance,wager,roll,size):
    database.execute('UPDATE players SET candy_in_bucket=? WHERE guild_id=1 AND player_id=10',(balance,))
    database.commit()
    result=settle(roll,wager,magic=0,size=size)
    lost=-result['delta']
    assert 0 < lost <= wager
    if roll == .95:
        assert lost == wager
    data=db.get_player_data(10,1)
    assert data['candy_in_bucket'] == balance-lost
    assert data['total_candy_lost_on_pumpkins'] == lost
    assert db.get_cauldron_pool(1) == lost
    assert db.get_cauldron_contribution(10,1) == lost
    replay,repeated=pumpkins.smash(1,10,wager,'smash',Rolls())
    assert repeated and replay == result
    assert db.get_player_data(10,1)['candy_in_bucket'] == balance-lost
    assert db.get_cauldron_pool(1) == lost
