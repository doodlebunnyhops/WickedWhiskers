import asyncio
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import discord
import pytest
import db_utils as db
from cogs.help import Help, HelpView, make_embed, PLAYER_TOPICS, MOD_TOPICS
from utils.messages import MessageLoader


def caller(manage=False,roles=()):
    return NS(user=NS(id=10,guild_permissions=NS(manage_guild=manage),roles=[NS(id=r) for r in roles]),guild=NS(id=1),client=NS(message_loader=MessageLoader(str(Path(__file__).resolve().parents[1]/'discord-bot/utils/messages.json'))),response=NS(send_message=AsyncMock(),edit_message=AsyncMock()))


@pytest.mark.parametrize('manage,roles,expected',[(False,(),PLAYER_TOPICS),(True,(),PLAYER_TOPICS+MOD_TOPICS),(False,(99,),PLAYER_TOPICS+MOD_TOPICS)])
def test_role_specific_private_menu(database,manage,roles,expected):
    db.set_role_by_guild(1,99)
    interaction=caller(manage,roles)
    asyncio.run(Help().help.callback(Help(),interaction))
    kwargs=interaction.response.send_message.call_args.kwargs
    assert kwargs['ephemeral'] is True
    assert tuple(o.value for o in kwargs['view'].children[0].options)==expected
    assert 'Set a stat' not in kwargs['embed'].description


def test_revoked_access_and_foreign_user(database):
    async def scenario():
        original=caller(True)
        view=HelpView(original)
        select=view.children[0]
        select._values=['management']
        revoked=caller(False)
        await select.callback(revoked)
        revoked.response.edit_message.assert_not_awaited()
        assert revoked.response.send_message.call_args.kwargs['ephemeral']
        foreign=caller();foreign.user.id=20
        assert await view.interaction_check(foreign) is False
    asyncio.run(scenario())


def test_player_navigation_and_no_writes(database):
    before=database.total_changes
    async def scenario():
        interaction=caller()
        view=HelpView(interaction)
        view.children[0]._values=['potions']
        await view.children[0].callback(interaction)
        embed=interaction.response.edit_message.call_args.kwargs['embed']
        assert 'Choose your mischief' in embed.title
        assert view.children[0].options[1].default
    asyncio.run(scenario())
    assert database.total_changes==before


def test_embed_limits_and_message_loading():
    loader=caller().client.message_loader
    for topic in PLAYER_TOPICS+MOD_TOPICS:
        embed=make_embed(loader,topic)
        assert len(embed)<=6000
        assert len(embed.title)<=256 and len(embed.description)<=4096
        assert len(embed.fields)<=25
        for field in embed.fields:
            assert len(field.name)<=256 and len(field.value)<=1024
            assert 'Message not found' not in field.value
            assert 'Error formatting' not in field.value


def test_command_registration():
    async def scenario():
        from cogs.help import setup
        from discord.ext import commands
        async with commands.Bot(command_prefix='!',intents=discord.Intents.none()) as bot:
            await setup(bot)
            command=bot.tree.get_command('help')
            assert command is not None and command.guild_only
    asyncio.run(scenario())
