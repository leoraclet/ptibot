from discord import app_commands
from discord.ext import commands


class Github(commands.Cog, name="github"):
    """GitHub related commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="github")
    async def github_command(self, ctx: commands.Context):
        """Post the GitHub repository link."""
        await ctx.response.send_message("Check out the GitHub repository:")


async def setup(bot: commands.Bot):
    await bot.add_cog(Github(bot))
