import datetime
import time

import google.auth
import requests
from discord.ext import commands, tasks
from googleapiclient.discovery import build
from loguru import logger
from utils.config import (
    DAYS_IN_FUTURE,
    DISCORD_BOT_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_GUILD_ID,
    GOOGLE_CALENDAR_ID,
    GOOGLE_CREDENTIALS_JSON,
    SYNC_INTERVAL,
    ConfigManager,
)


def get_google_calendar_service():
    """
    Set up the Google Calendar API service using the provided credentials.
    """
    credentials, _ = google.auth.load_credentials_from_file(GOOGLE_CREDENTIALS_JSON)
    service = build("calendar", "v3", credentials=credentials)
    return service


def get_upcoming_events(service):
    """
    Fetch upcoming events from Google Calendar within the specified time frame.
    """
    logger.info(f"Requesting events from Google Calendar for the next {DAYS_IN_FUTURE} days.")
    now = datetime.datetime.utcnow()
    time_min = now.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    time_max = (now + datetime.timedelta(days=DAYS_IN_FUTURE)).strftime("%Y-%m-%dT%H:%M:%S") + "Z"

    events_result = (
        service.events()
        .list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=100,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def get_discord_events():
    """
    Fetch existing scheduled events from the Discord server.
    """
    logger.info("Requesting events from Discord.")
    url = f"https://discord.com/api/v9/guilds/{DISCORD_GUILD_ID}/scheduled-events"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to fetch Discord events: {response.content}")
        return []


def create_or_update_discord_event(event, discord_event_id=None):
    """
    Create a new scheduled event on Discord or update an existing one.
    """
    if discord_event_id is None:
        # Creating a new event
        url = f"https://discord.com/api/v9/guilds/{DISCORD_GUILD_ID}/scheduled-events"
        method = requests.post
    else:
        # Updating an existing event
        url = f"https://discord.com/api/v9/guilds/{DISCORD_GUILD_ID}/scheduled-events/{discord_event_id}"
        method = requests.patch

    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}

    # Get start and end times, handling all-day events
    start_time = event["start"].get("dateTime", event["start"].get("date"))
    end_time = event["end"].get("dateTime", event["end"].get("date"))

    if "date" in event["start"]:
        start_time += "T00:00:00Z"
        end_time += "T23:59:59Z"

    data = {
        "name": event["summary"],
        "description": event.get("description", ""),
        "scheduled_start_time": start_time,
        "scheduled_end_time": end_time,
        "privacy_level": 2,
        "entity_type": 2,
        "channel_id": DISCORD_CHANNEL_ID,
    }

    response = method(url, json=data, headers=headers)
    time.sleep(2)  # Pause to respect rate limits
    if response.status_code in (200, 201):
        action = "updated" if discord_event_id else "created"
        logger.info(f"Event {event['summary']} {action} on Discord")
        return response.json().get("id")
    else:
        action = "update" if discord_event_id else "create"
        logger.error(f"Failed to {action} event {event['summary']} on Discord: {response.content}")
        return None


def delete_discord_event(event_id):
    """
    Delete a scheduled event from Discord using its event ID.
    """
    url = f"https://discord.com/api/v9/guilds/{DISCORD_GUILD_ID}/scheduled-events/{event_id}"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    response = requests.delete(url, headers=headers)
    time.sleep(2)  # Pause to respect rate limits
    if response.status_code == 204:
        logger.info(f"Event {event_id} deleted from Discord")
    else:
        logger.error(f"Failed to delete event {event_id} from Discord: {response.content}")


class Calendar(commands.Cog, name="calendar"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.synced_events = ConfigManager.get("synced_events", {"events": []})

    @logger.catch
    @tasks.loop(seconds=SYNC_INTERVAL)
    async def sync_events_loop(self):
        """
        Periodically synchronize events from Google Calendar to Discord.
        """
        try:
            service = get_google_calendar_service()
            events = get_upcoming_events(service)
            discord_events = get_discord_events()

            # Create a set of current Discord event IDs for quick lookup
            discord_event_ids = {event["id"] for event in discord_events}

            for event in events:
                time.sleep(2)  # Pause to respect rate limits
                event_id = event["id"]
                event_data = {
                    "date": event["start"].get("dateTime", event["start"].get("date")),
                    "title": event["summary"],
                    "channel": DISCORD_CHANNEL_ID,
                    "notes": event.get("description", ""),
                }

                # Check if the event has already been synchronized
                if any(e["google_event_id"] == event_id for e in self.synced_events["events"]):
                    for synced_event in self.synced_events["events"]:
                        if synced_event["google_event_id"] == event_id:
                            discord_event_id = synced_event["discord_event_id"]
                            if discord_event_id not in discord_event_ids:
                                # The event is missing on Discord, recreate it
                                logger.info(
                                    f"Event {event['summary']} is missing on Discord, recreating"
                                )
                                discord_event_id = create_or_update_discord_event(event)
                                if discord_event_id:
                                    synced_event["discord_event_id"] = discord_event_id
                                    synced_event.update(event_data)
                                    ConfigManager.set("synced_events", self.synced_events)
                            else:
                                # Update the existing Discord event
                                discord_event_id = create_or_update_discord_event(
                                    event, discord_event_id
                                )
                                if discord_event_id:
                                    synced_event.update(event_data)
                                    ConfigManager.set("synced_events", self.synced_events)
                            break
                else:
                    # The event is new, create it on Discord
                    discord_event_id = create_or_update_discord_event(event)
                    if discord_event_id:
                        self.synced_events["events"].append(
                            {
                                "google_event_id": event_id,
                                "discord_event_id": discord_event_id,
                                **event_data,
                            }
                        )
                        ConfigManager.set("synced_events", self.synced_events)

            # Remove events from Discord that no longer exist in Google Calendar
            google_event_ids = {event["id"] for event in events}
            for synced_event in list(self.synced_events["events"]):
                time.sleep(2)  # Pause to respect rate limits
                if synced_event["google_event_id"] not in google_event_ids:
                    delete_discord_event(synced_event["discord_event_id"])
                    self.synced_events["events"].remove(synced_event)
                    ConfigManager.set("synced_events", self.synced_events)

        except Exception as e:
            logger.error(f"Error in sync_events_loop: {e}")
