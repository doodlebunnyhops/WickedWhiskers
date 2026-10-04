import asyncio
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import sqlite3
import discord
import pytest
import db_utils as db
from utils.mod_candy import adjust, CandyError
from utils.cauldron import candidates
from utils.messages import MessageLoader
from cogs.mod_commands import candy as command


def run(action='give', amount=10, request='one', guild=1):
    return adjust(guild,20,10,action,amount,False,request)


def test_only_target_balance_changes(database):
    before=database.execute('SELECT * FROM players ORDER BY guild_id,player_id').fetchall()
    names=[row[1] for row in database.execute('PRAGMA table_info(players)')]
    idx=names.index('candy_in_bucket')
    weights={(w,o):candidates(db.get_active_players_by_guild(1),w,o) for w,o in [('luna','normal'),('luna','special'),('raven','normal'),('raven','rage')]}
    result,_=run()
    assert 'balance' not in result
    after=database.execute('SELECT * FROM players ORDER BY guild_id,player_id').fetchall()
    for original,updated in zip(before,after):
        if original[names.index('guild_id')]==1 and original[names.index('player_id')]==10:
            expected=list(original);expected[idx]+=10
            assert tuple(expected)==updated
        else: assert original==updated
    for (w,o),value in weights.items(): assert candidates(db.get_active_players_by_guild(1),w,o)==value
    assert db.get_cauldron_pool(1)==0
    assert db.get_cauldron_contribution(10,1)==0


def test_take_exact_balance_and_replay(database):
    first,_=run('take',50)
    assert db.get_player_data(10,1)['candy_in_bucket']==0
    assert run('take',50)==(first,True)
    assert run('take',50,guild=2)[1] is False


@pytest.mark.parametrize('action,amount',[('give',0),('take',-1),('give',True),('give',1.2),('take',51),('invalid',5)])
def test_invalid_adjustment(database,action,amount):
    with pytest.raises(CandyError):run(action,amount)
    assert db.get_player_data(10,1)['candy_in_bucket']==50


def test_missing_and_overflow(database):
    with pytest.raises(CandyError):adjust(1,20,999,'give',1,True,'missing')
    with pytest.raises(CandyError):run('give',2**63)


def test_atomic_receipt_failure(database):
    database.execute("CREATE TRIGGER reject_mod BEFORE INSERT ON potion_actions BEGIN SELECT RAISE(ABORT,'test'); END")
    database.commit()
    with pytest.raises(sqlite3.Error):run()
    assert db.get_player_data(10,1)['candy_in_bucket']==50


def caller():
    channel=NS(send=AsyncMock(),permissions_for=lambda me:NS(view_channel=True,send_messages=True,embed_links=True))
    guild=NS(id=1,me=NS(),get_channel=lambda ident:channel)
    interaction=NS(id=321,guild=guild,user=NS(id=20,mention='<@20>'),client=NS(message_loader=MessageLoader(str(Path(__file__).resolve().parents[1]/'discord-bot/utils/messages.json'))),response=NS(defer=AsyncMock()),followup=NS(send=AsyncMock()))
    member=NS(id=10,mention='<@10>',guild=guild,bot=False)
    return interaction,member,channel


@pytest.mark.parametrize('named',[True,False])
def test_announcement_privacy_and_duplicate(database,monkeypatch,named):
    monkeypatch.setattr(command,'has_role_or_permission',lambda *args:True)
    interaction,member,channel=caller()
    args=(interaction,member,NS(value='give'),10,named)
    asyncio.run(command.candy.callback(*args))
    text=channel.send.call_args.kwargs['embed'].description
    assert ('<@20>' in text)==named
    assert '<@10>' in text and '10 candy' in text
    assert '60' not in text and 'bucket' not in text.lower()
    asyncio.run(command.candy.callback(*args))
    assert channel.send.await_count==1
    assert db.get_player_data(10,1)['candy_in_bucket']==60


@pytest.mark.parametrize('case',['denied','missing_channel','permissions'])
def test_guard_blocks_mutation(database,monkeypatch,case):
    monkeypatch.setattr(command,'has_role_or_permission',lambda *args:case!='denied')
    interaction,member,channel=caller()
    if case=='missing_channel':interaction.guild.get_channel=lambda ident:None
    if case=='permissions':channel.permissions_for=lambda me:NS(view_channel=True,send_messages=False,embed_links=True)
    asyncio.run(command.candy.callback(interaction,member,NS(value='give'),10,False))
    assert db.get_player_data(10,1)['candy_in_bucket']==50
    channel.send.assert_not_awaited()


def test_announcement_failure_does_not_repeat_payment(database,monkeypatch):
    monkeypatch.setattr(command,'has_role_or_permission',lambda *args:True)
    interaction,member,channel=caller()
    channel.send.side_effect=discord.Forbidden(NS(status=403,reason='Forbidden'),'Forbidden')
    args=(interaction,member,NS(value='give'),10,False)
    asyncio.run(command.candy.callback(*args))
    assert 'saved' in interaction.followup.send.call_args.args[0]
    asyncio.run(command.candy.callback(*args))
    assert db.get_player_data(10,1)['candy_in_bucket']==60
    assert channel.send.await_count==1
