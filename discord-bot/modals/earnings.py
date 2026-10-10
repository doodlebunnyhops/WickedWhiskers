"""Private owner-bound claim controls. No timers or Discord presence lookups."""
import logging
import sqlite3
import discord
import passive_income as income
import db_utils as db
from utils.artwork import icon_embed

logger=logging.getLogger('bot')


def text(interaction,key,**values):
    return interaction.client.message_loader.get_message('passive_income',key,**values)


def details(interaction, result):
    summary=text(interaction,'summary',**result)
    if result['pending']>=income.RESERVE_CAP:
        summary+='\n'+text(interaction,'reserve_full')
    elif result['earned_today']>=income.DAILY_CAP:
        summary+='\n'+text(interaction,'daily_full',**result)
    import player_state as state
    if state.freeze_info(interaction.guild.id,interaction.user.id):
        summary+='\n'+text(interaction,'frozen')
    elif db.get_game_settings(interaction.guild.id)[0]:
        summary+='\n'+text(interaction,'paused')
    return summary


class EarningsView(discord.ui.View):
    def __init__(self,interaction):
        super().__init__(timeout=600)
        self.owner_id=interaction.user.id
        self.guild_id=interaction.guild.id
        self.collect.label=text(interaction,'button')

    async def interaction_check(self,interaction):
        if interaction.user.id!=self.owner_id or interaction.guild.id!=self.guild_id:
            await interaction.response.send_message(text(interaction,'not_owner'),ephemeral=True)
            return False
        return True

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def collect(self,interaction,button):
        await interaction.response.defer(ephemeral=True)
        try:
            result=income.claim(self.guild_id,self.owner_id,interaction.id)
        except income.IncomeError as error:
            reply=text(interaction,str(error))
            if str(error)=='frozen':
                import player_state as state
                try:
                    state.require(self.guild_id,self.owner_id,'earnings')
                except state.StateError as restriction:
                    reply=str(restriction)
            await interaction.followup.send(reply,ephemeral=True)
            return
        except sqlite3.Error:
            logger.exception('Passive income claim rolled back')
            await interaction.followup.send(text(interaction,'failed'),ephemeral=True)
            return
        key='repeated' if result['repeated'] else 'claimed' if result['amount'] else 'nothing'
        # Replace the bucket view with a fresh one; no stale balance remains displayed.
        try:
            data=db.get_player_data(self.owner_id,self.guild_id)
            if data is None:
                await interaction.followup.send(text(interaction,'not_joined'),ephemeral=True)
                return
            current=income.status(self.guild_id,self.owner_id)
            content=text(interaction,key,**result)+'\n\n'+text(interaction,'balance',amount=data['candy_in_bucket'])+'\n\n'+details(interaction,current)
            await interaction.edit_original_response(content=None,embed=icon_embed(content,'candy_bucket'),view=EarningsView(interaction))
        except (discord.HTTPException,sqlite3.Error):
            logger.exception("Claim saved but bucket refresh failed")
            await interaction.followup.send(text(interaction,'display_failed',amount=result['amount']),ephemeral=True)
