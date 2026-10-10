import pytest
import db_utils as db
import potions
from utils import tricks,player
from test_more_potions import interaction,member,activate


def run(monkeypatch,rolls,*,a=50,b=5000,target=20):
    db.update_player_field(10,1,'candy_in_bucket',a)
    if target!=10:db.update_player_field(target,1,'candy_in_bucket',b)
    it=iter(rolls)
    monkeypatch.setattr(tricks.random,'random',lambda:next(it))
    with db.transaction():return tricks.settle(interaction(),member(target),player._TrickResponses())


@pytest.mark.parametrize('balance',[0,1,50,100,5000,2**63-1])
@pytest.mark.parametrize('bounds',[(2,6),(1,3),(25,50)])
def test_percentage_endpoints(balance,bounds,monkeypatch):
    from fractions import Fraction
    for r in (0,.999999):
        monkeypatch.setattr(tricks.random,'random',lambda:r)
        n=tricks.percentage(balance,*bounds)
        expected=Fraction(balance)*(Fraction(bounds[0])+Fraction(r)*(bounds[1]-bounds[0]))/100+Fraction(1,2)
        assert n==(min(balance,max(1,expected.numerator//expected.denominator)) if balance else 0)


def test_rate_relative_and_continuous():
    assert tricks.success_rate(50,50)==tricks.success_rate(5000,5000)==.5
    assert tricks.success_rate(50,5000)>.89
    assert tricks.success_rate(5000,50)<.11
    assert abs(tricks.success_rate(499,5000)-tricks.success_rate(500,5000))<.001


@pytest.mark.parametrize('target',[20,10])
def test_wipeout_sticky_preserved_and_pool_once(database,monkeypatch,target):
    activate('sticky')
    result=run(monkeypatch,[0,.5,0],a=5000,b=5000,target=target)
    assert result['kind']=='wipeout' and result['amount']==5000
    assert potions.inventory(1,10)[1]['sticky']==3
    assert db.get_player_data(target,1)['candy_in_bucket']==0
    assert db.get_cauldron_pool(1)==(5000 if target==10 else 0)
    assert db.get_cauldron_contribution(10,1)==(5000 if target==10 else 0)
    assert db.get_player_data(10,1)['candy_in_bucket']==(0 if target==10 else 10000)


def test_no_wipeout_at_100(database,monkeypatch):
    r=run(monkeypatch,[0,.5,0,.5],b=100)
    assert r['kind']=='both' and r['amount']==1


@pytest.mark.parametrize('a,b',[(50,5000),(5000,50),(500,500),(0,5000)])
def test_shared_loss_uses_smaller_bucket(database,monkeypatch,a,b):
    rolls=[0,.5]+([.9] if b>100 else [])+[0,.5]
    r=run(monkeypatch,rolls,a=a,b=b)
    n=min(a,b)//50
    assert r['amount']==n and db.get_cauldron_pool(1)==2*n
    assert db.get_player_data(10,1)['candy_in_bucket']==a-n
    assert db.get_player_data(20,1)['candy_in_bucket']==b-n


def test_sticky_percentage_bonus_and_guild_isolation(database,monkeypatch):
    activate('sticky')
    # 4% of 5000 = 200, midpoint bonus 37.5% = 75.
    r=run(monkeypatch,[0,.5,.9,.9,.9,.5])
    assert r['amount']==275 and r['kind']=='ordinary'
    assert potions.inventory(1,10)[1]['sticky']==2
    assert db.get_player_data(10,2)['candy_in_bucket']==50
    assert db.get_player_data(20,2)['candy_in_bucket']==50
    assert db.get_player_data(10,1)['total_candy_stolen']==275


def test_failure_and_consolation_amounts(database,monkeypatch):
    r=run(monkeypatch,[.99,.5,.9,.9,.5],a=5000,b=5000)
    assert r['kind']=='failed' and r['amount']==100
    r=run(monkeypatch,[.99,.5,.9,0],a=5000,b=5000)
    assert r['kind']=='consolation' and r['amount']==100


def test_redirect_uses_final_bucket(database,monkeypatch):
    from utils import potion_gameplay as perks
    activate('mirror',20)
    db.update_player_field(20,1,'candy_in_bucket',50)
    db.update_player_field(30,1,'candy_in_bucket',5000)
    monkeypatch.setattr(perks,'choose_redirect',lambda choices:member(30))
    it=iter([0,.5,.9,.9,.9]);monkeypatch.setattr(tricks.random,'random',lambda:next(it))
    with db.transaction():player._resolve_trick(interaction(),member(20),player._TrickResponses())
    assert db.get_player_data(20,1)['candy_in_bucket']==50
    assert db.get_player_data(30,1)['candy_in_bucket']==4800
    assert db.get_player_data(10,1)['candy_in_bucket']==250
