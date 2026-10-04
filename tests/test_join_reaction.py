import ast
import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock
import discord
import pytest
from utils.join_message import seed_join_reaction
from utils.messages import MessageLoader

ROOT=Path(__file__).resolve().parents[1]


def loader():
    return MessageLoader(str(ROOT/'discord-bot/utils/messages.json'))


@pytest.mark.parametrize('fail',[False,True])
def test_seed_and_permission_error(fail):
    message=NS(add_reaction=AsyncMock(),jump_url='https://discord.com/channels/1/2/3')
    if fail:message.add_reaction.side_effect=discord.Forbidden(NS(status=403,reason='Forbidden'),'denied')
    interaction=NS(client=NS(message_loader=loader()),response=NS(is_done=lambda:False,send_message=AsyncMock()),followup=NS(send=AsyncMock()))
    assert asyncio.run(seed_join_reaction(interaction,message)) is not fail
    message.add_reaction.assert_awaited_once_with('🎃')
    if fail:
        assert 'Add Reactions' in interaction.response.send_message.call_args.args[0]
        assert interaction.response.send_message.call_args.kwargs['ephemeral']


@pytest.mark.parametrize('uid,is_bot,expected',[(99,True,False),(88,True,False),(10,False,True)])
def test_raw_reaction_ignores_bots_but_enrolls_humans(uid,is_bot,expected,monkeypatch):
    # Load just the actual event handler without running production bot startup.
    tree=ast.parse((ROOT/'discord-bot/bot.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='on_raw_reaction_add')
    node.decorator_list=[]
    member=NS(id=uid,bot=is_bot,mention=f'<@{uid}>')
    channel=NS(send=AsyncMock())
    guild=NS(id=1,get_member=lambda _:member)
    client=NS(user=NS(id=99),get_guild=lambda _:guild,get_channel=lambda _:channel,message_loader=loader())
    import player_state
    create=Mock()
    monkeypatch.setattr(player_state,"join",create)
    settings=Mock(return_value=(123,2))
    env=dict(bot=client,logger=logging.getLogger('test'),get_join_game_msg_settings=settings,is_player_active=lambda *args:False,create_player_data=create)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<handler>','exec'),env)
    payload=NS(guild_id=1,channel_id=2,user_id=uid,member=member,message_id=123,emoji='🎃')
    asyncio.run(env['on_raw_reaction_add'](payload))
    assert create.called==expected
    if not expected:settings.assert_not_called()


def test_existing_invitation_reseeds(database,monkeypatch):
    from cogs.mod_commands import send
    message=NS(add_reaction=AsyncMock(),jump_url='https://discord.com/channels/1/2/3')
    channel=NS(fetch_message=AsyncMock(return_value=message))
    monkeypatch.setattr(send.db_utils,'get_join_game_msg_settings',lambda guild:(3,2))
    interaction=NS(guild=NS(id=1,get_channel=lambda _:channel),client=NS(message_loader=loader()),response=NS(is_done=lambda:False,send_message=AsyncMock()),followup=NS(send=AsyncMock()))
    asyncio.run(send.set_join_game_msg.callback(interaction,channel))
    message.add_reaction.assert_awaited_once_with('🎃')
