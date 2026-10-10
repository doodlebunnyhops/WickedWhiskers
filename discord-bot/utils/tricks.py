"""Shared percentage trick settlement, inside the caller's transaction."""
import random
from fractions import Fraction
import discord
import db_utils as db
from utils import potion_gameplay as perks


def percentage(balance, low, high):
    if balance <= 0:
        return 0
    fraction = (Fraction(low) + Fraction(random.random()) * (high-low)) / 100
    value = balance*fraction + Fraction(1,2)
    return min(balance,max(1,value.numerator//value.denominator))


def success_rate(attacker, target):
    return float(Fraction(1,10)+Fraction(4*target,5*(attacker+target))) if attacker+target else .5


def settle(interaction, target, responses):
    guild=interaction.guild.id
    uid=interaction.user.id
    reflected=uid==target.id
    conn=db.get_db_connection()
    a=db.get_player_data(uid,guild)['candy_in_bucket']
    b=db.get_player_data(target.id,guild)['candy_in_bucket']
    rate=perks.prepare_rate(interaction,responses,success_rate(a,b))
    hit=perks.roll_trick(interaction,responses,rate)
    base=percentage(b,2,6)
    if hit:
        if b>100 and random.random()<.001:
            kind,amount='wipeout',b
        elif random.random()<.10:
            kind,amount='both',percentage(min(a,b),1,3)
        elif random.random()<.15 and base>5:
            kind,amount='reclaimed',base-1
        else:
            kind,amount='ordinary',base
            if not reflected:
                amount=perks.sticky_amount(interaction,responses,target,amount,b)
    elif random.random()<.10:
        kind,amount='both',percentage(min(a,b),1,3)
    elif random.random()<.10:
        kind,amount='consolation',min(b,max(1,(base+1)//2))
    else:
        kind,amount='failed',0 if reflected else percentage(a,1,3)

    def change(player,delta,lost=0,stolen=0,success=0,failed=0):
        conn.execute('UPDATE players SET candy_in_bucket=candy_in_bucket+?,total_candy_lost=total_candy_lost+?,total_candy_stolen=total_candy_stolen+?,successful_tricks=successful_tricks+?,failed_tricks=failed_tricks+? WHERE guild_id=? AND player_id=?',(delta,lost,stolen,success,failed,guild,player))
    def pool(player,n):
        db.update_cauldron_pool(guild,n)
        db.update_cauldron_contribution(player,guild,n)
    if reflected:
        change(uid,-amount,lost=amount,failed=1)
        if amount:pool(uid,amount)
        key='reflect_wipeout' if kind=='wipeout' else 'reflect_loss' if amount else 'reflect_miss'
    elif kind=='both':
        change(uid,-amount,lost=amount,failed=1)
        change(target.id,-amount,lost=amount)
        pool(uid,amount);pool(target.id,amount)
        key='both'
    elif kind=='failed':
        change(uid,-amount,lost=amount,failed=1)
        change(target.id,amount)
        key='failed'
    else:
        change(uid,amount,stolen=amount,success=1)
        change(target.id,-amount,lost=amount)
        key=kind
    message=interaction.client.message_loader.get_message
    body=message('scaled_tricks',key,user=interaction.user.mention,target=target.mention,amount=amount)
    embed=discord.Embed(title=message('scaled_tricks','title'),description=body,color=discord.Color.dark_purple())
    embed.set_thumbnail(url=message('who_is_raven','image_url'))
    responses.append_event(message=embed)
    return dict(kind=kind,amount=amount,reflected=reflected)
