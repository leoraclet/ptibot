import contextlib
import re
from collections import defaultdict

from discord import Message, NotFound
from discord.ext import commands
from loguru import logger

from .api.api import MistralAI


def divide_msg(content):
    parts = []
    while len(content) > 2000:
        split_index = content.rfind(".", 0, 2000)
        if split_index == -1:
            split_index = content.rfind(" ", 0, 2000)
        if split_index == -1:
            split_index = 2000
        parts.append(content[: split_index + 1])
        content = content[split_index + 1 :]
    parts.append(content)

    return parts


class Mistral(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conversations = defaultdict(list)

    @logger.catch
    @commands.Cog.listener()
    async def on_message(self, message: Message):

        logger.debug(f"Received message: {message.content} from {message.author}")
        if message.author.bot:
            return

        logger.debug(f"Processing message in channel {message.channel.id}")
        channel_id = message.channel.id
        ref = message.reference
        replied_message = None
        if ref and ref.message_id:
            with contextlib.suppress(NotFound):
                replied_message = await message.channel.fetch_message(ref.message_id)

        msg = message.content.lower()
        if (
            replied_message
            and replied_message.author == self.bot.user
            or "ptibot" in msg
            or f"<@{self.bot.user.id}>" in msg
        ):
            logger.debug("Message is a reply to the bot or mentions the bot.")
            new = {
                "role": "user",
                "content": re.sub(r"<@1397118403004731514>|ptibot", "", message.content),
            }
            if channel_id in self.conversations:
                self.conversations[channel_id].append(new)
            else:
                self.conversations[channel_id] = [new]

            conversation = self.conversations[channel_id]

            if len(conversation) > 10:
                conversation = conversation[-10:]
            async with message.channel.typing():
                try:
                    answer = await MistralAI.chat_completion(
                        messages=conversation, model="codestral-latest"
                    )
                    conversation.append({"role": "assistant", "content": answer})
                    for part in divide_msg(answer):
                        await message.reply(part)
                except Exception as e:
                    await message.reply(str(e))
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(Mistral(bot))
