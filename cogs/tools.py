from discord import Embed, Interaction, app_commands
from discord.ext import commands

from config import TOOLS_CHANNEL, ConfigManager


def update_embed(embeds, category, tools):
    new_value = "\n".join(
        [
            f"{i}. **{tool['tool']}**{': ' + tool['description'] if tool['description'] else ''}"
            for i, tool in enumerate(tools, 1)
        ]
    )
    for embed in embeds:
        for index, field in enumerate(embed.fields):
            if field.name == f"__{category.upper()}__":
                embed.set_field_at(index, name=field.name, value=new_value, inline=False)
                return
    for embed in embeds:
        if len(embed.fields) < 4:
            embed.add_field(name=f"__{category.upper()}__", value=new_value, inline=False)
            return
    new_embed = Embed()
    new_embed.add_field(name=f"__{category.upper()}__", value=new_value, inline=False)
    embeds.append(new_embed)


class Tools(commands.Cog, name="tools"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_id = ConfigManager.get("tools_message_id", 0)

    async def category_autocomplete(
        self, _: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        categories = [tool["category"] for tool in ConfigManager.get("tools", [])]
        return [
            app_commands.Choice(name=category, value=category)
            for category in categories
            if current.lower() in category.lower()
        ]

    async def tool_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        option = interaction.namespace.option
        category = interaction.namespace.category
        tools = ConfigManager.get("tools", [])
        categories = [tool["category"] for tool in tools]

        if option not in ["2", "3"] and category not in categories:
            return []

        return [
            app_commands.Choice(name=field["tool"], value=field["tool"])
            for field in tools[categories.index(category)]["fields"]
            if current.lower() in field["tool"].lower()
        ]

    @app_commands.command(description="Ajouter, modifier ou supprimer un outil.")
    @app_commands.describe(
        category="Choisir la catégorie.",
        tool="Nom de l'outil.",
        description="Description de l'outil.",
    )
    @commands.is_owner()
    @app_commands.choices(
        option=[
            app_commands.Choice(name="add", value="1"),
            app_commands.Choice(name="edit", value="modifié"),
            app_commands.Choice(name="remove", value="supprimé"),
        ]
    )
    @app_commands.autocomplete(category=category_autocomplete)
    @app_commands.autocomplete(tool=tool_autocomplete)
    async def tool(
        self,
        interaction: Interaction,
        option: app_commands.Choice[str],
        category: str,
        tool: str = None,
        description: str = "",
    ):
        tools_channel = interaction.guild.get_channel(TOOLS_CHANNEL.id)

        try:
            # Try to fetch the tools message
            msg = await tools_channel.fetch_message(self.message_id)
        except Exception:
            # If it doesn't exist, create a new message with an empty embed
            msg = await tools_channel.send(
                embeds=[
                    Embed(
                        title="Outils", description="Liste des outils disponibles, par catégorie."
                    )
                ],
            )
            ConfigManager.set("tools_message_id", msg.id)
            self.message_id = msg.id

        formatted_time = interaction.created_at.strftime("%Y-%m-%d %H:%M:%S")

        tools = ConfigManager.get("tools", [])

        match option.name:
            case "add":
                store = {
                    "category": category,
                    "fields": [{"tool": tool, "description": description}],
                }

                for existing_tool in tools:
                    if existing_tool["category"].lower() == category.lower():
                        existing_tool["fields"].append(store["fields"][0])
                        update_embed(msg.embeds, category, existing_tool["fields"])
                        msg.embeds[-1].set_footer(
                            text=f"Last update by {interaction.user.display_name} at {formatted_time}",
                            icon_url=interaction.user.avatar.url,
                        )
                        await msg.edit(embeds=msg.embeds)
                        break
                else:
                    tools.append(store)
                    update_embed(msg.embeds, category, store["fields"])
                    msg.embeds[-1].set_footer(
                        text=f"Last update by {interaction.user.display_name} at {formatted_time}",
                        icon_url=interaction.user.avatar.url,
                    )
                    await msg.edit(embeds=msg.embeds)

                ConfigManager.set("tools", tools)

                await interaction.response.send_message(
                    f"Outil {tool} créé dans la catégorie {category}", ephemeral=True
                )

            case "edit" | "remove":
                for index, existing_tool in enumerate(tools, 1):
                    if existing_tool["category"].lower() == category.lower():
                        if 0 <= index - 1 < len(existing_tool["fields"]):
                            t = existing_tool["fields"][index - 1]["tool"]
                            if option.name == "edit":
                                if tool is not None:
                                    existing_tool["fields"][index - 1]["tool"] = tool
                                existing_tool["fields"][index - 1]["description"] = (
                                    description
                                    if description
                                    else existing_tool["fields"][index - 1]["description"]
                                )
                                update_embed(msg.embeds, category, existing_tool["fields"])
                            else:
                                del existing_tool["fields"][index - 1]
                                if existing_tool["fields"]:
                                    update_embed(msg.embeds, category, existing_tool["fields"])
                                else:
                                    for embed in msg.embeds:
                                        for field_index, field in enumerate(embed.fields):
                                            if field.name == f"__{category.upper()}__":
                                                embed.remove_field(field_index)
                                                break
                            msg.embeds[-1].set_footer(
                                text=f"Last update by {interaction.user.display_name} at {formatted_time}",
                                icon_url=interaction.user.avatar.url,
                            )
                            await msg.edit(embeds=msg.embeds)
                            await interaction.response.send_message(
                                f"Outil {t} dans la catégorie {category} {option.value}.",
                                ephemeral=True,
                            )
                            ConfigManager.set("tools", tools)
                        else:
                            await interaction.response.send_message(
                                "Index non trouvé.", ephemeral=True
                            )
                        break
                else:
                    await interaction.response.send_message(
                        "Catégorie non trouvée.", ephemeral=True
                    )


async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))
