import re

import discord
from discord.ext.commands import has_permissions

from src.common import *
from src.exceptions import *


def setup(bot):
    bot.add_cog(Management(bot))


class Management(commands.Cog):
    __slots__ = ["bot"]

    def __init__(self, bot):
        self.bot = bot

    async def get_confirmation(self, ctx,
                               timeout=30.0,
                               thumbnail_url=None,
                               required_msgs=("yes", "y"),
                               title="Are you sure?",
                               message="Type `yes` to confirm, or anything else to cancel."):
        """
        Get confirmation on a moderation action. This needs a rewrite.

        :param ctx: context
        :param timeout: how long the bot should wait for a response
        :param thumbnail_url: thumbnail to add to the embed
        :param required_msgs: a list of accepted confirmation responses
        :param title: the title for the embed
        :param message: the description for the embed
        :return: the message sent by the function, and True if successful (False if failed)
        """

        def check(message_):
            """
            Check whether the message sent was by the original author.

            :param message_: the message
            :return: True if author is the same; otherwise, False
            """
            return message_.author == ctx.message.author

        # confirmation embed
        confirm_embed = discord.Embed(
            colour=Colours.warn,
            title=title,
            description=message,
        )

        if thumbnail_url:
            confirm_embed.set_thumbnail(url=thumbnail_url)

        confirm_embed.set_footer(text=f"This will time out after {int(timeout)} seconds.")
        confirm_embed.set_author(name=ctx.message.author.display_name, icon_url=ctx.message.author.avatar_url)

        # send confirm embed
        embed_message_to_edit = await ctx.send(embed=confirm_embed)

        # wait for response
        try:
            reply = await self.bot.wait_for("message", timeout=(timeout := 30.0), check=check)

            # user replied with an approved response
            if reply.content.lower().rstrip() in required_msgs:
                return embed_message_to_edit, True
            else:
                return embed_message_to_edit, False

        # timeout exceeded
        except TimeoutError:
            return embed_message_to_edit, False  # cancelled

    @commands.command(name="rename",
                      description="Rename an emoji.",
                      usage="[BOT_PREFIX]rename [emoji] [new name]",
                      aliases=[],
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    async def rename(self, ctx, emoji_to_rename: discord.Emoji, *, args):
        """
        Rename an emoji.

        :param ctx: context
        :param emoji_to_rename: the emoji to be renamed. Must be part of the guild specified in ctx
        :param args: the name for the new emoji
        :return: N/A
        """

        # no emoji
        if emoji_to_rename.guild != ctx.message.guild:
            raise CustomCommandError("Couldn't find that emoji in this server.")

        old_name = emoji_to_rename.name

        # remove symbols and spaces
        new_name = "".join([re.sub(r"[^\w]", "", word.replace("\"", "")) for word in args])

        if new_name == "":
            raise CustomCommandError("You need to include at least one alphanumeric character in the emoji's name.")

        # rename
        await emoji_to_rename.edit(name=new_name)

        # send success
        embed = discord.Embed(
            title="Emoji renamed",
            colour=Colours.success,
            description=f"`:{old_name}:` -> `:{new_name}:`",
        )

        embed.set_thumbnail(url=emoji_to_rename.url)

        # send
        await ctx.message.channel.send(embed=embed)

    @commands.command(name="delete",
                      description="Delete some emojis.",
                      usage="[BOT_PREFIX]delete [emoji] <emoji> <emoji> ...",
                      aliases=["remove", "del", "deleteemoji", "delemoji"],
                      pass_context=True)
    @has_permissions(manage_emojis=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def delete_emoji(self, ctx, emojis_to_delete: commands.Greedy[discord.Emoji]):
        """
        Delete an emoji, or a list of emojis. Requires text confirmation.

        :param ctx: context
        :param emojis_to_delete: a list of emojis to be deleted
        :return: N/A
        """

        # no emojis provided
        if len(emojis_to_delete) == 0:
            raise CustomCommandError("You need to add at least one emoji to delete.")

        # make sure the user wants to delete the emojis
        msg_to_edit, result = await self.get_confirmation(ctx)

        # user doesn't want to delete
        if not result:
            raise CustomCommandError("Deletion cancelled.")

        # delete the emojis
        for emoji in emojis_to_delete:

            # emoji is from another guild
            if emoji.guild != ctx.message.guild:
                raise CustomCommandError(f"I can't find the emoji {emoji} in this server.")

            # delete
            await emoji.delete(reason=f"Deleted by {ctx.message.author.display_name}")

        # only one emoji deleted
        if len(emojis_to_delete) == 1:
            embed = discord.Embed(
                title="Emoji deleted",
                colour=Colours.success,
                description=f"`:{emojis_to_delete[0].name}:`"
            )

            embed.set_thumbnail(url=emojis_to_delete[0].url)

        # multiple emojis deleted; different embed required
        else:
            embed = discord.Embed(
                title=f"{len(emojis_to_delete)} emojis deleted",
                colour=Colours.success,
                description=f"`:{':`, `:'.join([emoji.name for emoji in emojis_to_delete])}:`"
            )

        # send success message
        await msg_to_edit.edit(embed=embed)

    @commands.command(name="usage",
                      description="View command usage for Emojis.",
                      usage="[BOT_PREFIX]usage",
                      aliases=["us", "ug"],
                      pass_context=True)
    async def command_usage(self, ctx):
        usage = [i for i in COMMAND_USAGE.find()]
        sorted_usage = sorted(usage, key=lambda x: x["usage"], reverse=True)

        usage_template = "`{0}{1}` - {2} uses"

        await ctx.send(
            embed=discord.Embed(
                title="Top commands",
                description="\n".join([usage_template.format(ctx.prefix, i["command"], i["usage"]) for i in sorted_usage[0:10]]),
                colour=Colours.base
            )
        )

    @commands.command(name="users",
                      description="Get the amount of people who have ever run a vote-locked command.",
                      usage="[BOT_PREFIX]users",
                      aliases=[],
                      hidden=True,
                      pass_context=True)
    @commands.is_owner()
    async def users(self, ctx):
        users_amount = VOTES.count()

        await ctx.send(
            embed=discord.Embed(
                colour=Colours.base,
                description=f"{users_amount}",
            ).set_footer(text="Calculated by the number of users who have used vote-locked commands.")
        )

    @commands.command(name="evaluate",
                      description="Evaluate Python code and run it.",
                      usage="[BOT_PREFIX]evaluate [code]",
                      aliases=["eval", "ev"],
                      hidden=True,
                      pass_context=True)
    @commands.is_owner()
    async def evaluate(self, ctx, *, args):
        try:
            eval_result = eval(args)
        except Exception as e:
            eval_result = str(e)

        eval_embed = discord.Embed(colour=Colours.base)
        eval_embed.add_field(name="Result", value=f"```py\n{eval_result}\n```")

        await ctx.send(embed=eval_embed)
