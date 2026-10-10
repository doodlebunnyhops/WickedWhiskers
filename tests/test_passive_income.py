import asyncio
import sqlite3
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
import db_utils as db
import passive_income as income
import player_state as state
from utils.messages import default_messages


@pytest.fixture
def clock(database,monkeypatch):
    current=[0]
    monkeypatch.setattr(income.time,'time',lambda:current[0])
    database.execute('UPDATE passive_earnings SET last_at=0')
    database.commit()
    return current


def test_partial_progress_and_no_auto_credit(database,clock):
    assert income.status(1,10,599)['pending']==0
    assert income.status(1,10,600)['pending']==1
    assert income.status(1,10,1199)['pending']==1
    assert income.status(1,10,1200)['pending']==2
    assert db.get_player_data(10,1)['candy_in_bucket']==50
    assert income.status(2,10,600)['pending']==1


def test_daily_cap_midnight_and_repeated_claim(database,clock):
    clock[0]=60000
    assert income.status(1,10)['earned_today']==100
    r=income.claim(1,10,123)
    assert r==dict(amount=100,repeated=False)
    assert income.claim(1,10,123)==dict(amount=100,repeated=True)
    assert income.status(1,10,86399)['pending']==0
    assert income.status(1,10,86400)['earned_today']==0
    assert income.status(1,10,87000)['pending']==1
    assert db.get_player_data(10,1)['candy_in_bucket']==150
    assert database.execute('SELECT COUNT(*) FROM passive_claims').fetchone()[0]==1


def test_reserve_cap_discards_capped_time_and_preserves_daily_limit(database,clock):
    clock[0]=7*86400
    assert income.status(1,10)['pending']==300
    assert income.claim(1,10,'claim')['amount']==300
    assert income.claim(1,10,'again')['amount']==0
    assert income.status(1,10,clock[0]+599)['pending']==0
    assert income.status(1,10,clock[0]+600)['pending']==1
    assert income.status(1,10,clock[0]+86400-1)['pending']==100
    assert income.status(1,10,clock[0]+86400-1)['total_earned']==400


def test_pause_settle_offline_resume_and_partial_time(database,clock):
    clock[0]=900;db.set_game_disabled(1,True)
    clock[0]=10*86400;db.set_game_setting(1,game_disabled=False)
    assert income.status(1,10)['pending']==1
    assert income.status(1,20)['pending']==1 # never opened bucket
    assert income.status(1,10,clock[0]+300)['pending']==2


def test_pause_rejects_claim_and_preserves_earnings(database,clock):
    clock[0]=600;db.set_game_disabled(1,True)
    with pytest.raises(income.IncomeError,match='paused'):income.claim(1,10,'x')
    assert income.status(1,10)['pending']==1


def test_freeze_expiry_update_and_unfreeze(database,clock):
    clock[0]=900;state.freeze(1,10,20,10,'test','f')
    clock[0]=1200
    with pytest.raises(income.IncomeError,match='frozen'):income.claim(1,10,'x')
    assert income.status(1,10)['pending']==1
    clock[0]=1800
    assert income.status(1,10)['pending']==2 # 300 seconds saved + 300 since expiry
    state.freeze(1,10,20,None,'test','f2')
    clock[0]=86400;state.freeze(1,10,20,10,'updated','f3',update=True)
    clock[0]=86500;state.unfreeze(1,10,20,'u')
    clock[0]+=600
    assert income.status(1,10)['pending']==3


def test_leaving_reset_and_rejoining_cannot_reset_daily_quota(database,clock):
    clock[0]=60000;state.leave(1,10)
    assert income.status(1,10)['pending']==0
    assert income.status(1,10)['total_forfeited']==100
    clock[0]+=3600;state.join(1,10)
    assert income.status(1,10,80000)['pending']==0
    db.reset_player_data(10,1)
    assert income.status(1,10,86000)['pending']==0
    assert income.status(1,10,87000)['pending']==1


def test_deleted_member_and_new_record_keep_daily_quota(database,clock):
    clock[0]=60000;db.delete_player_data(10,1)
    clock[0]+=1000;db.create_player_data(10,1)
    assert income.status(1,10,86000)['pending']==0


def test_veil_allowed_and_game_stats_unchanged(database,clock):
    database.execute('INSERT INTO player_protection VALUES(1,10,0,10000,\'fixed\',5,500,3600)');database.commit()
    clock[0]=600
    before=db.get_player_data(10,1)
    assert income.claim(1,10,'x')['amount']==1
    after=db.get_player_data(10,1)
    before.pop('candy_in_bucket');after.pop('candy_in_bucket')
    assert before==after
    assert db.get_cauldron_pool(1)==0


def test_rollback_and_balance_limit(database,clock):
    clock[0]=600
    database.execute("CREATE TRIGGER fail_claim BEFORE INSERT ON passive_claims BEGIN SELECT RAISE(ABORT,'fail'); END");database.commit()
    with pytest.raises(sqlite3.Error):income.claim(1,10,'fail')
    assert db.get_player_data(10,1)['candy_in_bucket']==50
    assert income.status(1,10)['pending']==1
    database.execute('DROP TRIGGER fail_claim');database.commit()
    db.update_player_field(10,1,'candy_in_bucket',2**63-1)
    with pytest.raises(income.IncomeError,match='balance_limit'):income.claim(1,10,'max')
    assert income.status(1,10)['pending']==1


def test_owner_and_guild_scoped_claims(database,clock):
    clock[0]=600
    income.claim(1,10,'same')
    with pytest.raises(income.IncomeError,match='not_owner'):income.claim(1,20,'same')
    assert income.claim(2,10,'same')['amount']==1


def test_restart_preserves_clock_and_ledger(database,clock,tmp_path):
    clock[0]=900;income.claim(1,10,'one')
    path=tmp_path/'state.db';target=sqlite3.connect(path);database.backup(target);target.close()
    db.close_db_connection();db.conn=sqlite3.connect(path)
    clock[0]=1200;db.initialize_database()
    assert income.status(1,10)['pending']==1
    assert income.claim(1,10,'one')['repeated']
    assert db.get_player_data(10,1)['candy_in_bucket']==51


def test_view_ownership_and_claim_refresh(database,clock):
    from modals.earnings import EarningsView
    async def run():
        caller=NS(user=NS(id=10),guild=NS(id=1),id=77,client=NS(message_loader=default_messages()),response=NS(send_message=AsyncMock(),defer=AsyncMock()),followup=NS(send=AsyncMock()),edit_original_response=AsyncMock())
        v=EarningsView(caller)
        assert await v.interaction_check(caller)
        clock[0]=600
        await v.collect.callback(caller)
        caller.edit_original_response.assert_awaited_once()
        assert db.get_player_data(10,1)['candy_in_bucket']==51
        caller.user.id=20
        assert not await v.interaction_check(caller)
        caller.user.id=10;caller.guild.id=2
        assert not await v.interaction_check(caller)
    asyncio.run(run())


def test_multiple_buttons_never_claim_twice_and_failed_action_cannot_backdate(database,clock):
    clock[0]=600
    assert income.claim(1,10,'first')['amount']==1
    assert income.claim(1,10,'second')['amount']==0
    assert income.status(1,10,100)['pending']==0
    assert income.status(1,10,1200)['pending']==1


def test_installation_does_not_backfill_previous_season(database,clock):
    database.execute('DELETE FROM passive_earnings');database.commit()
    clock[0]=999999;db.initialize_database()
    assert income.status(1,10)['pending']==0
    assert income.status(1,10,clock[0]+600)['pending']==1


def test_paused_freeze_overlap_counts_eligible_time_only(database,clock):
    clock[0]=300;state.freeze(1,10,20,20,'f','f')
    clock[0]=600;db.set_game_disabled(1,True)
    clock[0]=1800;db.set_game_disabled(1,False)
    # Freeze expires during pause; both blocked intervals must be excluded.
    assert income.status(1,10,2100)['pending']==1


def test_existing_indefinite_frozen_player_earns_nothing(database,clock):
    database.execute('UPDATE players SET frozen=1 WHERE guild_id=1 AND player_id=10');database.commit()
    assert income.status(1,10,86400)['pending']==0


def test_claim_late_day_does_not_allow_extra_daily_earnings(database,clock):
    clock[0]=3*86400-1000
    assert income.claim(1,10,'all')['amount']==300
    assert income.status(1,10,3*86400-1)['pending']==0
    assert income.status(1,10,3*86400+600)['pending']==1
