"""RPG Dungeon Master Bot entrypoint."""

import os
import sys

from dotenv import load_dotenv


def validate_env() -> None:
    """Validate required environment variables before importing the bot."""
    required = ["DISCORD_TOKEN"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        print(f"[FATAL] Missing required env vars: {', '.join(missing)}")
        sys.exit(1)

if __name__ == '__main__':
    load_dotenv()
    validate_env()

    from src.bot import main

    main()
