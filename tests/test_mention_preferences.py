import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import discord
import db_utils as db
import mention_preferences as prefs
from utils.utils import post_to_target_channel


def guild():
    return NS(id=1,get_member=lambda uid:NS(display_name='Quiet Player' if uid==10 else 'Other'))


def test_default_and_server_isolation(database):
    assert prefs.enabled(1,10)
    prefs.configure(1,10,False)
    assert not prefs.enabled(1,10) and prefs.enabled(2,10) and prefs.enabled(1,20)
    db.reset_player_data(10,1)
    assert not prefs.enabled(1,10)
    prefs.configure(1,10,True)
    assert prefs.enabled(1,10)


def test_mixed_announcement_and_safe_names(database):
    prefs.configure(1,10,False)
    p=prefs.Announcement(guild())
    embed=discord.Embed(title='<@10>',description='<@10> tricks <@20>')
    embed.add_field(name='Winner',value='<@!10>')
    result=p.message(embed)
    assert result.title=='Quiet Player'
    assert result.description=='Quiet Player tricks <@20>'
    assert result.fields[0].value=='Quiet Player'
    assert embed.title=='<@10>'
    assert p.allowed(result).to_dict()['users']==[20]
    assert p.allowed(result).to_dict()['parse']==[]
    evil=NS(id=1,get_member=lambda uid:NS(display_name='@everyone <@20> **oops**'))
    text=prefs.Announcement(evil).text('<@10>')
    assert '<@20>' not in text and '@everyone' not in text


def test_public_delivery_respects_each_player(database):
    prefs.configure(1,10,False)
    channel=NS(send=AsyncMock())
    g=guild();g.get_channel=lambda cid:channel
    caller=NS(guild=g,channel=channel)
    asyncio.run(post_to_target_channel(caller,'<@10> treated <@20>'))
    assert channel.send.call_args.args[0]=='Quiet Player treated <@20>'
    assert channel.send.call_args.kwargs['allowed_mentions'].to_dict()['users']==[20]


def test_command_only_updates_invoking_user(database):
    from cogs.player import Player
    from utils.messages import default_messages
    caller=NS(guild_id=1,user=NS(id=10),client=NS(message_loader=default_messages()),response=NS(send_message=AsyncMock()))
    asyncio.run(Player.mentions.callback(None,caller,False))
    assert not prefs.enabled(1,10) and prefs.enabled(1,20)
    assert caller.response.send_message.call_args.kwargs['ephemeral'] is True
