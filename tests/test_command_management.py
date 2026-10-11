import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
import discord
import db_utils as db
import potions
import player_state as state
import admin_settings as shared
from cogs.mod_commands.reset import apply_reset, ConfirmReset


def interaction(uid=99,guild_id=1,manage=True):
    return NS(id=1001,user=NS(id=uid,guild_permissions=NS(manage_guild=manage),roles=[]),
              guild_id=guild_id,guild=NS(id=guild_id),response=NS(send_message=AsyncMock(),edit_message=AsyncMock(),send_modal=AsyncMock()))


def snapshot(conn,table):
    return conn.execute('SELECT * FROM '+table).fetchall()


def test_bucket_reset_only_balance_and_guild(database):
    db.update_player_field(10,1,'candy_in_bucket',1200)
    db.update_player_field(10,1,'successful_tricks',12)
    with db.transaction() as conn:potions.grant(conn,1,10,'cunning',2)
    potions.use(1,10,'cunning','use')
    state.freeze(1,20,99,None,'reason','f')
    db.update_player_field(30,1,'active',0)
    tables=['potion_inventory','potion_effects','potion_stats','player_freezes','passive_earnings','returned_potions']
    before={t:snapshot(database,t) for t in tables}
    rows=snapshot(database,'players')
    result=apply_reset(1,'buckets',99,[10,20,30,999])
    assert result==dict(count=2,full=False)
    assert db.get_player_data(10,1)['candy_in_bucket']==50
    assert db.get_player_data(10,1)['successful_tricks']==12
    assert state.freeze_info(1,20) is not None
    assert {t:snapshot(database,t) for t in tables}==before
    after=snapshot(database,'players')
    # Every column except the intended bucket remains bit-for-bit unchanged.
    names=[r[1] for r in database.execute('PRAGMA table_info(players)')]
    bucket=names.index('candy_in_bucket')
    assert [r[:bucket]+r[bucket+1:] for r in rows]==[r[:bucket]+r[bucket+1:] for r in after]
    db.update_player_field(10,1,'candy_in_bucket',80)
    assert apply_reset(1,'buckets',99,[10])==result
    assert db.get_player_data(10,1)['candy_in_bucket']==80


def test_bucket_reset_keeps_veil_and_earnings(database):
    db.update_player_field(10,1,'candy_in_bucket',1000)
    state.buy_protection(1,10,state.quote(1,10,'fixed',5),'veil')
    database.execute('UPDATE passive_earnings SET pending=123 WHERE guild_id=1 AND player_id=10')
    database.commit()
    protection=state.protection_info(1,10)
    apply_reset(1,'bucket',99,[10])
    assert state.protection_info(1,10)==protection
    assert database.execute('SELECT pending FROM passive_earnings WHERE guild_id=1 AND player_id=10').fetchone()==(123,)


def test_full_reset_is_separate(database):
    state.freeze(1,10,99,None,'reason','freeze')
    db.update_player_field(10,1,'successful_tricks',7)
    with db.transaction() as conn:potions.grant(conn,1,10,'ward',2)
    assert apply_reset(1,'full',99,[10],True)['count']==1
    assert state.freeze_info(1,10) is None
    assert potions.inventory(1,10)==({},{})
    assert db.get_player_data(10,1)['active']==1
    assert db.get_player_data(10,1)['successful_tricks']==0
    with pytest.raises(ValueError):apply_reset(1,'bad',99,[10,20],True)


def test_confirmation_requires_owner_guild_current_role(database):
    async def run():
        i=interaction()
        view=ConfirmReset(i,[10,20])
        assert await view.interaction_check(i)
        assert not await view.interaction_check(interaction(uid=88))
        assert not await view.interaction_check(interaction(guild_id=2))
        assert not await view.interaction_check(interaction(manage=False))
        await view.cancel.callback(i)
        assert i.response.edit_message.call_args.kwargs['view'] is None
    asyncio.run(run())


def test_shared_settings_no_unrelated_updates(database):
    import slowmode
    db.set_join_game_msg_settings(1,7,8)
    shared.set_channel(1,'event',NS(id=22,guild=NS(id=1)))
    assert db.get_join_game_msg_settings(1)==(7,8)
    shared.set_pool(1,100)
    slowmode.configure(1,trick=8)
    assert not db.get_game_settings(1)[0]
    shared.set_state(1,False)
    assert db.get_game_settings(1)[0]
    assert slowmode.settings(1)==dict(trick=8,treat=0,smash=0)
    with pytest.raises(ValueError):shared.set_channel(1,'event',NS(id=22,guild=NS(id=2)))
    with pytest.raises(ValueError):shared.set_pool(1,-1)


def test_settings_modals_share_validation(database):
    import slowmode
    async def run():
        i=interaction();view=shared.GameSettingsView(i)
        modal=shared.SettingsModal(view,'slowmode')
        for k,v in modal.fields.items():v._value='-1' if k=='trick' else '15'
        await modal.on_submit(i)
        assert slowmode.settings(1)==dict(trick=0,treat=0,smash=0)
        for v in modal.fields.values():v._value='15'
        await modal.on_submit(i)
        assert slowmode.settings(1)==dict(trick=15,treat=15,smash=15)
        denied=interaction(manage=False)
        for v in modal.fields.values():v._value='22'
        await modal.on_submit(denied)
        assert slowmode.settings(1)['trick']==15
        assert len(shared.BotSettingsView(i).children)==4
    asyncio.run(run())


def test_tree_paths_and_scope(database):
    from cogs.game import Game
    from cogs.mod import Mod
    from cogs.shop import Shop
    from discord.ext import commands
    async def run():
        async with commands.Bot(command_prefix='!',intents=discord.Intents.none()) as bot:
            bot.tree.add_command(Game.game_group)
            bot.tree.add_command(Mod.cmds_group)
            await bot.add_cog(Shop(bot))
            paths={c.qualified_name for c in bot.tree.walk_commands() if not isinstance(c,discord.app_commands.Group)}
            required={'game manage shop','game reset bucket','game reset buckets','game reset player','game candy','game set auto_cauldron','game get auto_cauldron','bot post join','bot post shop','bot set shop_manager_role','bot add role','bot remove join_message'}
            assert required<=paths
            assert not {'bot candy','bot reset player','shop protection','shop manage','bot update channel','bot set role'} & paths
            assert not Game.game_group.get_command('set').get_command('settings').parameters
            bot.tree.copy_global_to(guild=discord.Object(id=1))
            assert {c.qualified_name for c in bot.tree.walk_commands(guild=discord.Object(id=1)) if not isinstance(c,discord.app_commands.Group)}==paths
            for command in bot.tree.get_commands():command.to_dict(bot.tree)
    asyncio.run(run())


def test_role_revocation_removes_access(database):
    from cogs.mod_commands.remove import remove_role
    from utils.messages import default_messages
    async def run():
        i=interaction();i.user.name='Moderator';i.user.mention='<@99>'
        i.guild.get_channel=lambda _:None
        i.channel=NS(send=AsyncMock())
        i.client=NS(message_loader=default_messages())
        db.set_role_by_guild(1,555)
        await remove_role.callback(i,NS(id=555,name='Mods'))
        assert db.fetch_roles_by_guild(1)==[]
    asyncio.run(run())


def test_help_and_settings_fit_discord_limits(database):
    from cogs.help import make_embed,PLAYER_TOPICS,MOD_TOPICS
    from utils.messages import default_messages
    import json
    import re
    messages=default_messages()
    for topic in PLAYER_TOPICS+MOD_TOPICS:
        embed=make_embed(messages,topic)
        assert len(embed)<=6000
        assert all(len(f.value)<=1024 for f in embed.fields)
    content=json.dumps(messages.messages)
    for obsolete in ('/game manage shopr_role','/shop protection','/shop manage','/bot update channel','/bot send join_game_msg'):
        assert obsolete not in content
    assert len(shared.summary(1))<=2000


def test_post_move_and_remove_invitation(database):
    from cogs.mod_commands.send import set_join_game_msg
    from cogs.mod_commands.remove import remove_join_message
    from utils.messages import default_messages
    async def run():
        i=interaction();i.client=NS(message_loader=default_messages());i.response.defer=AsyncMock();i.response.is_done=lambda:True;i.followup=NS(send=AsyncMock())
        old=NS(id=123,delete=AsyncMock())
        new=NS(id=456,add_reaction=AsyncMock(),delete=AsyncMock(),jump_url='https://discord.com/new')
        channels={10:NS(id=10,fetch_message=AsyncMock(return_value=old)),20:NS(id=20,send=AsyncMock(return_value=new),fetch_message=AsyncMock(return_value=new))}
        i.guild.get_channel=lambda cid:channels.get(cid)
        db.set_join_game_msg_settings(1,123,10)
        await set_join_game_msg.callback(i,channels[20])
        assert db.get_join_game_msg_settings(1)==(456,20)
        old.delete.assert_awaited_once()
        await remove_join_message.callback(i)
        new.delete.assert_awaited_once()
        assert db.get_join_game_msg_settings(1)==(None,None)
    asyncio.run(run())
