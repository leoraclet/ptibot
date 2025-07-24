import re
from datetime import datetime

import feedparser
from discord import Colour, Embed
from discord.ext import commands, tasks

from config import NEWS_CHANNEL, ConfigManager


class News(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = NEWS_CHANNEL.id
        self.sent_entries = ConfigManager.get("feeds", [])
        self.feeds = [
            ("https://www.cert.ssi.gouv.fr/feed/", "CERT-FR"),
            ("https://www.zataz.com/feed/", "ZATAZ"),
            ("https://www.clusif.fr/feed", "CLUSIF"),
        ]

        # Start the news update task
        self.news_update.start()

    def clean_html(self, raw_html):
        """Remove HTML tags from a string."""
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", raw_html)
        return cleantext.strip()

    def format_date(self, date_str):
        """Format the publication date nicely."""
        try:
            date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
            return date.strftime("%d/%m/%Y à %H:%M")
        except Exception:
            return date_str

    def get_source(self, feed_url):
        """Get source name from feed URL."""
        for url, name in self.feeds:
            if feed_url.startswith(url):
                return name

    def get_category_color(self, source):
        """Return color based on source."""
        colors = {"CERT-FR": Colour.red(), "ZATAZ": Colour.blue(), "CLUSIF": Colour.green()}
        return colors.get(source, Colour.default())

    def create_embed(self, entry, feed_url):
        """Create a rich embed for the news entry."""
        source = self.get_source(feed_url)

        # Clean and truncate description
        description = self.clean_html(entry.get("description", ""))
        if len(description) > 1000:
            description = description[:997] + "..."

        # Create embed
        embed = Embed(
            title=entry.get("title", "Sans titre"),
            url=entry.get("link", ""),
            description=description,
            color=self.get_category_color(source),
        )

        # Add metadata fields
        embed.add_field(name="Source", value=f":shield: {source}", inline=True)

        if "pubDate" in entry:
            embed.add_field(
                name="Date de publication",
                value=f":calendar: {self.format_date(entry.pubDate)}",
                inline=True,
            )

        if "author" in entry:
            embed.add_field(
                name="Auteur", value=f":pencil: {entry.get('author', 'Non spécifié')}", inline=True
            )

        if "category" in entry:
            categories = entry.get("category", [])
            if not isinstance(categories, list):
                categories = [categories]
            if categories:
                embed.add_field(
                    name="Catégories", value=f":label: {', '.join(categories)}", inline=False
                )

        # Add footer with entry ID for tracking
        embed.set_footer(text=f"ID: {entry.get('id', 'Unknown')}")

        return embed

    @commands.hybrid_command(
        name="news",
        description="Get the latest news from various sources.",
    )
    async def news_command(self, context: commands.Context):
        await self.news_update()

    @tasks.loop(minutes=30)
    async def news_update(self):
        new_entries = []
        for feed_url, _ in self.feeds:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue

            for entry in feed.entries:
                if entry.id not in self.sent_entries:
                    new_entries.append((entry, feed_url))
                    self.sent_entries.append(entry.id)

        if new_entries:
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                for entry, feed_url in new_entries:
                    embed = self.create_embed(entry, feed_url)
                    await channel.send(embed=embed)

            # Update the configuration file
            ConfigManager.set("feeds", list(self.sent_entries))

    @news_update.before_loop
    async def before_news_update(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(News(bot))
