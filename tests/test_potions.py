import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
import db_utils as db
import potions as p
from modals.shop import ShopModal, UsePotionModal, ManageModal, Checkout, ManageView, ShopEntrance
from utils import player


def balance(uid=10, guild=1):
    return db.get_player_data(uid, guild)['candy_in_bucket']


def grant(key, uid=10, quantity=1, guild=1):
    with db.transaction() as conn:
        p.grant(conn, guild, uid, key, quantity)


def test_purchase_is_atomic_scoped_and_idempotent(database):
    p.purchase(1, 10, 'ward', 2, 5, 'order')
    p.purchase(1, 10, 'ward', 2, 5, 'order')
    assert balance() == 40
    assert balance(20) == balance(10, 2) == 50
    assert p.inventory(1, 10)[0] == {'ward': 2}
    assert db.get_cauldron_pool(1) == 0
    with pytest.raises(p.PotionError):
        p.purchase(1, 20, 'ward', 2, 5, 'order')


def test_insufficient_funds_and_quantity(database):
    for quantity in (0, -1, 101, 1.5):
        with pytest.raises(p.PotionError):
            p.purchase(1, 10, 'ward', quantity, 5, str(quantity))
    with pytest.raises(p.PotionError):
        p.purchase(1, 10, 'ward', 11, 5, 'poor')
    assert balance() == 50
    assert p.inventory(1, 10)[0] == {}


def test_rollback_on_grant_failure(database, monkeypatch):
    def fail(*a):
        raise RuntimeError('simulated write failure')
    monkeypatch.setattr(p, 'grant', fail)
    with pytest.raises(RuntimeError):
        p.purchase(1, 10, 'ward', 1, 5, 'fail')
    assert balance() == 50
    assert database.execute('SELECT count(*) FROM potion_actions').fetchone()[0] == 0


def test_price_changes_disabled_sales_and_owned_items(database):
    grant('ward')
    p.configure(1, 99, 'ward', 7, True)
    with pytest.raises(p.PriceChanged):
        p.purchase(1, 10, 'ward', 1, 5, 'order')
    assert balance() == 50
    assert p.offer(2, 'ward') == (5, True)
    p.configure(1, 99, 'ward', 7, False)
    with pytest.raises(p.PotionError):
        p.purchase(1, 10, 'ward', 1, 7, 'order')
    assert p.use(1, 10, 'ward', 'use')['charges'] == 1
    p.reset_prices(1, 99)
    assert p.offer(1, 'ward') == (5, False)


def test_effect_activation_no_stack_and_duplicate_use(database):
    grant('cunning', quantity=2)
    p.use(1, 10, 'cunning', 'use1')
    assert p.use(1, 10, 'cunning', 'use1')['replayed']
    with pytest.raises(p.PotionError):
        p.use(1, 10, 'cunning', 'use2')
    assert p.inventory(1, 10) == ({'cunning': 1}, {'cunning': 3})
    with db.transaction():
        assert p.trick_rate(1, 10, .5) == pytest.approx(.65)
        assert p.trick_rate(1, 10, .9) == pytest.approx(.95)
        assert p.trick_rate(1, 10, 1) == 1
        assert p.trick_rate(1, 10, .5) == .5
    assert p.inventory(1, 10)[1] == {}


def test_luna_scope_cooldown_and_idempotency(database):
    grant('luna', quantity=2)
    result = p.use(1, 10, 'luna', 'summon', {10,20,30,40,50}, now=100)
    assert len(set(result['recipients'])) == 3
    assert 10 not in result['recipients']
    assert sum(balance(uid) for uid in (10,20,30,40,50)) == 265
    assert sum(balance(uid,2) for uid in (10,20,30,40,50)) == 250
    p.use(1, 10, 'luna', 'summon', {10,20,30,40,50}, now=101)
    with pytest.raises(p.PotionError):
        p.use(1, 10, 'luna', 'other', {10,20}, now=101)
    assert p.inventory(1,10)[0]['luna'] == 1
    # A single eligible recipient gets 5, not the entire 15-candy budget.
    p.use(1,10,'luna','later',{10,20},now=160)
    assert balance(20) in (55,60)


def test_luna_no_eligible_recipient_keeps_bottle(database):
    grant('luna')
    db.update_player_field(20,1,'frozen',1)
    for members in (None, {10}, {10,20}):
        with pytest.raises(p.PotionError):
            p.use(1,10,'luna','none',members)
    assert p.inventory(1,10)[0]['luna'] == 1


def test_pause_freeze_and_inactive_reject_mutations(database):
    grant('ward')
    for field in ('frozen','active'):
        db.update_player_field(10,1,field,1 if field=='frozen' else 0)
        with pytest.raises(p.PotionError):p.use(1,10,'ward','x')
        with pytest.raises(p.PotionError):p.purchase(1,10,'ward',1,5,'x')
        db.update_player_field(10,1,field,0 if field=='frozen' else 1)
    db.set_game_disabled(1,True)
    with pytest.raises(p.PotionError):p.use(1,10,'ward','x')
    assert p.inventory(1,10)[0]['ward'] == 1


def interaction(uid=10, guild=1, action=123):
    member=NS(id=uid,display_name=str(uid),mention=f'<@{uid}>',name=str(uid),guild_permissions=NS(manage_guild=False),roles=[])
    return NS(id=action,user=member,guild_id=guild,guild=NS(id=guild),delete_original_response=AsyncMock(),edit_original_response=AsyncMock(),response=NS(defer=AsyncMock(),send_message=AsyncMock(),edit_message=AsyncMock(),send_modal=AsyncMock(),is_done=lambda:False),client=NS(message_loader=NS(get_message=lambda *a,**k:'event')))


def test_modal_components_serialize(database):
    async def run():
        grant('ward')
        for modal in (ShopModal(10,1),UsePotionModal(10,1),ManageModal(10,1,'ward')):
            payload=modal.to_dict()
            assert payload['components'][0]['type'] == 18  # Label wrapping the input/select
        assert ShopEntrance().is_persistent()
        assert ManageView(10,1).to_components()
    asyncio.run(run())


def test_checkout_rechecks_owner_price_and_duplicate_click(database):
    async def run():
        view=Checkout(10,1,'ward',1,5,'order')
        assert not await view.interaction_check(interaction(20))
        assert not await view.interaction_check(interaction(10,2))
        buyer=interaction()
        p.configure(1,99,'ward',8,True)
        await view.confirm.callback(buyer)
        assert view.price == 8 and balance() == 50
        await view.confirm.callback(buyer)
        await view.confirm.callback(buyer)
        assert balance() == 42
        assert p.inventory(1,10)[0]['ward'] == 1
    asyncio.run(run())


def test_legacy_target_shop_opens_callers_modal(database):
    from utils.shop import buy_potion
    async def run():
        caller=interaction(10)
        await buy_potion(caller,interaction(20).user,100)
        modal=caller.response.send_modal.call_args.args[0]
        assert modal.owner_id == 10
        assert balance(10) == balance(20) == 50
    asyncio.run(run())


def test_management_revocation(database):
    async def run():
        member=interaction().user
        assert not p.can_manage(member,1)
        p.set_manager_role(1,99,123)
        member.roles=[NS(id=123)]
        assert p.can_manage(member,1) and not p.can_manage(member,2)
        modal=ManageModal(10,1,'ward')
        p.set_manager_role(1,99,None)
        assert not await modal.interaction_check(interaction())
    asyncio.run(run())


def test_ward_preserves_cunning_and_is_single_use(database):
    grant('cunning');grant('ward',uid=20)
    p.use(1,10,'cunning','c');p.use(1,20,'ward','w')
    responses=player._TrickResponses()
    with db.transaction():player._resolve_trick(interaction(),interaction(20).user,responses)
    assert balance(10)==balance(20)==50
    assert p.inventory(1,10)[1]['cunning']==3
    assert p.inventory(1,20)[1]=={}
    assert database.execute('SELECT tricks_blocked FROM potion_stats WHERE guild_id=1 AND player_id=20').fetchone()[0]==1


def test_reclaim_one_preserves_candy_and_counts_net_theft(database,monkeypatch):
    rolls=iter([0,.9,0])
    monkeypatch.setattr(player.random,'random',lambda:next(rolls))
    monkeypatch.setattr(player.random,'randint',lambda a,b:8)
    with db.transaction():player._resolve_trick(interaction(),interaction(20).user,player._TrickResponses())
    assert (balance(10),balance(20))==(57,43)
    assert db.get_player_data(10,1)['total_candy_stolen']==7


def test_recovery_steal_cannot_overdraw_target(database,monkeypatch):
    db.update_player_field(20,1,'candy_in_bucket',1)
    rolls=iter([.99,.9,0])
    monkeypatch.setattr(player.random,'random',lambda:next(rolls))
    monkeypatch.setattr(player.random,'randint',lambda a,b:5)
    with db.transaction():player._resolve_trick(interaction(),interaction(20).user,player._TrickResponses())
    assert (balance(10),balance(20))==(51,0)


def test_effect_rolls_back_if_trick_resolution_fails(database,monkeypatch):
    grant('cunning');p.use(1,10,'cunning','c')
    def fail(*a):raise RuntimeError('random failure')
    monkeypatch.setattr(player.random,'randint',fail)
    with pytest.raises(RuntimeError):
        asyncio.run(player.player_trick(interaction(),interaction(20).user))
    assert p.inventory(1,10)[1]['cunning']==3
    assert balance()==50


def test_trick_duplicate_interaction_cannot_consume_twice(database,monkeypatch):
    grant('cunning');p.use(1,10,'cunning','c')
    monkeypatch.setattr(player.random,'random',lambda:.5)
    monkeypatch.setattr(player.random,'randint',lambda a,b:3)
    monkeypatch.setattr(player,'post_to_target_channel',AsyncMock())
    caller=interaction()
    asyncio.run(player.player_trick(caller,interaction(20).user))
    asyncio.run(player.player_trick(caller,interaction(20).user))
    assert balance()==53
    assert p.inventory(1,10)[1]['cunning']==2


def test_candy_rain_and_named_gift(database):
    caller=interaction();target=interaction(20).user
    with db.transaction():
        player.give_all_candy(caller,1,caller.user,db.get_player_data(10,1),target,db.get_player_data(20,1),10)
    assert balance()==51 and balance(20)==61
    assert isinstance(balance(),int)
    with db.transaction():
        player.luna_cauldron_fill(caller,1,caller.user,db.get_player_data(10,1),target,db.get_player_data(20,1),10,500)
    assert p.inventory(1,10)[0]['ward']==1
    assert p.inventory(1,20)[0]['ward']==1


def test_season_reset_clears_state_only_in_server(database):
    grant('ward');grant('ward',guild=2)
    p.use(1,10,'ward','w');p.configure(1,99,'ward',9,True)
    db.reset_game(1)
    assert p.inventory(1,10)==({}, {})
    assert p.inventory(2,10)[0]['ward']==1
    assert p.offer(1,'ward')==(9,True)


def test_effects_survive_connection_restart(database,tmp_path):
    import sqlite3
    grant('cunning');p.use(1,10,'cunning','c')
    file=tmp_path/'season.db'
    disk=sqlite3.connect(file)
    database.backup(disk);disk.close()
    db.close_db_connection();db.conn=sqlite3.connect(file)
    assert p.inventory(1,10)[1]['cunning']==3


def test_cog_registration(database):
    import discord
    from discord.ext import commands
    from cogs.shop import setup
    async def run():
        bot=commands.Bot(command_prefix='!',intents=discord.Intents.none())
        async with bot:
            await setup(bot)
            assert {c.name for c in bot.tree.get_commands()}=={'shop','inventory','use'}
            assert {c.name for c in bot.tree.get_command('shop').commands}=={'browse','manage','manager_role','post','protection'}
            assert bot.persistent_views
    asyncio.run(run())


def test_empty_bucket_keeps_cunning(database, monkeypatch):
    grant('cunning');p.use(1,10,'cunning','c')
    db.update_player_field(20,1,'candy_in_bucket',0)
    monkeypatch.setattr(player.random,'random',lambda:.9)
    with db.transaction():player._resolve_trick(interaction(),interaction(20).user,player._TrickResponses())
    assert p.inventory(1,10)[1]['cunning']==3


def test_shared_loss_funds_only_actual_deductions(database, monkeypatch):
    db.update_player_field(20,1,'candy_in_bucket',1)
    rolls=iter([.99,0])
    monkeypatch.setattr(player.random,'random',lambda:next(rolls))
    monkeypatch.setattr(player.random,'randint',lambda a,b:5)
    with db.transaction():player._resolve_trick(interaction(),interaction(20).user,player._TrickResponses())
    assert balance(10)==45 and balance(20)==0
    assert db.get_cauldron_pool(1)==6


def test_two_orders_cannot_overspend(database):
    p.purchase(1,10,'ward',6,5,'first')
    with pytest.raises(p.PotionError):p.purchase(1,10,'ward',6,5,'second')
    assert balance()==20 and p.inventory(1,10)[0]['ward']==6


def test_luna_rollback_keeps_bottle_and_rewards(database,monkeypatch):
    grant('luna')
    def fail(*a):raise RuntimeError('history failure')
    monkeypatch.setattr(p,'record_action',fail)
    with pytest.raises(RuntimeError):p.use(1,10,'luna','use',{10,20},now=1)
    assert balance(20)==50
    assert p.inventory(1,10)[0]['luna']==1
    assert database.execute('SELECT count(*) FROM potion_cooldowns').fetchone()[0]==0


def test_settings_use_main_connection(database):
    db.set_game_setting(1,game_disabled=True)
    assert db.get_game_settings(1)[0]
    db.set_game_setting(1,game_disabled=False)
    assert not db.get_game_settings(1)[0]


def test_real_bot_setup_without_login(database,monkeypatch):
    import importlib
    import settings
    from discord.ext import commands
    from pathlib import Path
    settings.GUILDS_ID=None
    settings.DISCORD_API_SECRET='not-a-real-token'
    monkeypatch.setattr(commands.Bot,'run',lambda *a,**k:None)
    monkeypatch.chdir(Path(__file__).resolve().parents[1]/'discord-bot')
    module=importlib.import_module('bot')
    module.bot.tree.sync=AsyncMock(return_value=[])
    async def run():
        async with module.bot:
            await module.bot.setup_hook()
            names={c.name for c in module.bot.tree.get_commands()}
            assert {'shop','inventory','use','Potion Shop','trick','treat'} <= names
            assert 'buy' not in names
    asyncio.run(run())
