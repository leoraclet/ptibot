import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import NEWS_CHANNEL, ConfigManager

# TODO: News about uploaded videos
# TODO: Add a command to add/remove YouTube channels to follow


class Youtube(commands.Cog, name="youtube"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channels = ConfigManager.get("youtube_channels", [])

    async def add_channel(self, channel_id: str):
        if channel_id not in self.channels:
            self.channels.append(channel_id)
            ConfigManager.set("youtube_channels", self.channels)
            await self.bot.get_channel(NEWS_CHANNEL).send(
                f"Channel {channel_id} has been added to the follow list."
            )
        else:
            await self.bot.get_channel(NEWS_CHANNEL).send(
                f"Channel {channel_id} is already in the follow list."
            )

    async def remove_channel(self, channel_id: str):
        if channel_id in self.channels:
            self.channels.remove(channel_id)
            ConfigManager.set("youtube_channels", self.channels)
            await self.bot.get_channel(NEWS_CHANNEL).send(
                f"Channel {channel_id} has been removed from the follow list."
            )
        else:
            await self.bot.get_channel(NEWS_CHANNEL).send(
                f"Channel {channel_id} is not in the follow list."
            )

    @app_commands.command(name="add_youtube_channel")
    async def add_youtube_channel(self, interaction: discord.Interaction, channel_id: str):
        """Add a YouTube channel to the follow list."""
        await self.add_channel(channel_id)
        await interaction.response.send_message(f"Added channel {channel_id} to the follow list.")

    @app_commands.command(name="remove_youtube_channel")
    async def remove_youtube_channel(self, interaction: discord.Interaction, channel_id: str):
        """Remove a YouTube channel from the follow list."""
        await self.remove_channel(channel_id)
        await interaction.response.send_message(
            f"Removed channel {channel_id} from the follow list."
        )

    @tasks.loop(minutes=30)
    async def check_youtube_channels(self):
        """Check for new videos from followed YouTube channels."""
        # This is a placeholder for the actual implementation.
        # You would typically use the YouTube Data API to check for new videos.
        pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Youtube(bot))
