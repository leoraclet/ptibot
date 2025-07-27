import platform

import discord
from discord import Activity, ActivityType
from discord.ext import commands, tasks
from discord.ext.commands import Context
from loguru import logger


class Common(commands.Cog, name="common"):
    def __init__(self, bot) -> None:
        self.bot = bot
        # Start tasks
        self.update_status.start()

    @commands.hybrid_command(
        name="test",
        description="This is a testing command",
    )
    async def test_command(self, context: Context) -> None:
        await context.send(
            "This is a test command. It does nothing but "
            + "exists to show how to create a command."
        )
        pass

    @commands.hybrid_command(name="help", description="List all commands the bot has loaded.")
    async def help_command(self, context: Context) -> None:
        embed = discord.Embed(
            title="Help", description="List of available commands:", color=0xBEBEFE
        )
        for i in self.bot.cogs:
            if i == "owner" and not (await self.bot.is_owner(context.author)):
                continue
            cog = self.bot.get_cog(i)
            commands = cog.get_commands()
            data = []
            for command in commands:
                description = command.description.partition("\n")[0]
                data.append(f"{command.name} - {description}")
            help_text = "\n".join(data)
            embed.add_field(name=i.capitalize(), value=f"```{help_text}```", inline=False)
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="botinfo",
        description="Get some useful (or not) information about the bot.",
    )
    async def botinfo_command(self, context: Context) -> None:
        """
        Get some useful (or not) information about the bot.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            description="Create by Me",
            color=0xBEBEFE,
        )
        embed.set_author(name="Bot Information")
        embed.add_field(name="Owner:", value="Neutronys#1700", inline=True)
        embed.add_field(name="Python Version:", value=f"{platform.python_version()}", inline=True)
        embed.add_field(
            name="Prefix:",
            value="/ (Slash Commands) or > for normal commands",
            inline=False,
        )
        embed.set_footer(text=f"Requested by {context.author}")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="serverinfo",
        description="Get some useful (or not) information about the server.",
    )
    async def serverinfo_command(self, context: Context) -> None:
        """
        Get some useful (or not) information about the server.

        :param context: The hybrid command context.
        """
        roles = [role.name for role in context.guild.roles]
        num_roles = len(roles)
        if num_roles > 50:
            roles = roles[:50]
            roles.append(f">>>> Displaying [50/{num_roles}] Roles")
        roles = ", ".join(roles)

        embed = discord.Embed(
            title="**Server Name:**", description=f"{context.guild}", color=0xBEBEFE
        )
        if context.guild.icon is not None:
            embed.set_thumbnail(url=context.guild.icon.url)
        embed.add_field(name="Server ID", value=context.guild.id)
        embed.add_field(name="Member Count", value=context.guild.member_count)
        embed.add_field(name="Text/Voice Channels", value=f"{len(context.guild.channels)}")
        embed.add_field(name=f"Roles ({len(context.guild.roles)})", value=roles)
        embed.set_footer(text=f"Created at: {context.guild.created_at}")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="ping",
        description="Check if the bot is alive.",
    )
    async def ping_command(self, context: Context) -> None:
        """
        Check if the bot is alive.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"The bot latency is {round(self.bot.latency * 1000)}ms.",
            color=0xBEBEFE,
        )
        await context.send(embed=embed)

    @tasks.loop(minutes=2)
    async def update_status(self) -> None:
        """Update the bot's status."""
        guild = self.bot.get_guild(829032123301494834)
        logger.info(
            f"Updating status for guild: {guild.name if guild else 'DMs'} "
            f"with {len(guild.members) if guild else 'unknown'} members."
        )
        if guild:
            await self.bot.change_presence(
                activity=Activity(
                    type=ActivityType.watching,
                    name=f"{len([member for member in guild.members if not member.bot])} members",
                )
            )

    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()


async def setup(bot) -> None:
    await bot.add_cog(Common(bot))
