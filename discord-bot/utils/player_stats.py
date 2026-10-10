"""Private moderator statistics, with all labels sourced from messages.json."""
import discord
import db_utils as db
import game_stats as stats
import potions
import player_state as state
from utils.player import calculate_evilness, calculate_sweetness, calculate_thief_success_rate
from utils.artwork import image_url


def player_stats_embeds(interaction, user, section):
    guild=interaction.guild.id
    data=db.get_player_data(user.id,guild)
    if not data:
        return []
    message=interaction.client.message_loader.get_message
    def text(key, **values):
        return message('player_stats',key,**values)
    metrics=stats.totals(guild,user.id)
    bottles,effects=potions.inventory(guild,user.id)
    legacy=db.get_db_connection().execute('SELECT tricks_blocked,luna_summons FROM potion_stats WHERE guild_id=? AND player_id=?',(guild,user.id)).fetchone() or (0,0)
    cauldron=db.get_db_connection().execute('SELECT cauldron_contributions,cauldron_wins,cauldron_rewards_received FROM players WHERE guild_id=? AND player_id=?',(guild,user.id)).fetchone()
    status='inactive' if not data['active'] else 'frozen' if state.freeze_info(guild,user.id) else 'protected' if state.protection_info(guild,user.id) else 'active'
    values=dict(data,**{k:metrics.get(k,0) for k in ('trick_attempts','blocked_attempts','redirected_attempts','purchased','activated','triggered','spent','gifted','protection_purchased_seconds')})
    values.update(user=discord.utils.escape_markdown(user.display_name[:64]),status=text(status),bottles=sum(bottles.values()),charges=sum(effects.values()),wards=legacy[0],summons=legacy[1],contributions=cauldron[0],cauldron_wins=cauldron[1],cauldron_rewards=cauldron[2],protection_used_seconds=stats.protection_seconds(guild,user.id),resolved=data['successful_tricks']+data['failed_tricks'])
    embeds=[]
    if section in ('stats','all'):
        embed=discord.Embed(title=text('title',**values),color=discord.Color.purple())
        embed.set_thumbnail(url=image_url('inventory'))
        for key in ('overview','tricks','treats','pumpkins','cauldron','potions','protection'):
            embed.add_field(name=text(key+'_title'),value=text(key,**values),inline=False)
        import passive_income as income
        earnings=income.status(guild,user.id)
        embed.add_field(name=text('earnings_title'),value=text('earnings',**earnings),inline=False)
        embed.set_footer(text=text('tracking_note'))
        embeds.append(embed)
        details=stats.potion_details(guild,user.id)
        embed=discord.Embed(title=text('potion_title'),color=discord.Color.purple())
        for key in (*potions.CATALOG,'veil'):
            row=details.get(key,{})
            name=potions.CATALOG[key].name if key in potions.CATALOG else text('veil')
            embed.add_field(name=name,value=text('potion_row',bottles=bottles.get(key,0),charges=effects.get(key,0),**{metric:row.get(metric,0) for metric in ('purchased','activated','triggered','spent','gifted','defended')}),inline=False)
        embeds.append(embed)
    if section in ('hidden_values','all'):
        embed=discord.Embed(title=text('hidden_title'),description=text('hidden',sweetness=round(calculate_sweetness(data['total_candy_given'],data['total_candy_stolen'])*100,2),evilness=round(calculate_evilness(data['total_candy_given'],data['total_candy_stolen'])*100,2),chance=round(calculate_thief_success_rate(data['candy_in_bucket'])*100,2)),color=discord.Color.purple())
        embeds.append(embed)
    return embeds
