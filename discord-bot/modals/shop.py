"""Private modal shop. The buyer is always the interacting user, never a target."""
import logging
import discord
import db_utils as db
import potions
from utils.utils import post_to_target_channel

logger = logging.getLogger("bot")


async def tell(interaction, message):
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


class OwnedModal(discord.ui.Modal):
    def __init__(self, owner_id, guild_id, **kwargs):
        super().__init__(timeout=300, **kwargs)
        self.owner_id, self.guild_id = owner_id, guild_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id or interaction.guild_id != self.guild_id:
            await tell(interaction, "Open your own shop to use these controls.")
            return False
        return True

    async def on_error(self, interaction, error):
        logger.exception("Potion modal failed", exc_info=error)
        await tell(interaction, "The shop couldn't complete that request. Check your inventory before trying again.")


class OwnedView(discord.ui.View):
    def __init__(self, owner_id, guild_id):
        super().__init__(timeout=300)
        self.owner_id, self.guild_id = owner_id, guild_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id or interaction.guild_id != self.guild_id:
            await tell(interaction, "Open your own shop to use these controls.")
            return False
        return True

    async def on_error(self, interaction, error, item):
        logger.exception("Potion control failed", exc_info=error)
        await tell(interaction, "That control couldn't complete. Check your inventory before trying again.")


class ShopModal(OwnedModal):
    def __init__(self, owner_id, guild_id):
        balance = potions.eligible(guild_id, owner_id)
        super().__init__(owner_id, guild_id, title="Luna & Raven's Potion Shop")
        options = []
        for key, potion in potions.CATALOG.items():
            price, enabled = potions.offer(guild_id, key)
            if enabled:
                options.append(discord.SelectOption(label=f"{potion.name} — {price} candy", value=key, description=potion.description[:100]))
        import player_state as state
        if state.settings(guild_id)['enabled']:
            options.append(discord.SelectOption(label=state.text('protection_name'),value='veil',description=state.text('protection_option')))
        if not options:
            raise potions.PotionError("The shop has no potions for sale right now.")
        self.potion = discord.ui.Select(options=options)
        self.quantity = discord.ui.TextInput(default="1", min_length=1, max_length=3)
        self.add_item(discord.ui.Label(text="Choose a potion", description=f"Your balance: {balance} candy. Full effect and total shown before payment.", component=self.potion))
        self.add_item(discord.ui.Label(text="Quantity (1–100)", component=self.quantity))

    async def on_submit(self, interaction):
        try:
            quantity = int(self.quantity.value)
            if not 1 <= quantity <= potions.MAX_QUANTITY:
                raise ValueError
        except ValueError:
            await tell(interaction, "Choose a whole quantity from 1 to 100.")
            return
        try:
            key = self.potion.values[0]
            if key == 'veil':
                import player_state as state
                from modals.protection import open_protection
                if quantity != 1:
                    await tell(interaction,state.text('one_protection'))
                    return
                await open_protection(interaction)
                return
            price, enabled = potions.offer(self.guild_id, key)
            if not enabled:
                raise potions.PotionError("That potion is no longer for sale.")
            view = Checkout(self.owner_id, self.guild_id, key, quantity, price, str(interaction.id))
            await interaction.response.send_message(view.summary(), view=view, ephemeral=True)
        except potions.PotionError as error:
            await tell(interaction, str(error))


class Checkout(OwnedView):
    def __init__(self, owner_id, guild_id, key, quantity, price, order_id):
        super().__init__(owner_id, guild_id)
        self.key, self.quantity, self.price, self.order_id = key, quantity, price, order_id
        self.finished = False

    def summary(self):
        potion = potions.item(self.key)
        balance = potions.eligible(self.guild_id, self.owner_id)
        return (f"**{potion.name} × {self.quantity}**\n{potion.description}\n"
                f"Total: **{self.price * self.quantity} candy**\n"
                f"Balance: {balance} → {balance-self.price*self.quantity} candy\n"
                "Purchase adds bottles to inventory; activate them separately.")

    @discord.ui.button(label="Confirm Purchase", style=discord.ButtonStyle.success)
    async def confirm(self, interaction, button):
        if self.finished:
            await tell(interaction, "This order is already closed.")
            return
        try:
            result = potions.purchase(self.guild_id, interaction.user.id, self.key, self.quantity, self.price, self.order_id)
        except potions.PriceChanged as error:
            self.price = error.price
            await interaction.response.edit_message(content=f"{error}\n\n{self.summary()}", view=self)
            return
        except potions.PotionError as error:
            await tell(interaction, str(error))
            return
        self.finished = True
        self.stop()
        await interaction.response.edit_message(content=f"Purchased {result['quantity']} × {result['name']} for {result['cost']} candy.\nRemaining balance: {result['balance']} candy.", view=InventoryLink(self.owner_id, self.guild_id))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        self.finished = True
        self.stop()
        await interaction.response.edit_message(content="Purchase cancelled. No candy charged.", view=None)


class InventoryLink(OwnedView):
    @discord.ui.button(label="Open Inventory", style=discord.ButtonStyle.primary)
    async def open_inventory(self, interaction, button):
        await show_inventory(interaction)


class InventoryView(OwnedView):
    def __init__(self,owner_id,guild_id):
        super().__init__(owner_id,guild_id)
        import player_state as state
        self.protection.label=state.text('protection_name')

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def protection(self,interaction,button):
        from modals.protection import open_protection
        await open_protection(interaction)

    @discord.ui.button(label="Use Potion", style=discord.ButtonStyle.primary)
    async def activate(self, interaction, button):
        try:
            await interaction.response.send_modal(UsePotionModal(self.owner_id, self.guild_id))
        except potions.PotionError as error:
            await tell(interaction, str(error))


async def show_inventory(interaction):
    if not interaction.guild_id:
        await tell(interaction, "Open your inventory in a server.")
        return
    bottles, effects = potions.inventory(interaction.guild_id, interaction.user.id)
    lines = [f"{p.name}: {bottles.get(key, 0)} bottle(s)" for key, p in potions.CATALOG.items()]
    active = [f"{potions.item(key).name}: {charges} charge(s)" for key, charges in effects.items()]
    content = "**Your potions**\n" + "\n".join(lines) + "\n\n**Active effects**\n" + ("\n".join(active) or "None")
    import player_state as state
    from modals.protection import status_text
    content += '\n\n' + status_text(interaction.guild_id,interaction.user.id)
    returned = db.get_db_connection().execute('SELECT potion_id,charges FROM returned_potions WHERE guild_id=? AND player_id=? ORDER BY id',(interaction.guild_id,interaction.user.id)).fetchall()
    if returned:
        content += '\n' + state.text('returned_heading') + '\n' + '\n'.join(state.text('returned_bottle',name=potions.item(key).name,charges=charges) for key,charges in returned)
    view = InventoryView(interaction.user.id, interaction.guild_id)
    await interaction.response.send_message(content, view=view, ephemeral=True)


class UsePotionModal(OwnedModal):
    def __init__(self, owner_id, guild_id):
        potions.eligible(guild_id, owner_id)
        import player_state as state
        state.require(guild_id, owner_id, "use")
        super().__init__(owner_id, guild_id, title="Use a Potion")
        bottles, effects = potions.inventory(guild_id, owner_id)
        options = [discord.SelectOption(label=f"{potions.item(key).name} ({count})", value=key, description=potions.item(key).description[:100]) for key, count in bottles.items() if count > 0 and not effects.get(key)]
        if not options:
            raise potions.PotionError("You have no available potions to activate. Active effects cannot be stacked.")
        self.potion = discord.ui.Select(options=options)
        self.add_item(discord.ui.Label(text="Activate one bottle", description="Bottled effects keep their charges until triggered. Luna’s Calling acts immediately.", component=self.potion))

    async def on_submit(self, interaction):
        # Member lookup may await, but no database transaction is held while doing so.
        await interaction.response.defer(ephemeral=True)
        key = self.potion.values[0]
        members = None
        if key == "luna":
            try:
                if not interaction.guild.chunked:
                    await interaction.guild.chunk(cache=True)
                if not interaction.guild.chunked:
                    raise potions.PotionError("Couldn't verify server members. Your potion was not consumed.")
                members = {m.id for m in interaction.guild.members if not m.bot}
            except (discord.DiscordException, potions.PotionError):
                await tell(interaction, "Couldn't verify server members. Your potion was not consumed.")
                return
        try:
            result = potions.use(self.guild_id, interaction.user.id, key, interaction.id, members)
        except potions.PotionError as error:
            await tell(interaction, str(error))
            return
        if result['recipients']:
            names = ", ".join(f"<@{uid}>" for uid in result['recipients'])
            await tell(interaction, f"Luna gave 5 candy each to {names}. Your potion was consumed.")
            if not result.get('replayed'):
                try:
                    await post_to_target_channel(interaction, f"🌙 <@{self.owner_id}> summoned Luna! She gifted 5 candy each to {names}.")
                except discord.DiscordException:
                    logger.exception("Luna reward saved but public announcement failed")
                    await tell(interaction, "Rewards were saved, but I couldn't post the event announcement.")
        else:
            await tell(interaction, interaction.client.message_loader.get_message("potion_events", "activated", potion=result["name"], charges=result["charges"]))


class ManageModal(OwnedModal):
    def __init__(self, owner_id, guild_id, key):
        super().__init__(owner_id, guild_id, title="Edit Potion Shop")
        self.key = key
        price, enabled = potions.offer(guild_id, key)
        potion = potions.item(key)
        self.price = discord.ui.TextInput(default=str(price), max_length=7)
        self.enabled = discord.ui.Checkbox(default=enabled)
        self.add_item(discord.ui.Label(text=f"{potion.name}: price", description=f"Default {potion.price} candy. {potion.description}"[:100], component=self.price))
        self.add_item(discord.ui.Label(text="Available for purchase", description="Owned bottles remain usable when sales are disabled.", component=self.enabled))

    async def interaction_check(self, interaction):
        if not await super().interaction_check(interaction):
            return False
        if not potions.can_manage(interaction.user, self.guild_id):
            await tell(interaction, "You no longer have shop management permission.")
            return False
        return True

    async def on_submit(self, interaction):
        try:
            price = int(self.price.value)
            potions.configure(self.guild_id, interaction.user.id, self.key, price, self.enabled.value)
        except ValueError as error:
            await tell(interaction, str(error) if isinstance(error, potions.PotionError) else "Enter a positive whole-number price.")
            return
        await tell(interaction, f"Updated {potions.item(self.key).name}: {price} candy; {'on sale' if self.enabled.value else 'sales disabled'}.")


class ManageView(OwnedView):
    def __init__(self, owner_id, guild_id):
        super().__init__(owner_id, guild_id)
        self.selected = None
        import player_state as state
        self.protection_settings.label=state.text('settings_button')
        self.selector.options = [discord.SelectOption(label=p.name, value=key, description=p.description[:100]) for key, p in potions.CATALOG.items()]

    async def interaction_check(self, interaction):
        if not await super().interaction_check(interaction):
            return False
        if not potions.can_manage(interaction.user, self.guild_id):
            await tell(interaction, "Shop management permission is required.")
            return False
        return True

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def protection_settings(self,interaction,button):
        from modals.protection import ProtectionSettings
        await interaction.response.send_modal(ProtectionSettings(self.owner_id,self.guild_id))

    @discord.ui.select(placeholder="Select a potion to edit")
    async def selector(self, interaction, select):
        self.selected = select.values[0]
        await interaction.response.send_modal(ManageModal(self.owner_id, self.guild_id, self.selected))

    @discord.ui.button(label="Reset Selected Price")
    async def reset_one(self, interaction, button):
        if not self.selected:
            await tell(interaction, "Select a potion first.")
            return
        potions.reset_prices(self.guild_id, interaction.user.id, self.selected)
        await tell(interaction, "Default price restored. Sale availability is unchanged.")

    @discord.ui.button(label="Reset All Prices")
    async def reset_all(self, interaction, button):
        potions.reset_prices(self.guild_id, interaction.user.id)
        await tell(interaction, "Default prices restored for this server. Sale availability is unchanged.")


class ShopEntrance(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Shop", style=discord.ButtonStyle.primary, custom_id="wickedwhiskers:shop:open:v1")
    async def open_shop(self, interaction, button):
        await open_shop(interaction)

    @discord.ui.button(label="Inventory", style=discord.ButtonStyle.secondary, custom_id="wickedwhiskers:shop:inventory:v1")
    async def open_inventory(self, interaction, button):
        await show_inventory(interaction)


async def open_shop(interaction):
    if not interaction.guild_id:
        await tell(interaction, "Open the shop in a server.")
        return
    try:
        await interaction.response.send_modal(ShopModal(interaction.user.id, interaction.guild_id))
    except potions.PotionError as error:
        await tell(interaction, str(error))
