import os
import asyncio
import logging
from os import listdir
from os.path import splitext
from re import search
import keep_alive
import matplotlib.pyplot as plt
from dateutil.utils import today
from discord import (
    Activity,
    ActivityType,
    Message,
    Intents,
    AllowedMentions,
    HTTPException,
)
from discord.ext.commands import (
    CommandNotFound,
    MissingRequiredArgument,
    CommandInvokeError,
    AutoShardedBot,
    EmojiConverter,
    BucketType,
    CooldownMapping,
)



from src.common.common import *
# from replit import db as db
log = logging.Logger(__name__)

# from keep_alive import app as keep_alive_app
# keep_alive_app.loaded_in = True
GLOBAL_COOLDOWN = (1.0, 5.0)  # (1.0, 5.0) = 1 command per 5 seconds
WELCOME_MSG = "Thanks for inviting Emojis. My prefix is `~`.\n\n"


class CustomContext(Context):
    """ A custom Context class with additional methods. """
    async def error(self, err: Union[str, Exception]) -> None:
        """ Send an error Embed to a specified channel. """

        await self.send(embed=Embed(colour=Colours.error,
                                    description=f"{CustomEmojis.error} {err}"))

    async def success(self, string):
        """ Send a success Embed to a specified channel. """

        await self.send(embed=Embed(
            colour=Colours.success,
            description="%s %s" % (CustomEmojis.success, string),
        ))

    async def upload_emoji(self,
                           name: str,
                           url: str,
                           post_success: bool = True) -> Emoji:
        """
        Upload a custom emoji to a guild.

        :param name: The name for the emoji.
        :param url: The source of the image. Must be < 256kb.
        :param post_success: [Optional] Whether or not to post a success message in the chat.
        :returns: The new emoji.
        """
        response = get(url)

        if response.ok:
            # Store the image in BytesIO to avoid saving to disk
            emoji_bytes = BytesIO(response.content)

            # Upload the emoji to the Guild
            new_emoji = await self.guild.create_custom_emoji(
                name=name, image=emoji_bytes.read())
        else:
            raise Exception("Couldn't fetch image (%s)." %
                            response.status_code)

        # Post a success Embed in the chat
        if post_success:
            await self.send(embed=Embed(
                colour=Colours.success,
                description="%s `:%s:`" % (CustomEmojis.success, name),
            ).set_thumbnail(url=new_emoji.url))

        return new_emoji


class Emojis(AutoShardedBot):
    """ A custom AutoShardedBot class with overridden methods."""
    def __init__(self):
        self.cooldown = CooldownMapping.from_cooldown(*GLOBAL_COOLDOWN,
                                                      BucketType.user)
        self.command_usage = {}
        self.prefixes = {}
        self.blacklist = set()

        # Make sure the bot can't be abused to mass ping
        allowed_mentions = AllowedMentions(roles=False,
                                           everyone=False,
                                           users=True)

        # Minimum required
        intents = Intents(guilds=True,
                          emojis=True,
                          messages=True,
                          reactions=True)

        super().__init__(
            command_prefix=self.get_prefix,
            description="An emoji management bot.",
            activity=Activity(
                name=f"~help",
                type=ActivityType.watching,
            ),
            pm_help=None,
            chunk_guilds_at_startup=False,
            heartbeat_timeout=150.0,
            allowed_mentions=allowed_mentions,
            intents=intents,
            owner_ids=[
                269249777185718274,  # DJ
            ],
        )

        # Update continuously
        self.presence_updater = self.loop.create_task(
            self._bg_update_presence())
        # self.usage_updater = self.loop.create_task(self._bg_update_usage())

        # Update once
        # self.loop.create_task(self.update_prefix_list())
        # self.loop.create_task(self.update_blacklist())

    async def get_prefix(self, message):
        return self.prefixes.get(message.guild.id, "~")

    async def get_context(self, message, *, cls=CustomContext):
        """ Use CustomContext instead of Context. """
        return await super().get_context(message, cls=cls)

    async def on_message(self, message) -> None:
        # Process message
        await self.process_commands(message)

        # Replace unparsed :emojis:, NQN-style
        await self.replace_unparsed_emojis(message)

    async def on_command_error(self, ctx, err) -> None:
        """
        Catch and handle errors thrown by the bot.

        :param ctx:
        :param err: The error thrown.
        """
        if isinstance(err, CheckFailure):
            return
        elif isinstance(err, CommandNotFound):
            return  # Ignore
        elif isinstance(err, MissingRequiredArgument):
            # Make missing argument errors clearer
            err = Exception(
                "You're missing an argument (`%s`). Type `>help %s` for more info."
                % (err.param.name, ctx.command))
        elif isinstance(err, CommandInvokeError):
            # Try to simplify HTTP errors
            try:
                err = Exception(getattr(err, "original").text or str(err))
            except AttributeError:
                pass

        # Attempt to simplify error message
        msg = str(getattr(err, "__cause__") or err)

        # Send the error to the user
        await ctx.error(msg)

    async def invoke(self, ctx):
        if ctx.message.author.id in self.blacklist:
            await ctx.error("Sorry, buddy. You're blacklisted. ")
        else:
            await super().invoke(ctx)

    async def on_command_completion(self, ctx):
        cmd = ctx.command.name.lower()

        self.command_usage[cmd] = self.command_usage.get(cmd, 0) + 1

    async def on_guild_join(self, guild) -> None:  # noqa
        """ Send a welcome message, and create the Emojis webhook in each channel. """

        # Find the first channel the bot can type in and send the welcome message
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(embed=Embed(description=WELCOME_MSG))
                break

        for channel in guild.text_channels:
            await channel.create_webook(name="Emojis")

    async def on_ready(self) -> None:  # noqa
        print("Bot ready!")

    # async def update_blacklist(self):
    #     query = db.blacklist.find({}, {"_id": False})

        # async for result in query:
        #     self.blacklist.add(result["id"])

    # async def update_prefix_list(self):
    # #     query = db.prefixes.find({}, {"_id": False})

    #     async for result in query:
    #         self.prefixes[result["id"]] = result["prefix"]

    async def _bg_update_presence(self, delay: int = 300) -> None:
        """ Update the bot's status continuously. """

        await self.wait_until_ready()

        while True:
            if not self.is_closed():
                try:
                    await self.change_presence(activity=Activity(
                        name=f">help",
                        type=ActivityType.watching,
                    ))
                except HTTPException:
                    pass

            await asyncio.sleep(delay)

    # async def _bg_update_usage(self, delay: int = 900):
    #     """ Update the bot's usage stats in MongoDB. """

    #     await self.wait_until_ready()

    #     while not self.is_closed():
    #         # Update all-time usage data
    #         for cmd, usage in self.command_usage.items():
    #             # Update global command usage
    #             await db.usage.update_one({}, {"$inc": {
    #                 cmd.lower(): usage
    #             }},
    #                                       upsert=True)

    #             # Update today's command usage
    #             await db.historical_usage.update_one(
    #                 {"date": str(today().strftime("%Y-%m-%d"))},
    #                 {"$inc": {
    #                     "commands": usage
    #                 }},
    #                 upsert=True,
    #             )

    #         # Reset command usage cache
    #         self.command_usage = {}

    #         await make_graph()
    #         await asyncio.sleep(delay)

    async def replace_unparsed_emojis(self, message: Message):
        """
        Replace unparsed ':emojis:' in a message, to simulate Discord Nitro.
        Sends the modified message on a Webhook that looks like the user.
        """
        has_updated = False

        if not message.author.bot:
            # Check for :emojis:
            match = bool(search(r":[a-zA-Z0-9_-]+:", message.content))

            if match:
                ctx = await self.get_context(message)
                message_split = message.content.split()

                # Loop through every word and try to make it an emoji
                for i in range(len(message_split)):
                    word = message_split[i]

                    # Matches unparsed emojis
                    if search(r":[a-zA-Z0-9_-]+:", word):
                        try:
                            # Convert to Emoji
                            found_emoji = await EmojiConverter().convert(
                                ctx, word.replace(":", ""))

                            message_split[i] = str(found_emoji)
                            has_updated = True
                        except BadArgument:
                            pass

                if has_updated:
                    # Find the bot's Webhook and send the message on it
                    webhook = await get_emojis_webhook(ctx)

                    await webhook.send(
                        " ".join(message_split),
                        username=message.author.display_name,
                        avatar_url=message.author.avatar_url,
                    )

                    await message.delete()


# async def make_graph():
#     """ Make a graph of command usage. """
#     query = db.historical_usage.find({}, {"_id": False})

#     dates = []
#     commands = []

#     async for i in query:
#         date = i["date"]
#         cmds = i["commands"]

#         dates.append(date)
#         commands.append(cmds)

#     plt.clf()
#     plt.plot(dates, commands)
#     plt.title = "Command usage by day"
#     plt.savefig("./data/stats/usage.png")


if __name__ == "__main__":
    bot = Emojis()
    
    
    # Remove the default help command so a better one can be added
    bot.remove_command("help")

    # Load cogs
    # Ignores files starting with "_", like __init__.py
    for cog in listdir("./src/exts/"):
        if not cog.startswith("_"):
            file_name, file_extension = splitext(cog)
            bot.load_extension("src.exts.%s" % file_name)

    # Reload the Misc extension to update the help command
    bot.reload_extension("src.exts.misc")
    bottoken = os.environ['bottoken']
    keep_alive.keep_alive()
    bot.run(bottoken)
