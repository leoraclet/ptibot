import json
import os

from discord import Guild, Object, TextChannel, VoiceChannel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================ #
# CHANNELS
# ============================================ #

GUILD = Object(829032123301494834, type=Guild)  # Replace with your actual guild ID))

ANNOUNCEMENTS_CHANNEL = Object(1238843334387175484, type=TextChannel)
ALERT_CHANNEL = Object(1281994195137204256, type=TextChannel)
NEWS_CHANNEL = Object(1397543924901613679, type=TextChannel)
BOT_CHANNEL = Object(1397259312602288208, type=TextChannel)
CALENDAR_CHANNEL = Object(1058816788328091810, type=TextChannel)
LOGS_CHANNEL = Object(1397918688249905273, type=TextChannel)
GITHUB_CHANNEL = Object(1397931684720279624, type=TextChannel)
EVENTS_CHANNEL = Object(1398033188454138127, type=VoiceChannel)
TOOLS_CHANNEL = Object(1398205767827460148, type=TextChannel)
TODO_CHANNEL = Object(1398338757110927401, type=TextChannel)

# ============================================ #
# DISCORD BOT CONFIGURATION
# ============================================ #

DISCORD_GUILD_ID = int(GUILD.id)  # Use the guild ID from the GUILD object
DISCORD_CHANNEL_ID = int(EVENTS_CHANNEL.id)  # Use the channel ID from the EVENTS_CHANNEL object

DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
DAYS_IN_FUTURE = int(os.getenv("DAYS_IN_FUTURE", 90))  # Number of days to look ahead for events
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 60))  # In seconds

# ============================================ #
# COLORS
# ============================================ #

MAIN_COLOR = 0x476EFC

# ============================================ #
# CONFIGURATION MANAGER
# ============================================ #


class ConfigManager:
    path = "db/config.json"
    config = {}

    @classmethod
    def load(cls):
        if os.path.exists(cls.path):
            with open(cls.path, encoding="utf-8") as f:
                cls.config = json.load(f)

    @classmethod
    def get(cls, key, default=None):
        return cls.config.get(key, default)

    @classmethod
    def set(cls, key, value):
        cls.config[key] = value
        cls.save()

    @classmethod
    def append(cls, key, value):
        if key in cls.config and isinstance(cls.config[key], list):
            cls.config[key].append(value)
        else:
            cls.config[key] = [value]
        cls.save()

    @classmethod
    def remove(cls, key):
        if key in cls.config:
            del cls.config[key]
            cls.save()

    @classmethod
    def save(cls):
        with open(cls.path, "w", encoding="utf-8") as f:
            json.dump(cls.config, f, indent=4)
