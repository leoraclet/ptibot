from discord import Embed, Interaction, app_commands
from discord.ext import commands
from loguru import logger

from config import TODO_CHANNEL, ConfigManager

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


def update_embed(embeds, todos):
    new_value = "\n".join(
        [
            f"{i}. {'✅' if tool['completed'] else '❌'}**"
            + f"{' - ' + tool['task'] if tool['task'] else ''}**"
            for i, tool in enumerate(todos, 1)
        ]
    )

    for embed in embeds:
        try:
            embed.set_field_at(0, name="__MY TASKS__", value=new_value, inline=False)
            break
        except IndexError:
            # If the field does not exist, we will add it later
            continue
    else:
        embed.add_field(name="__MY TASKS__", value=new_value, inline=False)
        return


class Todo(commands.Cog, name="todo"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.todos = ConfigManager.get("todos", [])

        self.message_id = ConfigManager.get("todos_message_id")

    async def task_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        option = interaction.namespace.option
        if option == "3":
            tasks = [
                todo["task"] for todo in ConfigManager.get("todos", []) if not todo["completed"]
            ]
        else:
            tasks = [todo["task"] for todo in ConfigManager.get("todos", [])]

        return [
            app_commands.Choice(name=task, value=task)
            for task in tasks
            if current.lower() in task.lower()
        ]

    @app_commands.command(name="todo")
    @app_commands.describe(
        task="Description de la tâche.",
    )
    @commands.is_owner()
    @app_commands.choices(
        option=[
            app_commands.Choice(name="add", value="1"),
            app_commands.Choice(name="remove", value="2"),
            app_commands.Choice(name="complete", value="3"),
        ]
    )
    @app_commands.autocomplete(task=task_autocomplete)
    async def todo_command(
        self,
        interaction: Interaction,
        option: app_commands.Choice[str],
        task: str,
    ):
        if not task:
            await interaction.response.send_message(
                "Veuillez fournir une description de la tâche.",
                ephemeral=True,
            )
            return
        todos_channel = interaction.guild.get_channel(TODO_CHANNEL.id)
        logger.info(f"Todos channel: {todos_channel}")

        try:
            # Try to fetch the todos message
            msg = await todos_channel.fetch_message(self.message_id)
        except Exception:
            # If it doesn't exist, create a new message with an empty embed
            msg = await todos_channel.send(
                embeds=[Embed(title="Tâches", description="Liste des Tâches à faire")],
            )
            ConfigManager.set("todos_message_id", msg.id)
            self.message_id = msg.id

        formatted_time = interaction.created_at.strftime("%Y-%m-%d %H:%M:%S")

        todos = ConfigManager.get("todos", [])
        logger.info(f"Current todos: {todos}")

        match option.name:
            case "add":
                store = {"task": task, "completed": False}

                if len(todos) < 10:
                    todos.append(store)
                    update_embed(msg.embeds, todos)
                    msg.embeds[-1].set_footer(
                        text=f"Last update by {interaction.user.display_name} at {formatted_time}",
                        icon_url=interaction.user.avatar.url,
                    )
                    msg.embeds[-1].title = "Tâches à faire 📝"
                    await msg.edit(embeds=msg.embeds)
                else:
                    interaction.response.send_message(
                        "Limite de 10 tâches atteinte.", ephemeral=True
                    )
                    return

                ConfigManager.set("todos", todos)

                await interaction.response.send_message(f"Tâche {task} créé", ephemeral=True)

            case "remove" | "complete":
                for index, existing_todo in enumerate(todos, 1):
                    if existing_todo["task"].lower() == task.lower():
                        if option.name == "complete":
                            todos[index - 1]["completed"] = True
                            await interaction.response.send_message(
                                f"Tâche {task} marquée comme terminée", ephemeral=True
                            )
                        else:
                            del todos[index - 1]

                            msg.embeds[-1].set_footer(
                                text=f"Last update by {interaction.user.display_name} at "
                                + f"{formatted_time}",
                                icon_url=interaction.user.avatar.url,
                            )
                            await interaction.response.send_message(
                                f"Tâche {task} supprimée", ephemeral=True
                            )

                        if all(todo["completed"] for todo in todos):
                            msg.embeds[-1].title = "Toutes les tâches sont terminées ! 🎉"
                            todos.clear()

                        update_embed(msg.embeds, todos)
                        await msg.edit(embeds=msg.embeds)
                        ConfigManager.set("todos", todos)

                        break
                else:
                    await interaction.response.send_message("Tâche non trouvée.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Todo(bot))
