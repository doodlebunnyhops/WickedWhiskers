import logging
import discord
from discord import app_commands
from discord.ext import commands
import db_utils as db
import player_state as state
from utils.artwork import image_url
from utils.utils import has_role_or_permission
from modals.shop import OwnedView, tell

logger=logging.getLogger('bot')


async def moderator_change(interaction, player, minutes=None, reason='', update=False, thaw=False):
    await interaction.response.defer(ephemeral=True)
    if not has_role_or_permission(interaction.user, interaction.guild.id):
        await tell(interaction,state.text('denied'))
        return
    if player.bot or player.guild.id != interaction.guild.id:
        await tell(interaction,state.text('invalid_target'))
        return
    channel_id=db.get_event_channel(interaction.guild.id)
    channel=interaction.guild.get_channel(channel_id) if channel_id else None
    if channel is None:
        await tell(interaction,state.text('event_missing'))
        return
    permissions=channel.permissions_for(interaction.guild.me)
    if not (permissions.view_channel and permissions.send_messages and permissions.embed_links):
        await tell(interaction,state.text('event_denied'))
        return
    try:
        if thaw:
            result,repeated=state.unfreeze(interaction.guild.id,player.id,interaction.user.id,interaction.id)
        else:
            result,repeated=state.freeze(interaction.guild.id,player.id,interaction.user.id,minutes,reason,interaction.id,update)
    except state.StateError as error:
        await tell(interaction,str(error))
        return
    if repeated:
        await tell(interaction,state.text('already_processed'))
        return
    embed=discord.Embed(title=state.text('thaw_title' if thaw else 'freeze_title'),description=state.text('thaw_public' if thaw else 'freeze_public',player=player.mention),color=discord.Color.blue())
    if not thaw:
        embed.set_thumbnail(url=image_url('frozen_player'))
    try:
        await channel.send(embed=embed,allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException:
        logger.exception('Freeze status saved but event announcement failed')
        await tell(interaction,state.text('event_failed'))
        return
    await tell(interaction,state.text('thaw_saved' if thaw else 'freeze_saved',player=player.mention))


@app_commands.command(name='freeze',description='Freeze a player and return their active potions to inventory.')
@app_commands.guild_only()
@app_commands.describe(player='Player to freeze', minutes='Duration in minutes; omit for indefinite',reason='Private reason shown to the frozen player',update='Explicitly replace an existing freeze duration and reason')
async def freeze_command(interaction:discord.Interaction,player:discord.Member,minutes:app_commands.Range[int,1,525600]=None,reason:str='',update:bool=False):
    await moderator_change(interaction,player,minutes,reason,update)


@app_commands.command(name='unfreeze',description='Remove a moderator freeze without resetting the player.')
@app_commands.guild_only()
async def unfreeze_command(interaction:discord.Interaction,player:discord.Member):
    await moderator_change(interaction,player,thaw=True)


class LeaveConfirm(OwnedView):
    def __init__(self,interaction):
        super().__init__(interaction.user.id,interaction.guild.id)
        self.finished=False
        self.confirm.label=state.text('leave_confirm_button')
        self.cancel.label=state.text('cancel_button')

    @discord.ui.button(style=discord.ButtonStyle.danger)
    async def confirm(self,interaction,button):
        if self.finished:
            await tell(interaction,state.text('already_processed'))
            return
        self.finished=True
        now=state.clock()
        changed=state.leave(self.guild_id,self.owner_id,now)
        self.stop()
        await interaction.response.edit_message(content=state.text('left',expiry=now+3600) if changed else state.text('not_joined'),view=None)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def cancel(self,interaction,button):
        self.finished=True
        self.stop()
        await interaction.response.edit_message(content=state.text('cancelled'),view=None)


async def reconcile_members(guild):
    if not guild.chunked:
        await guild.chunk(cache=True)
    if not guild.chunked:
        return
    members={member.id for member in guild.members}
    # Use raw active records, including frozen and protected players.
    ids=[r[0] for r in db.get_db_connection().execute('SELECT player_id FROM players WHERE guild_id=? AND active=1',(guild.id,))]
    for uid in ids:
        if uid not in members:
            state.leave(guild.id,uid)


class Participation(commands.Cog):
    @app_commands.command(name='leave',description='Leave the game, forfeiting progress with a one-hour rejoin delay.')
    @app_commands.guild_only()
    async def leave_command(self,interaction:discord.Interaction):
        if not db.is_player_active(interaction.user.id,interaction.guild.id):
            await tell(interaction,state.text('not_joined'))
            return
        await interaction.response.send_message(state.text('leave_warning'),view=LeaveConfirm(interaction),ephemeral=True)

    @commands.Cog.listener()
    async def on_member_remove(self,member):
        if not member.bot:
            state.leave(member.guild.id,member.id)

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                await reconcile_members(guild)
            except discord.DiscordException:
                logger.exception('Could not verify members for guild %s; leaving saved players unchanged',guild.id)

    def __init__(self,bot):
        self.bot=bot


async def setup(bot):
    await bot.add_cog(Participation(bot))
