import asyncio
import json
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import discord
import pytest
import db_utils as db
from utils import player,pumpkins
from utils.messages import MessageLoader
from utils.game_messages import unique_mentions,publish_result


def caller():
    people={i:NS(id=i,mention=f'<@{i}>',display_name=n,name=n) for i,n in [(10,'Ashley'),(20,'Megatron'),(30,'Daisy')]}
    response=NS(is_done=lambda:False,defer=AsyncMock(),send_message=AsyncMock())
    return NS(id=553,user=people[10],guild=NS(id=1,get_member=people.get),channel=NS(send=AsyncMock()),client=NS(message_loader=MessageLoader(str(Path(__file__).resolve().parents[1]/'discord-bot/utils/messages.json'))),response=response,followup=NS(send=AsyncMock()),delete_original_response=AsyncMock(),edit_original_response=AsyncMock())


def test_mirror_mentions_unique_across_fields_and_self_reflection():
    c=caller()
    e=discord.Embed(description='<@20> reflects <@10> toward <@30>. <@!10> takes candy from <@30>.')
    e.add_field(name='Effect',value='<@20> stays safe. <@10> celebrates.')
    result=unique_mentions(e,c)
    assert result.description=='<@20> reflects <@10> toward <@30>. Ashley takes candy from Daisy.'
    assert result.fields[0].value=='Megatron stays safe. Ashley celebrates.'
    assert '<@!10>' in e.description # Original template untouched.
    assert unique_mentions('<@10> tricks <@10>',c)=='<@10> tricks Ashley'


def test_duplicate_names_and_markdown_do_not_create_new_mentions():
    c=caller();c.user.display_name='*same*';c.guild.get_member(20).display_name='*same*'
    text=unique_mentions('<@10> <@20> <@10> <@20>',c)
    assert '\\*same\\* (10)' in text and '\\*same\\* (20)' in text
    c.user.display_name='<@999> @everyone'
    text=unique_mentions('<@10> <@10>',c)
    assert '<@999>' not in text and '@everyone' not in text


def test_delivery_success_and_failure():
    async def run():
        c=caller();post=AsyncMock()
        assert await publish_result(c,discord.Embed(description='<@10> wins'),post)
        c.response.defer.assert_awaited_once_with(ephemeral=True,thinking=True)
        c.delete_original_response.assert_awaited_once()
        c.followup.send.assert_not_awaited();c.response.send_message.assert_not_awaited()
        c=caller();post=AsyncMock(side_effect=discord.Forbidden(NS(status=403,reason='Forbidden'),'denied'))
        assert not await publish_result(c,'saved outcome',post)
        assert 'saved' in c.edit_original_response.call_args.kwargs['content']
        c.delete_original_response.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize('balance,tier',[(0,'empty'),(1,'small'),(49,'small'),(50,'growing'),(499,'growing'),(500,'large')])
@pytest.mark.parametrize('witch',['luna','raven'])
def test_bucket_tiers(database,monkeypatch,balance,tier,witch):
    c=caller();db.update_player_field(10,1,'candy_in_bucket',balance)
    monkeypatch.setattr(player.random,'choice',lambda choices:witch if choices==['luna','raven'] else choices[0])
    c.client.message_loader.messages['bucket_messages'][witch][tier]=['correct tier']
    asyncio.run(player.player_bucket(c))
    text=c.response.send_message.call_args.kwargs['embed'].description
    assert 'correct tier' in text and f'Candy: {balance}' in text


def test_public_treat_and_trick_no_private_success(database,monkeypatch):
    monkeypatch.setattr(player.random,'random',lambda:.9)
    monkeypatch.setattr(player.random,'randint',lambda a,b:3)
    post=AsyncMock();monkeypatch.setattr(player,'post_to_target_channel',post)
    for action in ('treat','trick'):
        c=caller();c.id+=int(action=='trick')
        if action=='treat':asyncio.run(player.player_treat(c,c.guild.get_member(20),2))
        else:asyncio.run(player.player_trick(c,c.guild.get_member(20)))
        c.response.send_message.assert_not_awaited();c.followup.send.assert_not_awaited()
        c.delete_original_response.assert_awaited_once()
    assert post.await_count==2


def test_templates_format_and_no_repeated_pumpkin_addon_player():
    d=caller().client.message_loader.messages
    values=dict(user='<@10>',target='<@20>',original='<@30>',amount=3,net_amount=2,total=6,giver_bonus=3,cauldron_candy_amount=50,candy_amount=3,chance=30)
    def check(v):
        if isinstance(v,dict):
            for child in v.values():check(child)
        elif isinstance(v,list):
            for item in v:assert item.format(**values)
    for key in ('give_treat','trick_player','smash_pumpkin'):check(d[key]['event_messages'])
    for key in ('luna','raven','hidden_luna','hidden_raven'):
        assert all('{user}' not in text for text in d['smash_pumpkin']['event_messages'][key])


def test_special_treat_announces_wards_and_real_double_gains(database):
    c=caller();target=c.guild.get_member(20)
    with db.transaction():
        embed,_=player.luna_cauldron_fill(c,1,c.user,db.get_player_data(10,1),target,db.get_player_data(20,1),10,500)
    assert 'Witch’s Ward' in embed.description and '**10 candy**' in embed.description
    before_a=db.get_player_data(10,1)['candy_in_bucket'];before_b=db.get_player_data(20,1)['candy_in_bucket']
    with db.transaction():
        embed,_=player.double_candy(c,1,c.user,db.get_player_data(10,1),target,db.get_player_data(20,1),10)
    assert '**20 candy**' in embed.description and '**10 extra**' in embed.description
    assert db.get_player_data(10,1)['candy_in_bucket']==before_a+10
    assert db.get_player_data(20,1)['candy_in_bucket']==before_b+20


def test_treat_modal_uses_single_public_result(database,monkeypatch):
    from modals.player import Treat
    monkeypatch.setattr(player.random,'random',lambda:.9)
    post=AsyncMock();monkeypatch.setattr(player,'post_to_target_channel',post)
    async def run():
        c=caller();modal=Treat(c.guild.get_member(20));modal.amount._value='2'
        await modal.on_submit(c)
        post.assert_awaited_once();c.delete_original_response.assert_awaited_once()
        c.response.send_message.assert_not_awaited()
    asyncio.run(run())


def test_missing_event_channel_falls_back_publicly(database):
    from utils.utils import post_to_target_channel
    c=caller();c.guild.get_channel=lambda uid:None
    asyncio.run(publish_result(c,discord.Embed(description='public result'),post_to_target_channel))
    c.channel.send.assert_awaited_once();c.followup.send.assert_not_awaited()


def test_invalid_treat_stays_private_without_candy_changes(database,monkeypatch):
    c=caller();post=AsyncMock();monkeypatch.setattr(player,'post_to_target_channel',post)
    asyncio.run(player.player_treat(c,c.guild.get_member(20),999))
    assert c.response.send_message.call_args.kwargs['ephemeral']
    assert db.get_player_data(10,1)['candy_in_bucket']==50
    post.assert_not_awaited();c.delete_original_response.assert_not_awaited()
