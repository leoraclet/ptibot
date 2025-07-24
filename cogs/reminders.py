from datetime import datetime, timedelta

from dateparser import parse
from discord import Embed, Interaction, NotFound, app_commands
from discord.ext import commands, tasks

from config import CALENDAR_CHANNEL, ConfigManager

# TODO: Handle Timezone issues
# TODO: Add a way to set the timezone for the reminders


class Reminders(commands.Cog, name="reminders"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminders = ConfigManager.get("reminders", [])

        # Start the reminder check task
        self.check_reminders.start()

    async def course_autocomplete(
        self, _: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        courses = [reminder["name"] for reminder in self.reminders]
        return [
            app_commands.Choice(name=course, value=course)
            for course in courses
            if current.lower() in course.lower()
        ]

    async def event_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        option = interaction.namespace.option
        course = interaction.namespace.course
        courses = [reminder["name"] for reminder in self.reminders]
        if option not in ["2", "3"] and course not in courses:
            return []

        return [
            app_commands.Choice(name=field["name"], value=field["name"])
            for field in self.reminders[courses.index(course)]["fields"]
            if current.lower() in field["name"].lower()
        ]

    @app_commands.command(name="reminder", description="Etablit un rappel pour un événement.")
    @app_commands.describe(
        course="Choisir le cours.",
        date="Choisir la date de l'événement.",
        event="Nom de l'événement",
        modality="Modalité de l'événement",
    )
    @app_commands.choices(
        option=[
            app_commands.Choice(name="add", value="1"),
            app_commands.Choice(name="edit", value="2"),
            app_commands.Choice(name="remove", value="3"),
        ]
    )
    @app_commands.autocomplete(course=course_autocomplete)
    @app_commands.autocomplete(event=event_autocomplete)
    async def reminder_command(
        self,
        interaction: Interaction,
        option: app_commands.Choice[str],
        course: str,
        date: str,
        event: str,
        description: str = "",
        modality: str = "",
    ):
        try:
            if " " not in date:
                date += " 23:59"
            try:
                reminder_date = datetime.strptime(date, "%d/%m/%Y %H:%M")
            except ValueError:
                reminder_date = parse(
                    date,
                    languages=["fr", "en"],
                    settings={
                        "RETURN_AS_TIMEZONE_AWARE": False,
                        "PREFER_DATES_FROM": "future",
                        "PREFER_DAY_OF_MONTH": "first",
                        "PREFER_LOCALE_DATE_ORDER": True,
                        "PREFER_MONTH_OF_YEAR": "current",
                    },
                )
                if reminder_date.hour == 0 and reminder_date.minute == 0:
                    reminder_date = reminder_date.replace(hour=23, minute=59)

                if not reminder_date:
                    raise ValueError("Invalid date format") from ValueError

            reminder_timestamp = f"<t:{int(reminder_date.timestamp())}:R>"
            calendar_message_id = ConfigManager.get("calendar_message_id", 0)
            calendar_channel = self.bot.get_channel(CALENDAR_CHANNEL.id)

            if description:
                description = f"{description}\n\n"
            if modality:
                modality = f"\n\n``{modality}``"

            match option.name:
                case "add":
                    reminder = {
                        "name": course,
                        "fields": [
                            {
                                "name": event,
                                "date": f"{reminder_date.date().__str__()} {reminder_date.time().__str__()[:5]}",
                                "description": description,
                                "modality": modality,
                            }
                        ],
                    }

                    try:
                        msg = await calendar_channel.fetch_message(calendar_message_id)
                        for embed in msg.embeds:
                            if embed.title == course.upper():
                                embed.add_field(
                                    name=f"__{event}__",
                                    value=f"{description}Echéance: {reminder_timestamp}{modality}",
                                    inline=False,
                                )
                                embed.fields.sort(
                                    key=lambda field: datetime.fromtimestamp(
                                        int(field.value.split("Echéance: <t:")[1].split(":")[0])
                                    ),
                                    reverse=True,
                                )
                                msg.embeds.sort(
                                    key=lambda embed: datetime.fromtimestamp(
                                        int(
                                            embed.fields[-1]
                                            .value.split("Echéance: <t:")[1]
                                            .split(":")[0]
                                        )
                                    ),
                                    reverse=True,
                                )
                                await msg.edit(embeds=msg.embeds)
                                break
                        else:
                            embed = Embed(title=course.upper())
                            embed.add_field(
                                name=f"__{event}__",
                                value=f"{description}Echéance: {reminder_timestamp}{modality}",
                                inline=False,
                            )
                            msg.embeds.append(embed)
                            msg.embeds.sort(
                                key=lambda embed: datetime.fromtimestamp(
                                    int(
                                        embed.fields[-1]
                                        .value.split("Echéance: <t:")[1]
                                        .split(":")[0]
                                    )
                                ),
                                reverse=True,
                            )
                            await msg.edit(embeds=msg.embeds)
                    except NotFound:
                        embed = Embed(title=course.upper())
                        embed.add_field(
                            name=f"__{event}__",
                            value=f"{description}Echéance: {reminder_timestamp}{modality}",
                            inline=False,
                        )
                        msg = await calendar_channel.send(embed=embed)
                        ConfigManager.set("calendar_message_id", msg.id)

                    for existing_reminder in self.reminders:
                        if existing_reminder["name"] == course:
                            existing_reminder["fields"].append(reminder["fields"][0])
                            break
                    else:
                        self.reminders.append(reminder)
                    ConfigManager.set("reminders", self.reminders)
                    await interaction.response.send_message(
                        f"Rappel créé pour {reminder_timestamp}", ephemeral=True
                    )
                case "edit":
                    try:
                        msg = await calendar_channel.fetch_message(calendar_message_id)
                        for embed in msg.embeds:
                            if embed.title == course.upper():
                                for index, field in enumerate(embed.fields):
                                    if event in field.name:
                                        embed.set_field_at(
                                            index,
                                            name=f"__{event}__",
                                            value=f"{description}Echéance: {reminder_timestamp}{modality}",
                                            inline=False,
                                        )
                                        embed.fields.sort(
                                            key=lambda field: datetime.fromtimestamp(
                                                int(
                                                    field.value.split("Echéance: <t:")[1].split(
                                                        ":"
                                                    )[0]
                                                )
                                            ),
                                            reverse=True,
                                        )
                                        msg.embeds.sort(
                                            key=lambda embed: datetime.fromtimestamp(
                                                int(
                                                    embed.fields[-1]
                                                    .value.split("Echéance: <t:")[1]
                                                    .split(":")[0]
                                                )
                                            ),
                                            reverse=True,
                                        )
                                        await msg.edit(embeds=msg.embeds)
                                        for existing_reminder in self.reminders:
                                            if existing_reminder["name"] == course:
                                                for field in existing_reminder["fields"]:
                                                    if field["name"] == event:
                                                        field["date"] = (
                                                            f"{reminder_date.date().__str__()} {reminder_date.time().__str__()[:5]}"
                                                        )
                                                        field["description"] = description
                                                        field["modality"] = modality
                                                        break
                                                break

                                        ConfigManager.set("reminders", self.reminders)

                                        await interaction.response.send_message(
                                            f"Rappel pour l'événement '{event}' du cours '{course}' modifié.",
                                            ephemeral=True,
                                        )
                                        break
                                else:
                                    await interaction.response.send_message(
                                        "Événement non trouvé.", ephemeral=True
                                    )
                                break
                        else:
                            await interaction.response.send_message(
                                "Cours non trouvé.", ephemeral=True
                            )
                    except NotFound:
                        await interaction.response.send_message(
                            "Aucun message de rappel trouvé.", ephemeral=True
                        )
                case "remove":
                    for existing_reminder in self.reminders:
                        if existing_reminder["name"] == course:
                            for field in existing_reminder["fields"]:
                                if field["name"] == event:
                                    await self.remove_event(
                                        existing_reminder, field, calendar_channel
                                    )
                                    await interaction.response.send_message(
                                        f"Rappel pour l'événement '{event}' du cours '{course}' supprimé.",
                                        ephemeral=True,
                                    )
                                    break
                            else:
                                await interaction.response.send_message(
                                    "Événement non trouvé.", ephemeral=True
                                )
                            break
                    else:
                        await interaction.response.send_message("Cours non trouvé.", ephemeral=True)

        except ValueError:
            await interaction.response.send_message(
                "Format invalide - JJ/MM/AAAA <HH:II>.", ephemeral=True
            )

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        now = datetime.now()
        calendar_channel = self.bot.get_channel(CALENDAR_CHANNEL.id)
        for reminder in self.reminders:
            for event in reminder["fields"]:
                event_time = datetime.strptime(event["date"], "%Y-%m-%d %H:%M")
                if (
                    now + timedelta(hours=1) - timedelta(seconds=30)
                    <= event_time
                    <= now + timedelta(hours=1) + timedelta(seconds=30)
                ):
                    await calendar_channel.send(
                        f":warning: L'échéance *{event['name']}* du cours "
                        + f"**{reminder['name'].upper()}** a lieu dans 1 heure !\n|| @everyone ||",
                        delete_after=3600,
                    )
                elif (
                    now + timedelta(days=1) - timedelta(seconds=30)
                    <= event_time
                    <= now + timedelta(days=1) + timedelta(seconds=30)
                ):
                    await calendar_channel.send(
                        f":warning: L'échéance *{event['name']}* du cours "
                        + f"**{reminder['name'].upper()}** a lieu dans 1 jour !\n|| @everyone ||",
                        delete_after=3600,
                    )
                elif (
                    now + timedelta(weeks=1) - timedelta(seconds=30)
                    <= event_time
                    <= now + timedelta(weeks=1) + timedelta(seconds=30)
                ):
                    await calendar_channel.send(
                        f":warning: L'échéance *{event['name']}* du cours "
                        + f"**{reminder['name'].upper()}** a lieu dans 1 semaine !\n|| @everyone ||",
                        delete_after=3600,
                    )
                elif event_time <= now:
                    await calendar_channel.send(
                        f":warning: L'échéance *{event['name']}* du cours "
                        + f"**{reminder['name'].upper()}** vient d'avoir lieu !\n|| @everyone ||",
                        delete_after=60,
                    )
                    await self.remove_event(reminder, event, calendar_channel)

    async def remove_event(self, reminder, event, calendar_channel):
        try:
            msg = await calendar_channel.fetch_message(ConfigManager.get("calendar_message_id", 0))
            for embed in msg.embeds:
                if embed.title == reminder["name"].upper():
                    fields_to_remove = [
                        field for field in embed.fields if event["name"] in field.name
                    ]
                    for field in fields_to_remove:
                        embed.remove_field(embed.fields.index(field))
                    if not embed.fields:
                        msg.embeds.remove(embed)
                        if not msg.embeds:
                            await msg.delete()
                            ConfigManager.remove("calendar_message_id")
                            break
                    else:
                        msg.embeds.sort(
                            key=lambda embed: datetime.fromtimestamp(
                                int(embed.fields[-1].value.split("Echéance: <t:")[1].split(":")[0])
                            ),
                            reverse=True,
                        )
                    await msg.edit(embeds=msg.embeds)
                    break
        except NotFound:
            pass

        reminder["fields"] = [
            field for field in reminder["fields"] if field["name"] != event["name"]
        ]
        if not reminder["fields"]:
            self.reminders.remove(reminder)

        ConfigManager.set("reminders", self.reminders)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Reminders(bot))
