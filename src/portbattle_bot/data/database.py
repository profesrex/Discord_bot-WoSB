"""Database utilities for the Portbattle bot.

This module provides a minimal SQLite implementation for the current bot
features and initializes the required tables.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "bot.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_ships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ship_name TEXT NOT NULL,
            ship_class TEXT,
            tier INTEGER,
            UNIQUE(user_id, ship_name)
        )
        """
    )

    conn.commit()
    conn.close()


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)
