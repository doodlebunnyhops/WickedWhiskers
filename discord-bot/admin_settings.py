"""Settings operations shared by slash commands and their private interfaces."""
import discord
import db_utils as db
import slowmode
from utils.messages import default_messages
from utils.utils import has_role_or_permission


def text(key, **values):
    return default_messages().get_message('management', key, **values)


def authorized(interaction, owner_id=None, guild_id=None):
    return (interaction.guild is not None
            and (owner_id is None or interaction.user.id == owner_id)
            and (guild_id is None or interaction.guild_id == guild_id)
            and has_role_or_permission(interaction.user, interaction.guild_id))


def set_state(guild_id, enabled):
    if type(enabled) is not bool:
        raise ValueError(text('invalid'))
    db.set_game_disabled(guild_id, not enabled)


def set_pool(guild_id, amount):
    if type(amount) is not int or not 0 <= amount <= 9223372036854775807:
        raise ValueError(text('invalid'))
    db.set_cauldron_pool(guild_id, amount)


def set_channel(guild_id, kind, channel):
    if kind not in ('event', 'admin') or channel.guild.id != guild_id:
        raise ValueError(text('invalid'))
    getattr(db, 'set_' + kind + '_channel')(guild_id, channel.id)


def add_role(guild_id, role):
    if role.guild.id != guild_id or role.is_default() or role.managed:
        raise ValueError(text('invalid_role'))
    db.set_role_by_guild(guild_id, role.id)


def summary(guild_id):
    import auto_cauldron
    values=slowmode.settings(guild_id)
    return text('game_summary', enabled=text('enabled') if not db.get_game_settings(guild_id)[0] else text('disabled'),
                amount=db.get_cauldron_pool(guild_id), **values) + '\n\n' + auto_cauldron.describe(guild_id)


class AdminView(discord.ui.View):
    def __init__(self, interaction):
        super().__init__(timeout=300)
        self.owner_id=interaction.user.id
        self.guild_id=interaction.guild_id

    async def interaction_check(self, interaction):
        if authorized(interaction, self.owner_id, self.guild_id):
            return True
        await interaction.response.send_message(text('denied'), ephemeral=True)
        return False


class SettingsModal(discord.ui.Modal):
    def __init__(self, view, kind):
        super().__init__(title=text(kind + '_title'))
        self.owner_id, self.guild_id=view.owner_id,view.guild_id
        self.kind=kind
        if kind=='slowmode':
            values=slowmode.settings(self.guild_id)
        else:
            values={'amount':db.get_cauldron_pool(self.guild_id)}
        self.fields={}
        for key,value in values.items():
            field=discord.ui.TextInput(label=text(key),default=str(value),max_length=19)
            self.fields[key]=field
            self.add_item(field)

    async def on_submit(self, interaction):
        if not authorized(interaction,self.owner_id,self.guild_id):
            await interaction.response.send_message(text('denied'),ephemeral=True)
            return
        try:
            values={k:int(v.value) for k,v in self.fields.items()}
            if self.kind=='slowmode':
                slowmode.configure(self.guild_id,**values)
            else:
                set_pool(self.guild_id,values['amount'])
        except ValueError:
            await interaction.response.send_message(text('invalid'),ephemeral=True)
            return
        await interaction.response.edit_message(content=summary(self.guild_id))


class GameSettingsView(AdminView):
    def __init__(self, interaction):
        super().__init__(interaction)
        for item in self.children:
            item.label=text(item.custom_id)

    @discord.ui.button(custom_id='toggle_state',style=discord.ButtonStyle.secondary)
    async def toggle_state(self, interaction, button):
        set_state(self.guild_id,bool(db.get_game_settings(self.guild_id)[0]))
        await interaction.response.edit_message(content=summary(self.guild_id))

    @discord.ui.button(custom_id='slowmode_title',style=discord.ButtonStyle.secondary)
    async def slowmode_button(self,interaction,button):
        await interaction.response.send_modal(SettingsModal(self,'slowmode'))

    @discord.ui.button(custom_id='pool_title',style=discord.ButtonStyle.secondary)
    async def pool_button(self,interaction,button):
        await interaction.response.send_modal(SettingsModal(self,'pool'))

    @discord.ui.button(custom_id='auto_title',style=discord.ButtonStyle.secondary)
    async def auto_button(self,interaction,button):
        from modals.auto_cauldron import AutoView
        import auto_cauldron
        await interaction.response.send_message(auto_cauldron.describe(self.guild_id,interaction.guild),view=AutoView(interaction),ephemeral=True)


class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self,kind):
        self.kind=kind
        super().__init__(placeholder=text(kind+'_channel'),channel_types=[discord.ChannelType.text],min_values=1,max_values=1)

    async def callback(self,interaction):
        channel=interaction.guild.get_channel(self.values[0].id)
        if channel is None:
            await interaction.response.send_message(text('invalid'),ephemeral=True)
            return
        set_channel(interaction.guild_id,self.kind,channel)
        await interaction.response.send_message(text('channel_saved',kind=self.kind,channel=channel.mention),ephemeral=True)


class AccessRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder=text('add_role'),min_values=1,max_values=1)

    async def callback(self,interaction):
        try:
            add_role(interaction.guild_id,self.values[0])
        except ValueError as error:
            await interaction.response.send_message(str(error),ephemeral=True)
            return
        await interaction.response.send_message(text('role_saved'),ephemeral=True)


class BotSettingsView(AdminView):
    def __init__(self,interaction):
        super().__init__(interaction)
        self.add_item(ChannelSelect('event'))
        self.add_item(ChannelSelect('admin'))
        self.add_item(AccessRoleSelect())
        if interaction.user.guild_permissions.manage_guild:
            self.add_item(ShopManagerSelect())


def set_shop_manager(interaction,role):
    import potions
    if not interaction.user.guild_permissions.manage_guild:
        raise ValueError(text('shop_role_denied'))
    if role and (role.guild.id!=interaction.guild_id or role.is_default() or role.managed):
        raise ValueError(text('invalid_role'))
    potions.set_manager_role(interaction.guild_id,interaction.user.id,role.id if role else None)


class ShopManagerSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder=text('shop_role_select'),min_values=0,max_values=1)

    async def callback(self,interaction):
        role=self.values[0] if self.values else None
        try:set_shop_manager(interaction,role)
        except ValueError as error:
            await interaction.response.send_message(str(error),ephemeral=True)
            return
        await interaction.response.send_message(text('shop_role',role=role.name if role else text('none')),ephemeral=True)
