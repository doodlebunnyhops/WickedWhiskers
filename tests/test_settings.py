import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
import db_utils as db
from cogs.mod_commands.get import get_settings


@pytest.mark.parametrize('event,admin,invite,message', [
    (101,None,None,None), (101,202,303,404), (None,202,None,None),
])
def test_settings_display_matches_database_fields(database,event,admin,invite,message):
    database.execute('INSERT INTO guild_settings VALUES(?,?,?,?,?)', (1,event,admin,message,invite))
    database.commit()
    assert db.get_guild_settings(1)==(event,admin,invite,message)
    channels={i:NS(mention=f'<#{i}>',fetch_message=AsyncMock(return_value=NS(jump_url='https://discord.com/channels/1/303/404'))) for i in (101,202,303)}
    interaction=NS(guild=NS(id=1,get_channel=lambda i:channels.get(i),get_role=lambda i:None),response=NS(send_message=AsyncMock()))
    asyncio.run(get_settings.callback(interaction))
    text=interaction.response.send_message.call_args.args[0]
    assert f"Event Channel: {f'<#{event}>' if event else 'Not Set'}" in text
    assert f"Admin Channel: {f'<#{admin}>' if admin else 'Not Set'}" in text
    assert f"Invite Channel: {f'<#{invite}>' if invite else 'Not Set'}" in text
    if message:channels[invite].fetch_message.assert_awaited_once_with(message)


def test_roles_without_channel_settings(database):
    db.set_role_by_guild(1,999)
    interaction=NS(guild=NS(id=1,get_channel=lambda i:None,get_role=lambda i:NS(name='Moderators')),response=NS(send_message=AsyncMock()))
    asyncio.run(get_settings.callback(interaction))
    text=interaction.response.send_message.call_args.args[0]
    assert 'Event Channel: Not Set' in text
    assert 'Moderators' in text
