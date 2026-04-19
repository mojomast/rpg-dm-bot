"""RPG Dungeon Master Bot entrypoint."""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "rpg.log"


def configure_logging() -> None:
    """Configure file and stdout logging before bot startup."""
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)
    logging.getLogger('discord').setLevel(logging.INFO)
    logging.getLogger('rpg.llm').setLevel(logging.DEBUG)


def validate_env() -> None:
    """Validate required environment variables before importing the bot."""
    required = ["DISCORD_TOKEN"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        logging.getLogger('rpg').critical("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)

if __name__ == '__main__':
    load_dotenv()
    configure_logging()
    validate_env()

    from src.bot import main

    main()
