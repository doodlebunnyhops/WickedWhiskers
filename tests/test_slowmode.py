import asyncio
import sqlite3
import pytest
import db_utils as db
import slowmode
from utils import player,pumpkins
from test_more_potions import interaction,member
from unittest.mock import AsyncMock


def test_defaults_validation_and_independent_clocks(database):
    assert slowmode.settings(1)==dict(trick=0,treat=0,smash=0)
    slowmode.configure(1,trick=10,treat=20,smash=30)
    with db.transaction() as conn:
        slowmode.mark(conn,1,10,'trick',100)
        with pytest.raises(slowmode.SlowmodeError,match='<t:110:R>'):slowmode.check(conn,1,10,'trick',109)
        slowmode.check(conn,1,10,'trick',110)
        slowmode.check(conn,1,10,'treat',101)
        slowmode.check(conn,1,20,'trick',101)
        slowmode.check(conn,2,10,'trick',101)
    for bad in [-1,True,1.5,86401]:
        with pytest.raises(ValueError):slowmode.configure(1,trick=bad)
    slowmode.configure(1,trick=0)
    assert slowmode.settings(1)['treat']==20
    slowmode.configure(1,trick=10)
    slowmode.check(database,1,10,'trick',101)


def test_restart_and_rollback(database,tmp_path):
    slowmode.configure(1,trick=10)
    with db.transaction() as conn:slowmode.mark(conn,1,10,'trick',100)
    path=tmp_path/'persist.db';backup=sqlite3.connect(path);database.backup(backup);backup.close()
    reopened=sqlite3.connect(path)
    assert reopened.execute('SELECT used_at FROM action_last_used').fetchone()==(100,)
    reopened.close()
    with pytest.raises(RuntimeError):
        with db.transaction() as conn:
            slowmode.mark(conn,1,20,'trick',100)
            raise RuntimeError()
    slowmode.check(database,1,20,'trick',101)


@pytest.mark.parametrize('action',['trick','treat','smash'])
def test_shared_gameplay_gate_no_extra_changes(database,monkeypatch,action):
    slowmode.configure(1,**{action:10})
    monkeypatch.setattr(slowmode.time,'time',lambda:100)
    monkeypatch.setattr(player.random,'random',lambda:.8)
    monkeypatch.setattr(player,'post_to_target_channel',AsyncMock())
    def run(request):
        caller=interaction();caller.id=request
        if action=='trick':asyncio.run(player.player_trick(caller,member(20)))
        elif action=='treat':player.give_treat(caller,member(20),2)
        else:pumpkins.smash(1,10,2,request)
        return caller
    run(100)
    original=db.get_player_data(10,1).copy()
    run(100) # Receipt lookup precedes cooldown; cannot pay twice.
    if action=='smash':
        with pytest.raises(slowmode.SlowmodeError):run(101)
    else:
        caller=run(101)
        if action=='trick':caller.response.send_message.assert_awaited_once()
    assert db.get_player_data(10,1)==original
    assert database.execute('SELECT used_at FROM action_last_used WHERE action=?',(action,)).fetchone()==(100,)
    monkeypatch.setattr(slowmode.time,'time',lambda:110)
    run(102)
    assert database.execute('SELECT used_at FROM action_last_used WHERE action=?',(action,)).fetchone()==(110,)


def test_invalid_request_does_not_start_timer(database,monkeypatch):
    slowmode.configure(1,trick=10,treat=10,smash=10)
    asyncio.run(player.player_trick(interaction(),member(10)))
    caller=interaction();caller.id=988
    player.give_treat(caller,member(20),9999)
    with pytest.raises(pumpkins.PumpkinError):pumpkins.smash(1,10,9999,998)
    assert database.execute('SELECT COUNT(*) FROM action_last_used').fetchone()[0]==0


def test_command_has_moderator_check_and_bounds():
    from importlib import import_module
    command=import_module('cogs.game_commands.set').set_slowmode
    assert command.checks
    assert [p.name for p in command.parameters]==['trick','treat','smash']
    assert all(p.min_value==0 and p.max_value==86400 for p in command.parameters)
