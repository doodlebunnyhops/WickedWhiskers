import asyncio
import sqlite3
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
import discord
import auto_cauldron as auto
import db_utils as db
import player_state as state
from utils.cauldron import award_pool,CauldronError
from utils.messages import default_messages


def guild(allowed=True):
    channel=NS(permissions_for=lambda _:NS(view_channel=True,send_messages=allowed,embed_links=True,attach_files=True),send=AsyncMock())
    return NS(id=1,me=object(),get_channel=lambda _:channel,get_member=lambda _:None)


def enable(**kwargs):
    db.set_cauldron_pool(1,100)
    return auto.configure(1,now=1000,enabled=True,trigger='interval',interval_minutes=10,**kwargs)


def test_defaults_and_required_validation(database):
    assert not auto.settings(1)['enabled']
    assert not auto.due(1,10000)
    for updates in [dict(enabled=True),dict(enabled=True,trigger='threshold'),dict(interval_minutes=0),dict(minimum_gap_minutes=-1),dict(witch='nobody')]:
        with pytest.raises(ValueError):auto.configure(1,**updates)
    assert not auto.settings(1)['enabled']
    auto.configure(1,enabled=False,trigger='threshold')
    assert auto.settings(1)['trigger']=='threshold'


def test_missing_or_denied_channel_cannot_enable(database):
    with pytest.raises(ValueError):auto.configure(1,enabled=True,interval_minutes=5,guild=guild(False))
    with pytest.raises(ValueError):auto.configure(1,enabled=True,interval_minutes=5,guild=NS(id=1,get_channel=lambda _:None))
    db.set_event_channel(1,999)
    auto.configure(1,enabled=True,interval_minutes=5,guild=guild())
    assert auto.settings(1)['enabled']


def test_interval_and_manual_cast_reset_timer(database):
    enable()
    assert not auto.due(1,1599)
    assert auto.due(1,1600)
    award_pool(1,'manual',99,'luna','many',now=1500)
    db.set_cauldron_pool(1,100)
    assert not auto.due(1,2099)
    assert auto.due(1,2100)
    award_pool(1,'manual',99,'luna','many',now=2000)
    assert auto.settings(1)['last_cast']==1500 # replay does not move the schedule


@pytest.mark.parametrize('trigger', ['threshold','either'])
def test_threshold_and_gap(database,trigger):
    auto.configure(1,now=1000,enabled=True,trigger=trigger,candy_threshold=100,interval_minutes=60)
    db.set_cauldron_pool(1,99)
    assert not auto.due(1,1001)
    db.set_cauldron_pool(1,100)
    assert auto.due(1,1001)
    assert auto.claim(1,'first',99,now=1001)['amount']==100
    db.set_cauldron_pool(1,100)
    assert auto.claim(1,'race',99,now=1001) is None
    assert not auto.due(1,1300)
    assert auto.due(1,1301)


def test_pause_empty_ineligible_preserve_clock(database):
    enable()
    db.set_game_disabled(1,True)
    assert auto.claim(1,'paused',99,now=2000) is None
    db.set_game_disabled(1,False)
    database.execute('UPDATE players SET active=0 WHERE guild_id=1');database.commit()
    with pytest.raises(CauldronError):auto.claim(1,'empty',99,now=2000)
    assert db.get_cauldron_pool(1)==100
    assert auto.settings(1)['last_cast'] is None
    database.execute('UPDATE players SET active=1 WHERE guild_id=1');database.commit()
    result=auto.claim(1,'ready',99,now=2000)
    assert result['amount']==100
    assert auto.claim(1,'empty-pool',99,now=10000) is None


def test_disable_preserves_config_and_reenable_starts_interval(database):
    enable(witch='raven',winners='many')
    auto.configure(1,enabled=False,now=1100)
    assert not auto.due(1,9000)
    assert auto.settings(1)['witch']=='raven'
    auto.configure(1,enabled=True,now=9000)
    assert not auto.due(1,9599)
    assert auto.due(1,9600)


def test_restart_one_overdue_cast_and_persistence(database,tmp_path):
    enable(witch='luna',winners='one')
    path=tmp_path/'restart.db'
    saved=sqlite3.connect(path);database.backup(saved);saved.close()
    original=db.conn
    db.conn=sqlite3.connect(path)
    try:
        db.initialize_database()
        first=auto.claim(1,'restart',99,now=100000)
        assert first['witch']=='luna' and len(first['awards'])==1
        db.set_cauldron_pool(1,100)
        assert auto.claim(1,'catchup',99,now=100000) is None
        assert auto.settings(1)['last_cast']==100000
    finally:
        db.close_db_connection();db.conn=original


def test_award_rollback_does_not_advance_schedule(database,monkeypatch):
    enable()
    original=auto.mark_cast
    def fail(*args):
        original(*args)
        raise sqlite3.OperationalError('failure')
    monkeypatch.setattr(auto,'mark_cast',fail)
    with pytest.raises(sqlite3.OperationalError):auto.claim(1,'broken',99,now=2000)
    assert db.get_cauldron_pool(1)==100
    assert auto.settings(1)['last_cast'] is None
    assert sum(r[0] for r in database.execute('SELECT candy_in_bucket FROM players WHERE guild_id=1'))==250


def test_automatic_includes_veil_but_respects_freeze_and_guild(database,monkeypatch):
    enable(witch='raven',winners='many')
    state.freeze(1,10,99,None,'reason','f')
    db.update_player_field(20,1,'candy_in_bucket',1000)
    state.buy_protection(1,20,state.quote(1,20,'fixed',5),'veil')
    monkeypatch.setattr(auto.random,'randint',lambda low,high:high)
    result=auto.claim(1,'eligible',99,now=2000)
    assert {r['player_id'] for r in result['awards']}=={20,30,40,50}
    assert sum(r['amount'] for r in result['awards'])==100
    assert sum(r[0] for r in database.execute('SELECT candy_in_bucket FROM players WHERE guild_id=2'))==250


def test_random_modes_and_witches(database,monkeypatch):
    enable()
    seen=[]
    def choose(options):
        seen.append(options)
        return options[-1]
    monkeypatch.setattr(auto.random,'choice',choose)
    result=auto.claim(1,'random',99,now=2000)
    assert result['witch']=='raven' and len(result['awards'])>=2
    assert ('luna','raven') in seen and ('one','many') in seen


def test_poll_failed_post_never_pays_twice(database):
    from cogs.auto_cauldron import AutoCauldron
    enable(witch='luna',winners='many')
    db.set_event_channel(1,999)
    g=guild();channel=g.get_channel(999)
    channel.send.side_effect=discord.Forbidden(NS(status=403,reason='Forbidden'),'denied')
    bot=NS(get_guild=lambda _:g,user=NS(id=99),message_loader=default_messages())
    async def run():
        cog=AutoCauldron(bot)
        await cog.poll()
        assert channel.send.await_count==1
        assert db.get_cauldron_pool(1)==0
        await cog.poll()
        assert channel.send.await_count==1
    asyncio.run(run())
    assert database.execute('SELECT COUNT(*) FROM cauldron_event WHERE guild_id=1').fetchone()[0]==1


def test_auto_ui_same_validation_and_permission(database):
    from modals.auto_cauldron import AutoView,AutoModal
    from test_command_management import interaction
    async def run():
        i=interaction();i.guild=guild();db.set_event_channel(1,999)
        view=AutoView(i)
        view.pending=dict(trigger='either',witch='luna',winners='many')
        modal=AutoModal(view)
        for key,value in dict(interval_minutes='10',candy_threshold='100',minimum_gap_minutes='5').items():modal.fields[key]._value=value
        await modal.on_submit(i)
        assert auto.settings(1)['trigger']=='either'
        assert not auto.settings(1)['enabled']
        await view.toggle.callback(i)
        assert auto.settings(1)['enabled']
        revoked=interaction(manage=False)
        assert not await view.interaction_check(revoked)
        modal.fields['candy_threshold']._value='900'
        await modal.on_submit(revoked)
        assert auto.settings(1)['candy_threshold']==100
    asyncio.run(run())


def test_only_veiled_player_can_trigger_auto_draw(database):
    enable(witch='luna',winners='one')
    db.update_player_field(10,1,'candy_in_bucket',1000)
    state.buy_protection(1,10,state.quote(1,10,'fixed',5),'veil')
    database.execute('UPDATE players SET active=0 WHERE guild_id=1 AND player_id<>10')
    database.commit()
    assert not db.get_active_players_by_guild(1)  # Still unavailable to other witch gifts.
    assert [r[0] for r in db.get_cauldron_players(1)]==[10]
    result=auto.claim(1,'veil-only',99,now=2000)
    assert result['awards']==[dict(player_id=10,amount=100)]
    assert state.protection_info(1,10)  # The reward does not consume/end the Veil.
