"""Bucket resets only touch candy. Full progress resets are explicit and confirmed."""
import discord
from discord import app_commands
import db_utils as db
import potions
import player_state as state
from utils.checks import check_if_has_permission_or_role
from admin_settings import AdminView, text

reset_group=app_commands.Group(name='reset',description='Reset buckets or explicitly reset full player progress')


def apply_reset(guild_id,action_id,actor_id,player_ids,full=False):
    ids=list(dict.fromkeys(player_ids))
    if full and len(ids)!=1:
        raise ValueError('Full reset requires exactly one player')
    with db.transaction() as conn:
        previous=potions.prior_action(conn,guild_id,action_id,actor_id,'admin_reset')
        if previous is not None:return previous
        changed=[]
        for uid in ids:
            row=conn.execute('SELECT active FROM players WHERE guild_id=? AND player_id=?',(guild_id,uid)).fetchone()
            if row is None:continue
            if full:
                db.reset_player_data(uid,guild_id)
            elif row[0]:
                conn.execute('UPDATE players SET candy_in_bucket=50 WHERE guild_id=? AND player_id=?',(guild_id,uid))
            else:continue
            changed.append(uid)
        result=dict(count=len(changed),full=full)
        potions.record_action(conn,guild_id,action_id,actor_id,'admin_reset',result)
        return result


class ConfirmReset(AdminView):
    def __init__(self,interaction,ids,full=False):
        super().__init__(interaction)
        self.ids=list(ids)
        self.full=full
        self.action_id=interaction.id
        for child in self.children:child.label=text(child.custom_id)

    @discord.ui.button(custom_id='confirm_reset',style=discord.ButtonStyle.danger)
    async def confirm(self,interaction,button):
        result=apply_reset(self.guild_id,self.action_id,self.owner_id,self.ids,self.full)
        await interaction.response.edit_message(content=text('full_reset_done' if self.full else 'bucket_reset_done',count=result['count']),view=None)
        self.stop()

    @discord.ui.button(custom_id='cancel',style=discord.ButtonStyle.secondary)
    async def cancel(self,interaction,button):
        await interaction.response.edit_message(content=text('cancelled'),view=None)
        self.stop()


class PlayerSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder=text('choose_players'),min_values=1,max_values=25)

    async def callback(self,interaction):
        ids=[u.id for u in self.values]
        await interaction.response.edit_message(content=text('bucket_reset_confirm',count=len(ids)),view=ConfirmReset(interaction,ids))


class PickPlayers(AdminView):
    def __init__(self,interaction):
        super().__init__(interaction)
        self.add_item(PlayerSelect())


@reset_group.command(name='bucket',description='Reset one joined player’s bucket to 50 candy without clearing stats')
@check_if_has_permission_or_role()
async def reset_bucket(interaction:discord.Interaction,user:discord.Member):
    result=apply_reset(interaction.guild_id,interaction.id,interaction.user.id,[user.id])
    await interaction.response.send_message(text('bucket_reset_done',count=result['count']),ephemeral=True)


@reset_group.command(name='buckets',description='Reset selected or all joined players’ buckets to 50; confirmation required')
@check_if_has_permission_or_role()
@app_commands.choices(scope=[app_commands.Choice(name='Selected players',value='selected'),app_commands.Choice(name='All joined players',value='all')])
async def reset_buckets(interaction:discord.Interaction,scope:str):
    if scope=='all':
        ids=[r[0] for r in db.get_db_connection().execute('SELECT player_id FROM players WHERE guild_id=? AND active=1',(interaction.guild_id,))]
        await interaction.response.send_message(text('bucket_reset_confirm',count=len(ids)),view=ConfirmReset(interaction,ids),ephemeral=True)
    else:
        await interaction.response.send_message(text('choose_players'),view=PickPlayers(interaction),ephemeral=True)


@reset_group.command(name='player',description='Full player reset: clears progress, inventory, effects and freeze; confirmation required')
@check_if_has_permission_or_role()
async def reset_player(interaction:discord.Interaction,user:discord.Member):
    if db.get_player_data(user.id,interaction.guild_id) is None:
        await interaction.response.send_message(state.text('reset_missing'),ephemeral=True)
        return
    await interaction.response.send_message(text('full_reset_confirm',player=user.mention),view=ConfirmReset(interaction,[user.id],full=True),ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
