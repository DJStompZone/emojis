import discord
from discord.ext import commands, tasks
import disnake
from disnake.ext import commands
# import random
# from slashtilities import log

# pylint: disable=E1101  # Man, get your types right


class MetaTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.change_status.start()

    def cog_unload(self):
        self.change_status.cancel()

    @tasks.loop(seconds=60.0)
    async def change_status(self):
        # print("Hit change_status in loop")
        # l_watching = ["Netflix", "Hulu", "YouTube", "HBO Go", "CrunchyRoll", "a DVD", "something... Else"]
        # l_oops = ["Pornhu", "xTub", "hent", "Tentacle P"]
        # shh = '! \U0001F92B'
        # badliar = '- Uhhh, I mean '
        # pick_wch = random.choice(l_watching)
        # pick_oop = random.choice(l_oops)
        # # print(pick_wch)
        # # print(pick_oop)
        # # print(shh)
        # # print(badliar)
        #actstring = pick_oop+badliar+pick_wch+shh
        # print(actstring)
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="DJ Screw Up Again",
            )
        )

    @change_status.before_loop
    async def before_change_status(self):
        await self.bot.wait_until_ready()