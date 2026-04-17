# RPG Dungeon Master Bot

RPG Dungeon Master Bot is an AI-powered Discord bot for tabletop-style campaigns. It helps a server run persistent characters, quests, combat, inventory, NPCs, and session-based story progression across Discord and the web dashboard.

It is designed for two modes of play: players can join and play through Discord or browser chat, while dungeon masters and operators can manage campaigns, game data, and world state from the web UI.

## Highlights
- Persistent characters, sessions, combat, quests, spells, skills, and inventory
- AI DM narration, NPC dialogue, and tool-driven gameplay flow
- Browser chat with shared session state and live dashboard panels
- Web admin tools for campaigns, locations, NPCs, items, spells, and game data
- Content-pack aware runtime data for themed campaigns

## Quick Start
For setup, hosting, and environment configuration, see the [Operator Guide](docs/operator-guide.md).

## Documentation
- [Player Guide](docs/player-guide.md)
- [Dungeon Master Guide](docs/dm-guide.md)
- [Operator / Self-Hosting Guide](docs/operator-guide.md)

## Project Structure
```text
rpg-dm-bot/
├── run.py              # Entry point
├── requirements.txt    # Dependencies
├── .env               # Environment variables (not in repo)
├── .gitignore         # Git ignore file
├── data/
│   ├── rpg.db         # SQLite database (created at runtime)
│   └── game_data/     # Static game data (classes, races, items)
├── logs/              # Log files
├── src/
│   ├── bot.py         # Main bot class
│   ├── database.py    # Database operations
│   ├── llm.py         # LLM integration
│   ├── prompts.py     # System prompts
│   ├── tools.py       # Tool executor
│   ├── tool_schemas.py # Tool definitions
│   └── cogs/
│       ├── characters.py  # Character management
│       ├── combat.py      # Combat system
│       ├── inventory.py   # Inventory management
│       ├── quests.py      # Quest system
│       ├── npcs.py        # NPC interactions
│       ├── dice.py        # Dice rolling
│       ├── spells.py      # Spells, spell slot management, and casting UI
│       ├── sessions.py    # Session management
│       ├── dm_chat.py     # AI chat/narration
│       └── game_master.py # Game flow management
└── tests/             # Unit tests
```

## Contributing
Contributions are welcome. Please open an issue or pull request if you find a bug or want to improve the project.

## License
MIT License. See the repository license for details.
