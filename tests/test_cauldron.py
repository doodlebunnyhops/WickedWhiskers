import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from cogs.game_commands import cast
from utils.cauldron import eligibility_report


def test_report_explains_legacy_eligibility():
    report = eligibility_report([
        (10, 50, 0, 3, 15, 0, 0, 0),
        (20, 50, 2, 0, 0, 3, 0, 6),
    ])
    assert report['Luna normal (76.5%)']['players'] == [(20, 2)]
    assert report['Luna fumble (15%)']['players'] == [(20, 3)]
    assert report['Raven normal (76.5%)']['players'] == [(20, 3)]
    assert report['Raven explosion (15%)']['players'] == [(20, 1)]
    assert report['Luna special (8.5%)']['players'] == []
    assert report['Raven rage (8.5%)']['players'] == []


def test_moderator_report_is_private_and_read_only(database):
    import db_utils as db
    from cogs.game_commands.get import get_cauldron_eligibility
    db.set_cauldron_pool(1, 75)
    before = database.total_changes
    interaction = SimpleNamespace(guild=SimpleNamespace(id=1), response=SimpleNamespace(send_message=AsyncMock()))
    asyncio.run(get_cauldron_eligibility.callback(interaction))
    call = interaction.response.send_message.call_args
    assert call.kwargs['ephemeral'] is True
    assert 'Active database players: **5**' in call.kwargs['embed'].description
    assert len(call.kwargs['embed'].fields) == 7
    assert get_cauldron_eligibility.checks
    assert database.total_changes == before


@pytest.mark.parametrize('witch', ['luna', 'raven'])
@pytest.mark.parametrize('winners', ['One', 'many'])
@pytest.mark.parametrize('players', [[], [(10, 50, 0, 0, 0, 0, 0, 0)]])
def test_empty_eligibility_returns_message(database, monkeypatch, witch, winners, players):
    import db_utils as db
    db.set_cauldron_pool(1, 100)
    monkeypatch.setattr(cast, 'get_active_players_by_guild', lambda guild: players)
    monkeypatch.setattr(cast.random, 'random', lambda: 0.5)
    interaction = SimpleNamespace(guild=SimpleNamespace(id=1), response=SimpleNamespace(send_message=AsyncMock()))
    asyncio.run(cast.cast_spell.callback(interaction, witch, winners))
    call = interaction.response.send_message.call_args
    assert 'No eligible players' in call.args[0]
    assert call.kwargs['ephemeral'] is True
    assert db.get_cauldron_pool(1) == 100


@pytest.mark.parametrize('witch', ['luna', 'raven'])
@pytest.mark.parametrize('winners', ['One', 'many'])
def test_existing_eligible_selection_still_announces(monkeypatch, witch, winners):
    monkeypatch.setattr(cast, 'get_active_players_by_guild', lambda guild: [(10, 50, 1, 0, 0, 1, 0, 1)])
    monkeypatch.setattr(cast.random, 'random', lambda: 0.5)
    interaction = SimpleNamespace(guild=SimpleNamespace(id=1, get_member=lambda uid: SimpleNamespace(display_name='Player')), response=SimpleNamespace(send_message=AsyncMock()))
    asyncio.run(cast.cast_spell.callback(interaction, witch, winners))
    assert interaction.response.send_message.call_args.args[0] == f'{witch} has cast a spell with Player winners!'
