import asyncio
import logging
import discord
from discord.ext import commands

from .config import config

logger = logging.getLogger("portbattle_bot")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler("portbattle.log", encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


async def main():
    intents = discord.Intents.default()
    intents.message_content = False

    bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
        try:
            await bot.tree.sync()
            logger.info("Application commands synced")
        except Exception:
            logger.exception("Failed to sync application commands")

    # Load cogs
    try:
        await bot.load_extension("portbattle_bot.cogs.portbattle")
        logger.info("Loaded cogs.portbattle")
    except Exception:
        logger.exception("Failed to load cogs")

    token = config.DISCORD_TOKEN
    if not token:
        logger.error("DISCORD_TOKEN is not set. Please add it to your .env file.")
        return

    await bot.start(token)


def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    run()
