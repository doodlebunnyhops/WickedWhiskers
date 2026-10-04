"""Private protection checkout, status, and per-server shop settings."""
import discord
import potions
import player_state as state
from modals.shop import OwnedView, OwnedModal, tell


def status_text(guild_id,player_id):
    shield=state.protection_info(guild_id,player_id)
    lines=[state.text('protection_active',expiry=shield['end'],mode=state.text('mode_'+shield['mode'])) if shield else state.text('protection_inactive')]
    count=state.credits(guild_id,player_id)
    if count:
        lines.append(state.text('protection_credit',count=count))
    conn=state.db.get_db_connection()
    row=conn.execute('SELECT available_at FROM protection_cooldowns WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
    if row and row[0]>state.clock():
        lines.append(state.text('cooldown_status',expiry=row[0]))
    return '\n'.join(lines)


async def open_protection(interaction):
    config=state.settings(interaction.guild_id)
    await interaction.response.send_message(state.text('protection_intro',**config)+'\n\n'+status_text(interaction.guild_id,interaction.user.id),view=ProtectionView(interaction.user.id,interaction.guild_id),ephemeral=True)


class ProtectionView(OwnedView):
    def __init__(self,owner_id,guild_id):
        super().__init__(owner_id,guild_id)
        self.buy.label=state.text('protection_buy_button')
        self.end.label=state.text('protection_end_button')
        active=state.protection_info(guild_id,owner_id)
        self.buy.disabled=bool(active)
        self.end.disabled=not active

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def buy(self,interaction,button):
        try:
            potions.eligible(self.guild_id,self.owner_id)
            state.require(self.guild_id,self.owner_id,'use')
            await interaction.response.send_modal(ProtectionModal(self.owner_id,self.guild_id))
        except potions.PotionError as error:
            await tell(interaction,str(error))

    @discord.ui.button(style=discord.ButtonStyle.danger)
    async def end(self,interaction,button):
        await interaction.response.send_message(state.text('end_warning'),view=EndConfirm(self.owner_id,self.guild_id,str(interaction.id)),ephemeral=True)


class ProtectionModal(OwnedModal):
    def __init__(self,owner_id,guild_id):
        super().__init__(owner_id,guild_id,title=state.text('protection_modal_title'))
        self.mode=discord.ui.Select(options=[discord.SelectOption(label=state.text('mode_'+mode),value=mode) for mode in ('fixed','budget')])
        self.units=discord.ui.TextInput(min_length=1,max_length=12)
        self.add_item(discord.ui.Label(text=state.text('mode_label'),component=self.mode))
        self.add_item(discord.ui.Label(text=state.text('units_label'),description=state.text('units_hint'),component=self.units))

    async def on_submit(self,interaction):
        try:
            quoted=state.quote(self.guild_id,self.owner_id,self.mode.values[0],int(self.units.value))
            view=ProtectionCheckout(self.owner_id,self.guild_id,quoted,str(interaction.id))
            await interaction.response.send_message(view.summary(),view=view,ephemeral=True)
        except (ValueError,potions.PotionError) as error:
            await tell(interaction,str(error) if isinstance(error,potions.PotionError) else state.text('bad_duration'))


class ProtectionCheckout(OwnedView):
    def __init__(self,owner_id,guild_id,quoted,order_id):
        super().__init__(owner_id,guild_id)
        self.quoted,self.order_id,self.finished=quoted,order_id,False
        self.confirm.label=state.text('confirm_protection_button')
        self.cancel.label=state.text('cancel_button')

    def summary(self):
        q=self.quoted
        return state.text('protection_quote',fee=q['fee'],rate=q['config']['rate'],reserve=q['reserve'],minutes=q['minutes'],total=q['total'],cooldown=q['config']['cooldown'],mode=state.text('mode_'+q['mode']))+'\n'+state.text('refund_'+q['mode'])

    @discord.ui.button(style=discord.ButtonStyle.success)
    async def confirm(self,interaction,button):
        if self.finished:
            await tell(interaction,state.text('already_processed'))
            return
        try:
            result=state.buy_protection(self.guild_id,self.owner_id,self.quoted,self.order_id)
        except potions.PotionError as error:
            await tell(interaction,str(error))
            return
        self.finished=True
        self.stop()
        await interaction.response.edit_message(content=state.text('protection_started',expiry=result['end'],amount=result['total']),view=ProtectionView(self.owner_id,self.guild_id))

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def cancel(self,interaction,button):
        self.finished=True
        self.stop()
        await interaction.response.edit_message(content=state.text('cancelled'),view=None)


class EndConfirm(OwnedView):
    def __init__(self,owner_id,guild_id,order_id):
        super().__init__(owner_id,guild_id)
        self.order_id=order_id
        self.confirm.label=state.text('protection_end_button')
        self.cancel.label=state.text('cancel_button')

    @discord.ui.button(style=discord.ButtonStyle.danger)
    async def confirm(self,interaction,button):
        try:
            result=state.end_protection(self.guild_id,self.owner_id,self.order_id)
        except potions.PotionError as error:
            await tell(interaction,str(error))
            return
        self.stop()
        await interaction.response.edit_message(content=state.text('protection_ended',amount=result['refund']),view=None)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def cancel(self,interaction,button):
        self.stop()
        await interaction.response.edit_message(content=state.text('cancelled'),view=None)


class ProtectionSettings(OwnedModal):
    def __init__(self,owner_id,guild_id):
        super().__init__(owner_id,guild_id,title=state.text('settings_title'))
        cfg=state.settings(guild_id)
        self.fee=discord.ui.TextInput(default=str(cfg['fee']),max_length=7)
        self.rate=discord.ui.TextInput(default=str(cfg['rate']),max_length=7)
        self.duration=discord.ui.TextInput(default=f"{cfg['minimum']},{cfg['maximum']}",max_length=12)
        self.cooldown=discord.ui.TextInput(default=str(cfg['cooldown']),max_length=5)
        self.modes=discord.ui.Select(options=[discord.SelectOption(label=state.text('settings_mode_'+m),value=m,default=m==(cfg['modes'] if cfg['enabled'] else 'disabled')) for m in ('both','fixed','budget','disabled')])
        for key,component in (('fee',self.fee),('rate',self.rate),('duration',self.duration),('cooldown',self.cooldown),('modes',self.modes)):
            self.add_item(discord.ui.Label(text=state.text('settings_'+key),component=component))

    async def interaction_check(self,interaction):
        if not await super().interaction_check(interaction):
            return False
        if not potions.can_manage(interaction.user,self.guild_id):
            await tell(interaction,state.text('shop_denied'))
            return False
        return True

    async def on_submit(self,interaction):
        # Recheck at save, including if permissions changed while the modal was open.
        if not potions.can_manage(interaction.user,self.guild_id):
            await tell(interaction,state.text('shop_denied'))
            return
        try:
            minimum,maximum=map(int,self.duration.value.split(','))
            mode=self.modes.values[0]
            state.configure(self.guild_id,self.owner_id,dict(fee=int(self.fee.value),rate=int(self.rate.value),minimum=minimum,maximum=maximum,cooldown=int(self.cooldown.value),modes=mode if mode!='disabled' else state.settings(self.guild_id)['modes'],enabled=mode!='disabled'))
        except (ValueError,potions.PotionError) as error:
            await tell(interaction,str(error) if isinstance(error,potions.PotionError) else state.text('bad_settings'))
            return
        await tell(interaction,state.text('settings_saved'))
