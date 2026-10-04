import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pathlib import Path
from utils.messages import MessageLoader

@pytest.fixture(autouse=True)
def event_setup(monkeypatch,database):
    import db_utils as db
    db.set_cauldron_pool(1,10016)
    global event
    event = SimpleNamespace(mention='<#999>', permissions_for=lambda member:SimpleNamespace(view_channel=True,send_messages=True,embed_links=True,attach_files=True),send=AsyncMock(return_value=SimpleNamespace(jump_url='https://discord.com/channels/1/999/123')))
    monkeypatch.setattr(cast,'get_event_channel',lambda guild:999)


MESSAGES = Path(__file__).resolve().parents[1] / "discord-bot/utils/messages.json"

def client():
    return SimpleNamespace(message_loader=MessageLoader(str(MESSAGES)))

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
    interaction=SimpleNamespace(id=12345,client=client(),user=SimpleNamespace(id=99,mention='<@99>'),guild=SimpleNamespace(id=1),followup=SimpleNamespace(send=AsyncMock()),response=SimpleNamespace(send_message=AsyncMock(),defer=AsyncMock()))
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
    interaction=SimpleNamespace(id=12345,client=client(),user=SimpleNamespace(id=99,mention='<@99>'),guild=SimpleNamespace(id=1),followup=SimpleNamespace(send=AsyncMock()),response=SimpleNamespace(send_message=AsyncMock(),defer=AsyncMock()))
    asyncio.run(cast.cast_spell.callback(interaction,witch,mode))
    assert 'No active players' in interaction.response.send_message.call_args.args[0]


@pytest.mark.parametrize('witch',['luna','raven'])
@pytest.mark.parametrize('mode',['One','many'])
def test_new_player_draw_succeeds_without_member_cache_or_purchases(database,witch,mode):
    import db_utils as db
    db.set_cauldron_pool(1,10016)
    before=database.total_changes
    interaction=SimpleNamespace(id=12345,client=client(),user=SimpleNamespace(id=99,mention='<@99>'),guild=SimpleNamespace(id=1,me=object(),get_channel=lambda cid:event,get_member=lambda uid:None),followup=SimpleNamespace(send=AsyncMock()),response=SimpleNamespace(send_message=AsyncMock(),defer=AsyncMock()))
    asyncio.run(cast.cast_spell.callback(interaction,witch,mode))
    assert 'Player ' in event.send.call_args.kwargs['embed'].description
    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    assert interaction.followup.send.call_args.kwargs['ephemeral'] is True
    interaction.response.send_message.assert_not_awaited()
    assert cast.cast_spell.checks
    assert db.get_cauldron_pool(1)==0
    assert database.execute('SELECT sum(candy_in_bucket) FROM players WHERE guild_id=1').fetchone()[0]==10016+250


@pytest.mark.parametrize('witch,outcome', [(w,o) for w,items in cauldron.OUTCOMES.items() for o,_ in items])
def test_draw_uses_custom_json_variant_and_placeholders(database,monkeypatch,tmp_path,witch,outcome):
    import json
    data=json.loads(MESSAGES.read_text())
    data['cauldron']['draw'][witch][outcome]=['Custom {witch}/{outcome}: {winner_count} winner(s): {winners}; moderator {user}']
    path=tmp_path/'messages.json'
    path.write_text(json.dumps(data))
    monkeypatch.setattr(cauldron,'roll_outcome',lambda _:outcome)
    interaction=SimpleNamespace(id=12345,client=SimpleNamespace(message_loader=MessageLoader(str(path))),user=SimpleNamespace(id=99,mention='<@99>'),guild=SimpleNamespace(id=1,me=object(),get_channel=lambda cid:event,get_member=lambda uid:None),followup=SimpleNamespace(send=AsyncMock()),response=SimpleNamespace(send_message=AsyncMock(),defer=AsyncMock()))
    asyncio.run(cast.cast_spell.callback(interaction,witch,'One'))
    text=event.send.call_args.kwargs['embed'].description
    assert text.startswith(f'Custom {witch.title()}/{outcome}: 1 winner(s): Player ')
    assert text.endswith('moderator <@99>')
    assert 'Message not found' not in text


def test_long_custom_announcement_is_preserved_in_attachment(database,monkeypatch):
    bot_client=client()
    bot_client.message_loader.messages['cauldron']['draw']['luna']['normal']=['x'*4100+' {winners}']
    monkeypatch.setattr(cauldron,'roll_outcome',lambda _: 'normal')
    interaction=SimpleNamespace(id=12345,client=bot_client,user=SimpleNamespace(id=99,mention='<@99>'),guild=SimpleNamespace(id=1,me=object(),get_channel=lambda cid:event,get_member=lambda uid:None),followup=SimpleNamespace(send=AsyncMock()),response=SimpleNamespace(send_message=AsyncMock(),defer=AsyncMock()))
    captured=[]
    async def capture(**kwargs):
        captured.append(kwargs['file'].fp.getvalue())
        return SimpleNamespace(jump_url='https://discord.com/channels/1/999/123')
    event.send.side_effect=capture
    asyncio.run(cast.cast_spell.callback(interaction,'luna','One'))
    call=event.send.call_args
    assert len(call.kwargs['embed'].description)<=1900
    assert captured[0].startswith(b'x'*4100)


@pytest.mark.parametrize('failure',['missing','denied','send'])
def test_event_post_failures_are_private(database,monkeypatch,failure):
    import discord
    if failure=='missing':
        monkeypatch.setattr(cast,'get_event_channel',lambda guild:None)
    if failure=='denied':
        event.permissions_for=lambda member:SimpleNamespace(view_channel=True,send_messages=False,embed_links=True,attach_files=True)
    if failure=='send':
        event.send.side_effect=discord.Forbidden(SimpleNamespace(status=403,reason='Forbidden'),'Denied')
    draw=__import__('unittest.mock',fromlist=['Mock']).Mock(wraps=cauldron.roll_outcome)
    monkeypatch.setattr(cauldron,'roll_outcome',draw)
    interaction=SimpleNamespace(id=12345,client=client(),user=SimpleNamespace(id=99,mention='<@99>'),guild=SimpleNamespace(id=1,me=object(),get_channel=lambda cid:event,get_member=lambda uid:None),followup=SimpleNamespace(send=AsyncMock()),response=SimpleNamespace(send_message=AsyncMock(),defer=AsyncMock()))
    asyncio.run(cast.cast_spell.callback(interaction,'luna','One'))
    if failure=='send':
        assert interaction.followup.send.call_args.kwargs['ephemeral']
        assert 'payouts are saved' in interaction.followup.send.call_args.args[0]
        assert draw.call_count==1
    else:
        draw.assert_not_called()
        event.send.assert_not_awaited()
        assert interaction.response.send_message.call_args.kwargs['ephemeral']


def test_all_themed_variants_render_through_loader():
    loader=client().message_loader
    count=0
    for witch,outcomes in loader.messages['cauldron']['draw'].items():
        for outcome,variants in outcomes.items():
            for variant in variants:
                loader.messages['_variant_check']=variant
                text=loader.get_message('_variant_check',witch=witch.title(),outcome=outcome,winners='BloominDaisy, Megatron',winner_count=2,user='<@99>')
                assert 'BloominDaisy, Megatron' in text
                assert f'~ {witch.title()}' in text
                assert len(text)<1900
                count+=1
    assert count==18


def test_payout_splits_remainder_and_is_idempotent(database,monkeypatch):
    import db_utils as db
    monkeypatch.setattr(cauldron,'select_winners',lambda *args,**kwargs:[10,20,30])
    db.set_cauldron_pool(1,10)
    result,repeated=cauldron.award_pool(1,777,99,'luna','many')
    assert [a['amount'] for a in result['awards']]==[4,3,3]
    assert not repeated
    assert db.get_cauldron_pool(1)==0
    assert database.execute('SELECT sum(candy_in_bucket) FROM players WHERE guild_id=1').fetchone()[0]==260
    assert database.execute('SELECT sum(candy_in_bucket) FROM players WHERE guild_id=2').fetchone()[0]==250
    db.set_cauldron_pool(1,25)
    again,repeated=cauldron.award_pool(1,777,99,'luna','many')
    assert repeated and again==result
    assert db.get_cauldron_pool(1)==25
    assert database.execute('SELECT count(*) FROM cauldron_event').fetchone()[0]==1


def test_small_pool_caps_winners(database,monkeypatch):
    import db_utils as db
    db.set_cauldron_pool(1,2)
    monkeypatch.setattr(cauldron.random,'randint',lambda low,high:high)
    result,_=cauldron.award_pool(1,778,99,'raven','many')
    assert len(result['awards'])==2
    assert all(a['amount']==1 for a in result['awards'])


def test_empty_pool_has_no_awards(database):
    import db_utils as db
    db.set_cauldron_pool(1,0)
    with pytest.raises(cauldron.CauldronError,match='empty_pool'):
        cauldron.award_pool(1,779,99,'luna','One')
    assert database.execute('SELECT sum(candy_in_bucket) FROM players WHERE guild_id=1').fetchone()[0]==250


def test_payout_rolls_back_after_partial_failure(database,monkeypatch):
    import db_utils as db
    import sqlite3
    monkeypatch.setattr(cauldron,'select_winners',lambda *args,**kwargs:[10,20])
    database.execute("CREATE TRIGGER fail_second BEFORE UPDATE OF candy_in_bucket ON players WHEN NEW.player_id=20 BEGIN SELECT RAISE(ABORT,'test failure'); END")
    database.commit()
    with pytest.raises(sqlite3.IntegrityError):
        cauldron.award_pool(1,780,99,'luna','many')
    assert database.execute('SELECT sum(candy_in_bucket) FROM players WHERE guild_id=1').fetchone()[0]==250
    assert db.get_cauldron_pool(1)==10016
    assert database.execute('SELECT count(*) FROM cauldron_event').fetchone()[0]==0


@pytest.mark.parametrize('witch',['luna','raven'])
def test_embed_image_title_payout_and_failed_post_retry(database,witch):
    import discord
    import db_utils as db
    interaction=SimpleNamespace(id=99999,client=client(),user=SimpleNamespace(id=99,mention='<@99>'),guild=SimpleNamespace(id=1,me=object(),get_channel=lambda cid:event,get_member=lambda uid:None),followup=SimpleNamespace(send=AsyncMock()),response=SimpleNamespace(send_message=AsyncMock(),defer=AsyncMock()))
    event.send.side_effect=discord.Forbidden(SimpleNamespace(status=403,reason='Forbidden'),'Denied')
    asyncio.run(cast.cast_spell.callback(interaction,witch,'One'))
    embed=event.send.call_args.kwargs['embed']
    assert 'A spell has been cast!' in embed.title
    assert witch.title() in embed.title
    assert embed.image.url==interaction.client.message_loader.messages[f'who_is_{witch}']['image_url']
    assert '+10016 candy' in embed.fields[0].value
    assert db.get_cauldron_pool(1)==0
    assert 'payouts are saved' in interaction.followup.send.call_args.args[0]
    asyncio.run(cast.cast_spell.callback(interaction,witch,'One'))
    assert event.send.await_count==1
    assert 'already awarded' in interaction.followup.send.call_args.args[0]
    assert database.execute('SELECT sum(candy_in_bucket) FROM players WHERE guild_id=1').fetchone()[0]==10266
