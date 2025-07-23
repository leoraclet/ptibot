import json
import logging
import os
import platform
import random
import re
import sys

import discord
import requests
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv
from loguru import logger
from peewee import Model, SqliteDatabase

# Load environment variables from .env file
load_dotenv()


# ==========================================================
# Set up logging
# ==========================================================


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:  # type: ignore
            frame = frame.f_back  # type: ignore
            depth += 1

        regex = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, regex.sub("", record.getMessage()), colorize=False
        )


# Intercept standard logging
logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)

# Configure Loguru logger
logger.remove()  # Remove the default logger
logger.add(sys.stdout, level="INFO", backtrace=True, diagnose=True)
logger.add(
    "logs/discord_bot.log",
    level="INFO",
    rotation="30 MB",
    backtrace=True,
    diagnose=True,
    colorize=False,
    retention="7 days",
    enqueue=True,
)

# ==========================================================
# Set up the SQLite database
# ==========================================================

db = SqliteDatabase("db/sqlite3.db")


# Base model for Peewee ORM
# This will be the base class for all models in the application
class BaseModel(Model):
    class Meta:
        database = db


# ==========================================================
# ==== Command to get a random quote from ZenQuotes API ====
# ==========================================================


@logger.catch
def get_quote():
    response = requests.get("https://zenquotes.io/api/random", timeout=5)
    json_data = json.loads(response.text)
    quote = json_data[0]["q"] + " -" + json_data[0]["a"]
    return quote


# ========================================================
# Discord bot class and event handlers
# ========================================================

intents = discord.Intents.default()
intents.message_content = True


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv("PREFIX")),
            intents=intents,
            help_command=None,
        )

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user or message.author.bot:
            return

        if message.content.startswith("$quote"):
            quote = get_quote()
            await message.channel.send(quote)
        else:
            await self.process_commands(message)

    @tasks.loop(seconds=10)  # task runs every +-10 seconds
    async def random_task(self):
        self.random_task.change_interval(seconds=10 + random.randint(-10, 10))
        # print(str(self.random_task.seconds))

        self.counter += 1
        await self.m_channel.send(self.counter)

    @random_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in

    async def on_ready(self):
        logger.info("Bot is ready. Enjoy !!")

    async def setup_hook(self):
        """
        This will just be executed when the bot starts the first time.
        """
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"discord.py API version: {discord.__version__}")
        logger.info(f"Python version: {platform.python_version()}")
        logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        logger.info(f"Database connected: {db.is_closed() is False}")

        # Load all cogs from the cogs directory
        logger.info("Loading cogs...")
        for filename in os.listdir("cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"Loaded cog: {filename[:-3]}")

        # Initialize the database
        db.connect()
        # db.create_tables([BaseModel], safe=True)

    async def on_command_completion(self, context: Context) -> None:
        """
        The code in this event is executed every time a normal
        command has been *successfully* executed.

        :param context: The context of the command that has been executed.
        """
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        if context.guild is not None:
            logger.info(
                f"Executed {executed_command} command in "
                + f"{context.guild.name} (ID: {context.guild.id}) "
                + f"by {context.author} (ID: {context.author.id})"
            )
        else:
            logger.info(
                f"Executed {executed_command} command "
                + "by {context.author} (ID: {context.author.id}) in DMs"
            )

    @logger.catch
    async def on_command_error(self, context: Context, error) -> None:
        """
        The code in this event is executed every time
        a normal valid command catches an error.

        :param context: The context of the normal command that failed executing.
        :param error: The error that has been faced.
        """
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                description="**Please slow down** - "
                + "You can use this command again in"
                + f"{f'{round(hours)} hours' if round(hours) > 0 else ''}"
                + f"{f'{round(minutes)} minutes' if round(minutes) > 0 else ''}"
                + f"{f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                description="You are not the owner of the bot!", color=0xE02B2B
            )
            await context.send(embed=embed)
            if context.guild:
                logger.warning(
                    f"{context.author} (ID: {context.author.id}) "
                    + "tried to execute an owner only command in the guild "
                    + f"{context.guild.name} (ID: {context.guild.id}), "
                    + "but the user is not an owner of the bot. "
                )
            else:
                logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to "
                    + "execute an owner only command in the bot's DMs, but "
                    + "the user is not an owner of the bot."
                )
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="You are missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to execute this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="I am missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to fully perform this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error!",
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        else:
            raise error


# ========================================================
# ========================================================


@logger.catch
def main():
    """Main function to run the Discord bot."""

    logger.info("Starting Discord bot...")

    # Initialize the bot
    bot = DiscordBot()
    bot.run(os.getenv("DISCORD_TOKEN"), log_handler=None)


if __name__ == "__main__":
    main()
