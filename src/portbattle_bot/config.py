import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    
    # Channel & Rollen
    ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID", "0").strip())
    ADMIRAL_ROLE_ID = int(os.getenv("ADMIRAL_ROLE_ID", "0").strip())
    
    # Bot Einstellungen
    PREFIX = "!"
    TEST_MODE = False  # Später für Tests nutzbar


config = Config()
