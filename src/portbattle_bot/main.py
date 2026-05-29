import asyncio
import logging
import sys
from pathlib import Path

# Projekt-Root zum Python-Path hinzufügen
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import discord
from discord.ext import commands

from .config import config
from .data.database import init_db

logger = logging.getLogger("portbattle_bot")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler("portbattle.log", encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=config.PREFIX, intents=intents)

    async def setup_hook(self):
        init_db()
        logger.info("Database initialized")

        await self.load_extension("portbattle_bot.cogs.portbattle")
        logger.info("Loaded cog: portbattle")

        await self.load_extension("portbattle_bot.cogs.flotte")
        logger.info("Loaded cog: flotte")

        await self.load_extension("portbattle_bot.cogs.portbattle_extra")
        logger.info("Loaded cog: portbattle_extra")


bot = Bot()


@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        await bot.tree.sync()
        logger.info("Application commands synced successfully")
    except Exception as e:
        logger.exception("Failed to sync application commands")


async def main():
    token = config.DISCORD_TOKEN
    if not token:
        logger.error("DISCORD_TOKEN is not set in .env file!")
        return

    async with bot:
        await bot.start(token)


def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    except Exception:
        logger.exception("Unexpected error occurred")


if __name__ == "__main__":
    run()