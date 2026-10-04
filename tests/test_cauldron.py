import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from cogs.game_commands import cast
from utils import cauldron

PLAYERS = [(10,50,0,3,15,0,0,0), (20,50,0,0,0,2,0,6), (30,50,0,0,0,0,0,0)]


def test_all_outcomes_include_newcomers_and_favor_witch_stat():
    report = cauldron.eligibility_report(PLAYERS)
    assert all({uid for uid, weight in row['players']} == {10,20,30} for row in report.values())
    assert report['Luna normal (76.5%)']['players'] == [(10,4),(20,1),(30,1)]
    assert report['Raven normal (76.5%)']['players'] == [(10,1),(20,3),(30,1)]
    assert report['Luna special (8.5%)']['players'] == [(10,4),(20,1),(30,1)]
    assert report['Raven rage (8.5%)']['players'] == [(10,1),(20,3),(30,1)]
    changed_purchases = [(uid,candy,999,treats,given,success,fail,stolen) for uid,candy,_,treats,given,success,fail,stolen in PLAYERS]
    assert cauldron.eligibility_report(changed_purchases) == report


@pytest.mark.parametrize('witch,outcome',[('luna','special'),('raven','rage')])
def test_special_outcome_falls_back_to_equal_weights(witch,outcome):
    assert cauldron.candidates([(10,50,0,3,15,3,0,6),(20,50,0,0,0,0,0,0)],witch,outcome) == [(10,1),(20,1)]


def test_many_samples_distinct_players_with_weights(monkeypatch):
    monkeypatch.setattr(cauldron.random,'randint',lambda low,high:high)
    calls=[]
    def choose(population,weights,k):
        calls.append((population.copy(),weights.copy()))
        return [population[0]]
    monkeypatch.setattr(cauldron.random,'choices',choose)
    assert cauldron.select_winners([(10,1000000),(20,2),(30,1)],'many') == [10,20,30]
    assert calls == [([10,20,30],[1000000,2,1]),([20,30],[2,1]),([30],[1])]


@pytest.mark.parametrize('witch',['luna','raven'])
@pytest.mark.parametrize('rolls,expected', [([0.1],1),([0.5,0.05],2),([0.5,0.5],0)])
def test_outcome_rolls_preserve_original_chances(monkeypatch,witch,rolls,expected):
    values=iter(rolls)
    monkeypatch.setattr(cauldron.random,'random',lambda:next(values))
    assert cauldron.roll_outcome(witch)==cauldron.OUTCOMES[witch][expected][0]


def test_moderator_report_private_read_only(database):
    import db_utils as db
    from cogs.game_commands.get import get_cauldron_eligibility
    db.set_cauldron_pool(1,75)
    before=database.total_changes
    interaction=SimpleNamespace(guild=SimpleNamespace(id=1),response=SimpleNamespace(send_message=AsyncMock()))
    asyncio.run(get_cauldron_eligibility.callback(interaction))
    call=interaction.response.send_message.call_args
    assert call.kwargs['ephemeral'] is True
    assert all('5 eligible' in f.name for f in call.kwargs['embed'].fields[:6])
    assert get_cauldron_eligibility.checks
    assert database.total_changes==before


@pytest.mark.parametrize('witch',['luna','raven'])
@pytest.mark.parametrize('mode',['One','many'])
def test_no_active_players_message(database,monkeypatch,witch,mode):
    monkeypatch.setattr(cast,'get_active_players_by_guild',lambda guild:[])
    interaction=SimpleNamespace(guild=SimpleNamespace(id=1),response=SimpleNamespace(send_message=AsyncMock()))
    asyncio.run(cast.cast_spell.callback(interaction,witch,mode))
    assert 'No active players' in interaction.response.send_message.call_args.args[0]


@pytest.mark.parametrize('witch',['luna','raven'])
@pytest.mark.parametrize('mode',['One','many'])
def test_new_player_draw_succeeds_without_member_cache_or_purchases(database,witch,mode):
    import db_utils as db
    db.set_cauldron_pool(1,10016)
    before=database.total_changes
    interaction=SimpleNamespace(guild=SimpleNamespace(id=1,get_member=lambda uid:None),response=SimpleNamespace(send_message=AsyncMock()))
    asyncio.run(cast.cast_spell.callback(interaction,witch,mode))
    assert 'Winners: Player' in interaction.response.send_message.call_args.args[0]
    assert cast.cast_spell.checks
    assert db.get_cauldron_pool(1)==10016
    assert database.total_changes==before
