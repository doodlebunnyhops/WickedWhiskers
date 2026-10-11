import discord
import auto_cauldron as auto
from admin_settings import AdminView, authorized, text


class AutoSelect(discord.ui.Select):
    def __init__(self,key,values,current):
        self.key=key
        super().__init__(placeholder=auto.text(key),options=[discord.SelectOption(label=auto.text(v),value=v,default=v==current) for v in values])

    async def callback(self,interaction):
        # Stage choices until Save, allowing trigger and numeric settings to change together.
        self.view.pending[self.key]=self.values[0]
        for option in self.options:option.default=option.value==self.values[0]
        await interaction.response.edit_message(content=auto.text('staged'),view=self.view)


class AutoModal(discord.ui.Modal):
    def __init__(self,view):
        super().__init__(title=auto.text('edit_title'))
        self.owner_id,self.guild_id=view.owner_id,view.guild_id
        self.pending=dict(view.pending)
        self.fields={}
        values=auto.settings(self.guild_id)
        for key in ('interval_minutes','candy_threshold','minimum_gap_minutes'):
            field=discord.ui.TextInput(label=auto.text(key),default=str(values[key]) if values[key] is not None else '',required=key=='minimum_gap_minutes',max_length=10)
            self.fields[key]=field
            self.add_item(field)

    async def on_submit(self,interaction):
        if not authorized(interaction,self.owner_id,self.guild_id):
            await interaction.response.send_message(text('denied'),ephemeral=True)
            return
        try:
            values={k:int(v.value) for k,v in self.fields.items() if v.value.strip()}
            auto.configure(self.guild_id,guild=interaction.guild,**self.pending,**values)
        except ValueError as error:
            await interaction.response.send_message(str(error) if not str(error).startswith('invalid literal') else auto.text('invalid'),ephemeral=True)
            return
        await interaction.response.edit_message(content=auto.describe(self.guild_id,interaction.guild),view=AutoView(interaction))


class AutoView(AdminView):
    def __init__(self,interaction):
        super().__init__(interaction)
        self.pending={}
        values=auto.settings(self.guild_id)
        for key,choices in [('trigger',('interval','threshold','either')),('witch',('luna','raven','random')),('winners',('one','many','random'))]:
            self.add_item(AutoSelect(key,choices,values[key]))
        for item in self.children:
            if isinstance(item,discord.ui.Button):item.label=auto.text(item.custom_id)

    @discord.ui.button(custom_id='save',row=3)
    async def save(self,interaction,button):
        await interaction.response.send_modal(AutoModal(self))

    @discord.ui.button(custom_id='toggle',row=3)
    async def toggle(self,interaction,button):
        try:
            auto.configure(self.guild_id,guild=interaction.guild,enabled=not bool(auto.settings(self.guild_id)['enabled']))
        except ValueError as error:
            await interaction.response.send_message(str(error),ephemeral=True)
            return
        await interaction.response.edit_message(content=auto.describe(self.guild_id,interaction.guild),view=AutoView(interaction))
