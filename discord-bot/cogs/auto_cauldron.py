"""One scheduler loop; each guild rechecks eligibility atomically before payout."""
import logging
import uuid
from discord.ext import commands,tasks
import auto_cauldron as schedules
import db_utils as db
from utils.cauldron import CauldronError
from cogs.game_commands.cast import post_award

logger=logging.getLogger('bot')

class AutoCauldron(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    async def cog_load(self):
        self.poll.start()

    def cog_unload(self):
        self.poll.cancel()

    @tasks.loop(seconds=30)
    async def poll(self):
        for (guild_id,) in db.get_db_connection().execute('SELECT guild_id FROM auto_cauldron WHERE enabled=1').fetchall():
            guild=self.bot.get_guild(guild_id)
            if guild is None:continue
            try:
                channel,error=schedules.event_channel(guild)
                if error:continue
                result=schedules.claim(guild_id,'auto:'+uuid.uuid4().hex,self.bot.user.id)
                if result is not None:
                    await post_award(guild,channel,self.bot.message_loader,result,self.bot.user.id)
            except CauldronError:
                # No eligible players / empty pool: retain the schedule for next poll.
                continue
            except Exception:
                # An announcement failure never replays an already committed award.
                logger.exception('Automatic cauldron failed for guild %s',guild_id)

    @poll.before_loop
    async def before_poll(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AutoCauldron(bot))
