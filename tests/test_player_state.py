import asyncio
import sqlite3
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
import discord
import db_utils as db
import potions
import player_state as state
from utils import player, pumpkins, cauldron
from modals.protection import ProtectionModal, ProtectionSettings, ProtectionCheckout
from cogs.participation import moderator_change, Participation, reconcile_members


@pytest.fixture
def clock(monkeypatch):
    now=[1000]
    monkeypatch.setattr(state.time,'time',lambda:now[0])
    return now


def fund(uid=10,amount=1000):
    db.update_player_field(uid,1,'candy_in_bucket',amount)


def protect(mode='fixed',units=5,uid=10,request='veil'):
    return state.buy_protection(1,uid,state.quote(1,uid,mode,units),request)


def balance(uid=10):
    return db.get_player_data(uid,1)['candy_in_bucket']


def caller(uid=10,moderator=True):
    channel=NS(send=AsyncMock(),permissions_for=lambda _:NS(view_channel=True,send_messages=True,embed_links=True))
    guild=NS(id=1,me=NS(),get_channel=lambda _:channel,chunked=True)
    def member(i):return NS(id=i,mention=f'<@{i}>',name=str(i),display_name=str(i),bot=False,guild=guild,guild_permissions=NS(manage_guild=moderator),roles=[])
    guild.get_member=member
    guild.members=[member(i) for i in (10,20,30,40,50)]
    return NS(id=991,guild=guild,guild_id=1,user=member(uid),client=NS(message_loader=state.loader()),delete_original_response=AsyncMock(),edit_original_response=AsyncMock(),response=NS(send_message=AsyncMock(),defer=AsyncMock(),is_done=lambda:True,edit_message=AsyncMock()),followup=NS(send=AsyncMock())),channel


def test_freeze_returns_remaining_charges_once(database,clock):
    with db.transaction() as conn:potions.grant(conn,1,10,'cunning',2)
    potions.use(1,10,'cunning','use')
    with db.transaction() as conn:potions.consume_charge(conn,1,10,'cunning')
    first,replayed=state.freeze(1,10,20,5,'take a break','freeze')
    assert not replayed and first['until']==1300
    assert potions.inventory(1,10)==({'cunning':2},{})
    assert database.execute('SELECT charges FROM returned_potions').fetchone()[0]==2
    assert state.freeze(1,10,20,5,'take a break','freeze')[1]
    with pytest.raises(state.StateError):state.freeze(1,10,20,10,'new','other')
    state.freeze(1,10,20,10,'new','update',update=True)
    assert database.execute('SELECT COUNT(*) FROM returned_potions').fetchone()[0]==1
    state.unfreeze(1,10,20,'thaw')
    potions.use(1,10,'cunning','reuse')
    assert potions.inventory(1,10)==({'cunning':1},{'cunning':2})


def test_freeze_expiry_reason_and_reset(database,clock):
    state.freeze(1,10,20,1,'private reason','f')
    with pytest.raises(state.StateError,match='private reason') as err:state.require(1,10)
    assert '<t:1060:F>' in str(err.value) and '<t:1060:R>' in str(err.value)
    assert not state.visible(1,10)
    clock[0]=1060
    assert state.visible(1,10) and not db.is_player_frozen(10,1)
    state.freeze(1,10,20,None,'indefinite','f2')
    with db.transaction():db.reset_player_data(10,1)
    assert state.freeze_info(1,10) is None
    assert balance()==50


@pytest.mark.parametrize('mode,units,total',[('fixed',10,100),('budget',50,100)])
def test_protection_cost_eligibility_and_no_stats(database,clock,mode,units,total):
    fund()
    before=db.get_player_data(10,1)
    result=protect(mode,units)
    assert balance()==1000-total and result['end']==1600
    after=db.get_player_data(10,1)
    before.pop('candy_in_bucket');after.pop('candy_in_bucket');assert before==after
    assert db.get_cauldron_pool(1)==0
    assert 10 not in [p[0] for p in db.get_active_players_by_guild(1)]
    with pytest.raises(state.StateError):state.require(1,10,'social')
    with pytest.raises(state.StateError):potions.use(1,10,'ward','blocked')
    potions.purchase(1,10,'ward',1,5,'purchase')
    assert potions.inventory(1,10)[0]['ward']==1
    assert not state.protection_info(2,10)
    clock[0]=1600
    assert state.visible(1,10)
    with pytest.raises(state.StateError,match='cooldown'):protect(request='early')
    clock[0]=5200
    protect(request='later')


@pytest.mark.parametrize('elapsed,refund',[(0,45),(1,45),(59,45),(60,40),(61,40),(599,0)])
def test_budget_started_minute_billing_and_replay(database,clock,elapsed,refund):
    fund();protect('budget',50)
    clock[0]+=elapsed
    result=state.end_protection(1,10,'stop')
    assert result['refund']==refund and balance()==900+refund
    assert state.end_protection(1,10,'stop')==result
    assert database.execute('SELECT available_at FROM protection_cooldowns').fetchone()[0]==clock[0]+3600


def test_fixed_early_stop_has_no_refund(database,clock):
    fund();protect('fixed',10)
    assert state.end_protection(1,10,'stop')['refund']==0 and balance()==900
    assert state.credits(1,10)==0


@pytest.mark.parametrize('mode,units',[('fixed',10),('budget',50)])
def test_freeze_returns_veil_and_unspent_time(database,clock,mode,units):
    fund();protect(mode,units)
    clock[0]=1060
    state.freeze(1,10,20,None,'reason','f')
    assert balance()==940 and state.credits(1,10)==1
    assert state.protection_info(1,10) is None
    state.freeze(1,10,20,None,'updated','f2',update=True)
    assert balance()==940 and state.credits(1,10)==1
    state.unfreeze(1,10,20,'u')
    clock[0]+=3600
    q=state.quote(1,10,'fixed',5)
    assert q['fee']==0 and q['total']==25
    state.buy_protection(1,10,q,'reuse')
    assert state.credits(1,10)==0 and balance()==915


def test_price_changes_do_not_reprice_existing_spell(database,clock):
    fund();q=state.quote(1,10,'budget',50)
    protect('budget',50)
    cfg=dict(state.DEFAULTS,rate=20,cooldown=5)
    state.configure(1,20,cfg)
    assert state.end_protection(1,10,'stop')['refund']==45
    assert database.execute('SELECT available_at FROM protection_cooldowns').fetchone()[0]==4600
    assert state.settings(2)==state.DEFAULTS
    clock[0]=4600
    with pytest.raises(state.StateError,match='changed'):state.buy_protection(1,10,q,'stale')


def test_rejected_checkout_and_duplicate_never_charge(database,clock):
    fund();q=state.quote(1,10,'fixed',5)
    first=state.buy_protection(1,10,q,'buy')
    before=balance()
    assert state.buy_protection(1,10,q,'buy')==first and balance()==before
    with pytest.raises(state.StateError):state.buy_protection(1,10,q,'other')
    assert balance()==before


def test_atomic_purchase_failure(database,clock):
    fund();database.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON potion_actions BEGIN SELECT RAISE(ABORT,'test'); END");database.commit()
    with pytest.raises(sqlite3.Error):protect()
    assert balance()==1000 and state.protection_info(1,10) is None
    assert database.execute('SELECT COUNT(*) FROM protection_cooldowns').fetchone()[0]==0


def test_leave_wipes_data_but_preserves_freeze_and_cooldowns(database,clock):
    fund();protect('budget',50)
    state.freeze(1,10,20,None,'persistent','freeze')
    assert state.leave(1,10)
    assert not state.leave(1,10)
    assert balance()==0 and state.credits(1,10)==0 and potions.inventory(1,10)==({},{})
    assert state.freeze_info(1,10)['reason']=='persistent'
    assert database.execute('SELECT available_at FROM protection_cooldowns').fetchone()[0]==4600
    with pytest.raises(state.StateError,match='frozen'):state.join(1,10)
    state.unfreeze(1,10,20,'u')
    with pytest.raises(state.StateError,match='fresh start'):state.join(1,10)
    clock[0]=4600
    state.join(1,10)
    assert balance()==50
    with pytest.raises(state.StateError):state.join(1,10)
    assert balance()==50


def test_server_departure_and_reconciliation(database,clock):
    interaction,_=caller()
    state.freeze(1,10,20,None,'freeze','f')
    cog=Participation(NS())
    asyncio.run(cog.on_member_remove(interaction.user))
    assert balance()==0 and state.freeze_info(1,10)
    guild=NS(id=1,chunked=True,members=[NS(id=uid) for uid in (30,40,50)])
    asyncio.run(reconcile_members(guild))
    assert not db.is_player_active(20,1)
    assert db.is_player_active(30,1)


def test_restart_persists_freeze_protection_and_delay(database,clock,tmp_path):
    fund();protect()
    state.freeze(1,20,30,None,'persistent','f')
    state.leave(1,30)
    snapshot=sqlite3.connect(tmp_path/'restart.db');database.backup(snapshot)
    db.conn=snapshot
    assert state.protection_info(1,10)['end']==1300
    assert state.freeze_info(1,20)['reason']=='persistent'
    with pytest.raises(state.StateError):state.join(1,30)
    snapshot.close();db.conn=database


def test_social_paths_block_without_spending_charges(database,clock):
    fund()
    with db.transaction() as conn:potions.grant(conn,1,10,'cunning')
    potions.use(1,10,'cunning','c')
    protect()
    interaction,_=caller()
    responses=player._TrickResponses()
    player._resolve_trick(interaction,interaction.guild.get_member(20),responses)
    assert len(responses.messages)==1 and responses.messages[0][0]=='personal'
    assert player.give_treat(interaction,interaction.guild.get_member(20),5)[0] is None
    assert potions.inventory(1,10)[1]['cunning']==3
    other,_=caller(20)
    other.id=992
    assert player.give_treat(other,other.guild.get_member(10),5)[0] is None
    result=potions.consume_charge(database,1,10,'cunning')
    assert not result


def test_luna_and_cauldron_skip_hidden_and_frozen(database,clock):
    fund();protect()
    state.freeze(1,20,30,None,'private','f')
    with db.transaction() as conn:potions.grant(conn,1,30,'luna')
    result=potions.use(1,30,'luna','luna',{10,20,30,40,50})
    assert set(result['recipients'])=={40,50}
    db.set_cauldron_pool(1,100)
    result,_=cauldron.award_pool(1,'cast',50,'luna','many')
    assert not {10,20}&{x['player_id'] for x in result['awards']}


def test_protected_pumpkin_still_funds_pool(database,clock,monkeypatch):
    fund();protect()
    class Rolls:
        values=iter([.9,0])
        def random(self):return next(self.values)
    result,_=pumpkins.smash(1,10,10,'pumpkin',Rolls())
    assert result['protected'] and result['contribution']==20
    assert db.get_cauldron_pool(1)==20
    msg=state.loader().get_message('smash_pumpkin','event_messages','hidden_raven',user='PLAYER',candy_amount=20)
    assert 'cauldron' in msg and ('lost sweets' in msg or 'already lost' in msg)


def test_freeze_public_privacy_and_permission(database,clock):
    db.set_event_channel(1,99)
    interaction,channel=caller(20)
    asyncio.run(moderator_change(interaction,interaction.guild.get_member(10),60,'PRIVATE REASON'))
    description=channel.send.call_args.kwargs['embed'].description
    assert '<@10>' in description and '<@20>' not in description and 'PRIVATE' not in description and '60' not in description
    denied,channel=caller(30,False)
    asyncio.run(moderator_change(denied,denied.guild.get_member(40)))
    assert not state.freeze_info(1,40)
    channel.send.assert_not_awaited()


def test_modal_components_and_new_commands(database,clock):
    async def run():
        for modal in (ProtectionModal(10,1),ProtectionSettings(10,1)):
            payload=modal.to_dict()
            assert len(payload['components'])<=5
        from cogs.game import Game
        assert Game.game_group.get_command('freeze')
        assert Game.game_group.get_command('unfreeze')
    asyncio.run(run())


def test_frozen_action_paths_have_private_details_and_no_game_changes(database,clock):
    state.freeze(1,10,20,5,'test reason','freeze')
    interaction,_=caller()
    before=balance()
    asyncio.run(player.player_trick(interaction,interaction.guild.get_member(20)))
    assert 'test reason' in interaction.response.send_message.call_args.args[0]
    assert interaction.response.send_message.call_args.kwargs['ephemeral']
    asyncio.run(player.player_treat(interaction,interaction.guild.get_member(20),5))
    assert 'test reason' in interaction.response.send_message.call_args.args[0]
    asyncio.run(player.smash_pumpkin(interaction,5))
    assert 'test reason' in interaction.followup.send.call_args.args[0]
    with pytest.raises(state.StateError,match='test reason'):potions.purchase(1,10,'ward',1,5,'buy')
    assert balance()==before


def test_protected_pumpkin_public_embed_has_no_witch_narrator(database,clock,monkeypatch):
    fund();protect()
    interaction,_=caller()
    values=iter([.9,0]);monkeypatch.setattr(pumpkins.random,'random',lambda:next(values))
    post=AsyncMock();monkeypatch.setattr(player,'post_to_target_channel',post)
    asyncio.run(player.smash_pumpkin(interaction,10))
    embed=post.call_args.args[1]
    assert 'hidden' in embed.description and 'cauldron' in embed.description
    assert not embed.image.url and not embed.author.name
    assert 'Bucket:' not in embed.description


def test_shop_config_permissions_and_serialization(database,clock):
    from modals.shop import ManageView, InventoryView, ShopModal
    async def scenario():
        interaction,_=caller(moderator=False)
        modal=ProtectionSettings(10,1)
        assert await modal.interaction_check(interaction) is False
        for view in (ManageView(10,1),InventoryView(10,1)):
            components=view.to_components()
            assert len(components)<=5
        modal=ShopModal(10,1)
        assert any(option.value=='veil' for option in modal.potion.options)
    asyncio.run(scenario())


def test_leave_confirmation_does_not_reset_before_confirm(database,clock):
    from cogs.participation import LeaveConfirm
    async def scenario():
        interaction,_=caller()
        view=LeaveConfirm(interaction)
        assert balance()==50
        await view.cancel.callback(interaction)
        assert balance()==50 and db.is_player_active(10,1)
        view=LeaveConfirm(interaction)
        await view.confirm.callback(interaction)
        assert balance()==0 and not db.is_player_active(10,1)
    asyncio.run(scenario())


def test_reaction_join_preserves_freeze_and_rejoin_delay(database,clock):
    import ast,logging
    from pathlib import Path
    tree=ast.parse((Path(__file__).resolve().parents[1]/'discord-bot/bot.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='on_raw_reaction_add');node.decorator_list=[]
    interaction,channel=caller()
    member=interaction.user;member.send=AsyncMock()
    client=NS(user=NS(id=99),get_guild=lambda _:interaction.guild,get_channel=lambda _:channel,message_loader=state.loader())
    env=dict(bot=client,logger=logging.getLogger('test'),get_join_game_msg_settings=lambda _: (123,99),discord=discord)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<reaction>','exec'),env)
    payload=NS(guild_id=1,channel_id=99,user_id=10,member=member,message_id=123,emoji='🎃')
    state.freeze(1,10,20,None,'secret','f');state.leave(1,10)
    asyncio.run(env['on_raw_reaction_add'](payload))
    assert 'secret' in member.send.call_args.args[0]
    channel.send.assert_not_awaited()
    state.unfreeze(1,10,20,'u')
    asyncio.run(env['on_raw_reaction_add'](payload))
    assert 'fresh start' in member.send.call_args.args[0] and balance()==0
    clock[0]=4600
    asyncio.run(env['on_raw_reaction_add'](payload))
    assert balance()==50 and channel.send.await_count==1


def test_mirror_choices_exclude_frozen_and_veiled_players(database,clock,monkeypatch):
    from utils import potion_gameplay as perks
    fund(30)
    protect(uid=30)
    state.freeze(1,40,20,None,'freeze','f')
    with db.transaction() as conn:potions.grant(conn,1,20,'mirror')
    potions.use(1,20,'mirror','mirror')
    interaction,_=caller()
    seen=[]
    def pick(options):
        seen.extend(member.id for member in options)
        return options[0]
    monkeypatch.setattr(perks,'choose_redirect',pick)
    with db.transaction():
        perks.resolve_protection(interaction,interaction.guild.get_member(20),player._TrickResponses())
    assert set(seen)=={10,50}
