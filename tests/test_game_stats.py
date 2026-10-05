import asyncio
from types import SimpleNamespace as NS
import pytest
import db_utils as db
import potions
import game_stats as stats
import player_state as state
from utils import player, potion_gameplay as perks, cauldron
from utils.player_stats import player_stats_embeds
from test_more_potions import interaction, member, activate, resolve


def test_luna_credit_once_and_failed_use_unchanged(database):
    with db.transaction() as conn:potions.grant(conn,1,10,'luna',2)
    db.update_player_field(10,1,'total_candy_stolen',15)
    result=potions.use(1,10,'luna','summon',{10,20,30,40},now=100)
    potions.use(1,10,'luna','summon',{10,20,30,40},now=101)
    with pytest.raises(potions.PotionCooldownError):potions.use(1,10,'luna','cooldown',{10,20},now=101)
    data=db.get_player_data(10,1)
    assert len(result['recipients'])==3
    assert (data['treats_given'],data['total_candy_given'])==(1,15)
    assert player.calculate_sweetness(data['total_candy_given'],data['total_candy_stolen'])==.5
    assert dict(cauldron.candidates(db.get_active_players_by_guild(1),'luna','normal'))[10]==2
    assert stats.totals(1,10)==dict(activated=1,gifted=15,triggered=1)
    assert dict(db.get_leaderboard_query('lunas_favorites',1))[10]==15


def test_purchases_gifts_replay_and_rollback(database):
    with db.transaction() as conn:potions.grant(conn,1,10,'ward',3)
    assert not stats.totals(1,10)
    potions.purchase(1,10,'ward',2,5,'buy')
    potions.purchase(1,10,'ward',2,5,'buy')
    assert stats.potion_details(1,10)['ward']==dict(purchased=2,spent=10)
    with pytest.raises(RuntimeError):
        with db.transaction() as conn:
            potions.purchase(1,10,'ward',1,5,'rolledback')
            raise RuntimeError()
    assert stats.totals(1,10)==dict(purchased=2,spent=10)
    assert not stats.totals(2,10)


def test_ward_defense_attempts_and_returned_bottle(database,monkeypatch):
    activate('ward',20)
    caller=resolve(monkeypatch)
    asyncio.run(player.player_trick(caller,member(20)))
    assert stats.totals(1,10)==dict(trick_attempts=1,blocked_attempts=1)
    assert stats.totals(1,20)==dict(activated=1,triggered=1,defended=1)
    assert dict(db.get_leaderboard_query('untouchable',1))[20]==1
    activate('cunning')
    state.freeze(1,10,99,5,'pause','freeze')
    state.unfreeze(1,10,99,'thaw')
    potions.use(1,10,'cunning','again')
    assert stats.totals(1,10).get('purchased',0)==0
    assert stats.totals(1,10)['activated']==2
    assert stats.totals(1,10).get('triggered',0)==0


def test_mirror_redirect_counts_owner_once(database,monkeypatch):
    activate('mirror',20)
    monkeypatch.setattr(perks,'choose_redirect',lambda options:member(30))
    monkeypatch.setattr(perks.random,'random',lambda:0)
    monkeypatch.setattr(perks.random,'randint',lambda a,b:3)
    resolve(monkeypatch)
    assert stats.totals(1,20)==dict(activated=1,triggered=1,defended=1)
    assert stats.totals(1,10)==dict(trick_attempts=1,redirected_attempts=1)
    assert db.get_player_data(10,1)['successful_tricks']==1


def test_boards_filter_before_limit_keep_protected_and_expired_freezes(database,monkeypatch):
    monkeypatch.setattr(state.time,'time',lambda:1000)
    db.update_player_field(10,1,'candy_in_bucket',1000)
    db.update_player_field(20,1,'active',0)
    state.freeze(1,30,99,None,'pause','freeze30')
    state.freeze(1,40,99,1,'short','freeze40',now=900)
    state.buy_protection(1,10,state.quote(1,10,'fixed',5),'veil')
    rows=db.get_leaderboard_query('candy_hoarders',1,3)
    assert {uid for uid,_ in rows}=={10,40,50}
    db.update_player_field(50,1,'total_candy_lost',9999)
    db.update_player_field(40,1,'total_candy_spent_on_pumpkins',20)
    assert db.get_leaderboard_query('highest_risk_takers',1)[0]==(40,20)


def test_protection_time_refund_expiry_and_reset(database,monkeypatch):
    now=[1000];monkeypatch.setattr(state.time,'time',lambda:now[0])
    db.update_player_field(10,1,'candy_in_bucket',2000)
    state.buy_protection(1,10,state.quote(1,10,'budget',25),'veil')
    now[0]=1060
    assert stats.protection_seconds(1,10)==60
    refund=state.end_protection(1,10,'stop')['refund']
    assert stats.totals(1,10)['spent']==75-refund
    assert stats.protection_seconds(1,10)==60
    now[0]=5000
    state.buy_protection(1,10,state.quote(1,10,'fixed',5),'veil2')
    now[0]=9000
    assert stats.protection_seconds(1,10)==360
    state.buy_protection(1,10,state.quote(1,10,'fixed',5),'veil3')
    assert stats.protection_seconds(1,10)==360
    assert stats.totals(1,10)['purchased']==3
    assert stats.totals(1,10).get('triggered',0)==0
    db.reset_player_data(10,1)
    assert stats.totals(1,10)=={} and stats.protection_seconds(1,10)==0


def test_cauldron_contributions_match_actual_trick_loss(database,monkeypatch):
    rolls=iter([0,0]);monkeypatch.setattr(player.random,'random',lambda:next(rolls))
    monkeypatch.setattr(player.random,'randint',lambda a,b:8)
    resolve(monkeypatch)
    assert db.get_cauldron_pool(1)==16
    assert dict(db.get_leaderboard_query('cauldron_contributors',1))[10]==8
    assert db.get_cauldron_contribution(20,1)==8


def test_stats_render_real_inventory_and_new_counters(database):
    potions.purchase(1,10,'ward',2,5,'buy')
    caller=interaction()
    embeds=player_stats_embeds(caller,member(10),'all')
    assert len(embeds)==3 and sum(map(len,embeds))<=6000
    text=' '.join(str(e.to_dict()) for e in embeds)
    assert 'Message not found' not in text
    assert 'Bought: 2' in text and 'Inventory: 2' in text
    assert 'before potion effects' in text
    state.leave(1,10)
    assert stats.totals(1,10)=={}
