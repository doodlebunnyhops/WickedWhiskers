import asyncio
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
import db_utils as db
import potions
from utils import player, potion_gameplay as perks
from utils.messages import MessageLoader


def balance(uid, guild=1):
    return db.get_player_data(uid, guild)['candy_in_bucket']


def activate(key,uid=10):
    with db.transaction() as conn:
        potions.grant(conn,1,uid,key)
    return potions.use(1,uid,key,f'use-{uid}-{key}')


def member(uid):
    return NS(id=uid,mention=f'<@{uid}>',name=str(uid),display_name=str(uid),bot=False)


def interaction():
    members={uid:member(uid) for uid in (10,20,30,40,50)}
    return NS(id=987,user=members[10],guild=NS(id=1,chunked=True,get_member=lambda uid:members.get(uid)),client=NS(message_loader=MessageLoader(str(Path(__file__).resolve().parents[1]/'discord-bot/utils/messages.json'))),delete_original_response=AsyncMock(),edit_original_response=AsyncMock(),response=NS(defer=AsyncMock(),send_message=AsyncMock(),is_done=lambda:False),followup=NS(send=AsyncMock()))


def resolve(monkeypatch,target=20):
    monkeypatch.setattr(player,'post_to_target_channel',AsyncMock())
    caller=interaction()
    asyncio.run(player.player_trick(caller,member(target)))
    return caller


@pytest.mark.parametrize('first,second',[('ward','mirror'),('mirror','ward')])
def test_defenses_cannot_coexist(database,first,second):
    activate(first)
    with db.transaction() as conn:potions.grant(conn,1,10,second)
    with pytest.raises(potions.PotionError):potions.use(1,10,second,'conflict')
    assert potions.inventory(1,10)[0][second]==1
    assert potions.inventory(1,10)[1]=={first:1}


@pytest.mark.parametrize('key,price',[('mirror',10),('sticky',8),('second_chance',8),('favor',5)])
def test_new_potions_buy_activate_and_server_prices(database,key,price):
    potions.configure(2,99,key,99,True)
    assert potions.offer(1,key)==(price,True)
    potions.purchase(1,10,key,1,price,'purchase')
    potions.use(1,10,key,'activate')
    assert balance(10)==50-price
    assert potions.inventory(1,10)[1][key]==(3 if key=='sticky' else 1)
    assert not potions.inventory(2,10)[1]


def test_mirror_self_pool_and_duplicate_request(database,monkeypatch):
    activate('mirror',20)
    activate('cunning');activate('sticky');activate('second_chance')
    monkeypatch.setattr(perks,'choose_redirect',lambda options:next(m for m in options if m.id==10))
    monkeypatch.setattr(perks.random,'random',lambda:0)
    monkeypatch.setattr(perks.random,'randint',lambda a,b:8)
    caller=resolve(monkeypatch)
    asyncio.run(player.player_trick(caller,member(20)))
    assert (balance(10),balance(20),db.get_cauldron_pool(1))==(49,50,1)
    assert potions.inventory(1,20)[1]=={}
    assert potions.inventory(1,10)[1]=={'cunning':2,'sticky':3,'second_chance':1}
    assert db.get_player_data(10,1)['failed_tricks']==1
    event=player.post_to_target_channel.call_args.args[1]
    assert 'cauldron' in event.description and '<@20>' in event.description and 'Cunning' in event.description


def test_redirect_to_third_player_with_sticky(database,monkeypatch):
    activate('mirror',20);activate('sticky')
    monkeypatch.setattr(perks,'choose_redirect',lambda options:next(m for m in options if m.id==30))
    rolls=iter([0,.9,.9]);monkeypatch.setattr(perks.random,'random',lambda:next(rolls))
    monkeypatch.setattr(perks.random,'randint',lambda a,b:7)
    resolve(monkeypatch)
    assert (balance(10),balance(20),balance(30))==(53,50,47)
    assert potions.inventory(1,10)[1]=={'sticky':2}
    assert db.get_player_data(10,1)['total_candy_stolen']==3
    assert 'Sticky Fingers' in player.post_to_target_channel.call_args.args[1].description


@pytest.mark.parametrize('shield',['ward','mirror'])
def test_redirected_protection_stops_once_preserves_attacker_effects(database,monkeypatch,shield):
    activate('mirror',20);activate(shield,30)
    activate('cunning');activate('second_chance')
    choices=[]
    def redirect(options):
        choices.append(options)
        return next(m for m in options if m.id==30)
    monkeypatch.setattr(perks,'choose_redirect',redirect)
    monkeypatch.setattr(perks.random,'random',lambda:pytest.fail('Blocked attempt must not roll'))
    resolve(monkeypatch)
    assert len(choices)==1
    assert [balance(x) for x in (10,20,30)]==[50,50,50]
    assert not potions.inventory(1,20)[1] and not potions.inventory(1,30)[1]
    assert potions.inventory(1,10)[1]=={'cunning':3,'second_chance':1}


def test_mirror_filters_inactive_frozen_missing_and_bot_members(database,monkeypatch):
    activate('mirror',20)
    db.update_player_field(30,1,'active',0);db.update_player_field(40,1,'frozen',1)
    caller=interaction();caller.guild.get_member(50).bot=True
    def choose(options):
        assert [x.id for x in options]==[10]
        return options[0]
    monkeypatch.setattr(perks,'choose_redirect',choose)
    monkeypatch.setattr(perks.random,'random',lambda:0.99)
    responses=player._TrickResponses()
    with db.transaction():player._resolve_trick(caller,member(20),responses)
    assert balance(10)==balance(20)==50
    assert not potions.inventory(1,20)[1]


def test_empty_redirect_keeps_roll_potions(database,monkeypatch):
    activate('mirror',20);activate('cunning');activate('second_chance')
    db.update_player_field(30,1,'candy_in_bucket',0)
    monkeypatch.setattr(perks,'choose_redirect',lambda options:next(m for m in options if m.id==30))
    monkeypatch.setattr(perks.random,'random',lambda:pytest.fail('Empty target must not roll'))
    resolve(monkeypatch)
    assert potions.inventory(1,10)[1]=={'cunning':3,'second_chance':1}


def test_second_chance_rerolls_once_at_boosted_rate(database,monkeypatch):
    activate('cunning');activate('second_chance')
    rolls=iter([.99,.6,.9,.9])
    monkeypatch.setattr(player.random,'random',lambda:next(rolls))
    monkeypatch.setattr(player.random,'randint',lambda a,b:8)
    resolve(monkeypatch)
    assert (balance(10),balance(20))==(52,48)
    assert potions.inventory(1,10)[1]=={'cunning':2}
    description=player.post_to_target_channel.call_args.args[1].description
    assert 'Second Chance' in description and 'Cunning' in description


def test_second_failed_roll_no_third_roll_in_reflection(database,monkeypatch):
    activate('mirror',20);activate('second_chance')
    monkeypatch.setattr(perks,'choose_redirect',lambda options:options[0])
    rolls=iter([.99,.99,.9,.9])
    monkeypatch.setattr(perks.random,'random',lambda:next(rolls))
    resolve(monkeypatch)
    assert balance(10)==50 and db.get_cauldron_pool(1)==0
    assert not potions.inventory(1,10)[1]


def test_sticky_normal_cap_and_remaining_charges(database,monkeypatch):
    activate('sticky')
    db.update_player_field(20,1,'candy_in_bucket',8)
    rolls=iter([0,.9,.9])
    monkeypatch.setattr(player.random,'random',lambda:next(rolls))
    from utils import tricks
    monkeypatch.setattr(tricks,'percentage',lambda balance,low,high:7 if low==2 else 3)
    resolve(monkeypatch)
    assert (balance(10),balance(20))==(58,0)
    assert potions.inventory(1,10)[1]=={'sticky':2}


def test_sticky_kept_when_special_success_changes_outcome(database,monkeypatch):
    activate('sticky')
    rolls=iter([0,0])
    monkeypatch.setattr(player.random,'random',lambda:next(rolls))
    monkeypatch.setattr(player.random,'randint',lambda a,b:8)
    resolve(monkeypatch)
    assert potions.inventory(1,10)[1]['sticky']==3


@pytest.mark.parametrize('amount,bonus',[(1,0),(2,1),(5,2),(20,5)])
def test_favor_bonus_cap_cost_and_duplicate_treat(database,monkeypatch,amount,bonus):
    activate('favor')
    monkeypatch.setattr(player.random,'random',lambda:.9)
    caller=interaction()
    event,personal=player.give_treat(caller,member(20),amount)
    player.give_treat(caller,member(20),amount)
    assert balance(10)==50-amount
    assert balance(20)==50+amount+bonus
    assert potions.inventory(1,10)[1].get('favor',0)==(0 if bonus else 1)
    assert db.get_player_data(10,1)['total_candy_given']==amount+bonus
    assert db.get_player_data(10,1)['treats_given']==1
    if bonus:assert 'Luna’s Favor' in event.description


def test_favor_kept_for_magical_treat(database,monkeypatch):
    activate('favor')
    monkeypatch.setattr(player.random,'random',lambda:0)
    player.give_treat(interaction(),member(20),30)
    assert potions.inventory(1,10)[1]['favor']==1


def test_mirror_charge_rolls_back_on_failure(database,monkeypatch):
    activate('mirror',20)
    monkeypatch.setattr(perks,'choose_redirect',lambda options:options[0])
    from utils import tricks
    monkeypatch.setattr(tricks,'percentage',lambda *args:(_ for _ in ()).throw(RuntimeError('failure')))
    with pytest.raises(RuntimeError):resolve(monkeypatch)
    assert potions.inventory(1,20)[1]['mirror']==1
    assert balance(10)==balance(20)==50


def test_reflection_into_attackers_ward_blocks_self_loss(database,monkeypatch):
    activate('mirror',20);activate('ward');activate('cunning')
    monkeypatch.setattr(perks,'choose_redirect',lambda options:options[0])
    monkeypatch.setattr(perks.random,'random',lambda:pytest.fail('Ward prevents roll'))
    resolve(monkeypatch)
    assert balance(10)==50
    assert potions.inventory(1,10)[1]=={'cunning':3}
    assert not potions.inventory(1,20)[1]


def test_sticky_preserved_when_no_extra_candy_available(database,monkeypatch):
    activate('sticky')
    db.update_player_field(20,1,'candy_in_bucket',7)
    rolls=iter([0,.9,.9])
    monkeypatch.setattr(player.random,'random',lambda:next(rolls))
    from utils import tricks
    monkeypatch.setattr(tricks,'percentage',lambda balance,low,high:balance)
    resolve(monkeypatch)
    assert balance(20)==0
    assert potions.inventory(1,10)[1]['sticky']==3


def test_favor_rolls_back_both_transfer_and_charge(database,monkeypatch):
    import sqlite3
    activate('favor')
    monkeypatch.setattr(player.random,'random',lambda:.9)
    database.execute("CREATE TRIGGER fail_favor BEFORE UPDATE OF candy_in_bucket ON players WHEN NEW.player_id=20 AND NEW.candy_in_bucket>60 BEGIN SELECT RAISE(ABORT,'failure'); END")
    database.commit()
    with pytest.raises(sqlite3.IntegrityError):player.give_treat(interaction(),member(20),10)
    assert balance(10)==balance(20)==50
    assert potions.inventory(1,10)[1]['favor']==1


def test_new_effects_do_not_trigger_on_invalid_tricks(database,monkeypatch):
    activate('mirror',20);activate('second_chance');activate('cunning')
    db.update_player_field(10,1,'frozen',1)
    monkeypatch.setattr(perks,'choose_redirect',lambda options:pytest.fail('Invalid trick must not redirect'))
    resolve(monkeypatch)
    assert potions.inventory(1,20)[1]['mirror']==1
    assert potions.inventory(1,10)[1]=={'second_chance':1,'cunning':3}


def test_all_gameplay_templates_format_and_have_player_context(database):
    loader=interaction().client.message_loader
    values=dict(user='<@10>',target='<@20>',original='<@30>',amount=2,total=9,chance=95,potion='Mirror Brew',charges=1)
    for key,value in loader.messages['potion_events'].items():
        for variant in value if isinstance(value,list) else [value]:
            loader.messages['_test_potion']=variant
            result=loader.get_message('_test_potion',**values)
            assert 'Message not found' not in result
            assert not result.startswith('Error formatting')


def test_sticky_three_thefts_then_normal_and_replay(database,monkeypatch):
    activate('sticky')
    monkeypatch.setattr(player,'post_to_target_channel',AsyncMock())
    monkeypatch.setattr(player.random,'randint',lambda a,b:4)
    for index,expected in enumerate([3,3,3,2]):
        rolls=iter([0,.9,.9])
        monkeypatch.setattr(player.random,'random',lambda:next(rolls))
        caller=interaction();caller.id+=index
        before=balance(10)
        asyncio.run(player.player_trick(caller,member(20)))
        assert balance(10)==before+expected
        assert potions.inventory(1,10)[1].get('sticky',0)==max(0,2-index)
        asyncio.run(player.player_trick(caller,member(20)))
        assert balance(10)==before+expected
        assert potions.inventory(1,10)[1].get('sticky',0)==max(0,2-index)
    assert db.get_player_data(10,1)['total_candy_stolen']==11
    assert db.get_player_data(20,1)['total_candy_lost']==11


@pytest.mark.parametrize('blocked',[False,True])
def test_sticky_failed_or_blocked_attempt_preserves_charges(database,monkeypatch,blocked):
    activate('sticky')
    if blocked:
        activate('ward',20)
    monkeypatch.setattr(player.random,'random',lambda:.99)
    resolve(monkeypatch)
    assert potions.inventory(1,10)[1]['sticky']==3


def test_sticky_transfer_failure_rolls_back_charge(database,monkeypatch):
    import sqlite3
    activate('sticky')
    rolls=iter([0,.9,.9])
    monkeypatch.setattr(player.random,'random',lambda:next(rolls))
    monkeypatch.setattr(player.random,'randint',lambda a,b:4)
    database.execute("CREATE TRIGGER fail_sticky BEFORE UPDATE OF candy_in_bucket ON players WHEN NEW.candy_in_bucket<>OLD.candy_in_bucket BEGIN SELECT RAISE(ABORT,'failure'); END")
    database.commit()
    with pytest.raises(sqlite3.IntegrityError):
        resolve(monkeypatch)
    assert balance(10)==balance(20)==50
    assert potions.inventory(1,10)[1]['sticky']==3


@pytest.fixture(autouse=True)
def stable_trick_amounts(monkeypatch):
    from utils import tricks
    monkeypatch.setattr(tricks,'percentage',lambda balance,low,high:min(balance,max(1,(balance*(low+high)+100)//200)) if balance else 0)
