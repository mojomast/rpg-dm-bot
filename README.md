# 🎲 RPG Dungeon Master Bot

An AI-powered Discord bot that serves as a Dungeon Master for tabletop RPG games. Features persistent characters, combat mechanics, inventory management, interactive NPCs, multiplayer sessions, AI-driven storytelling, and a web dashboard for game management.

> **🤖 AI-Generated Project**: This entire project was created by giving Claude Opus 4.5 a single prompt asking it to transform [ussybot](https://github.com/kyleawayan/ussybot) into an RPG Dungeon Master bot. The AI designed the architecture, implemented all features, wrote tests, and created documentation autonomously.

## ✨ Features

### 🧙 Character System
- **Character Creation**: Create persistent characters with race, class, stats, and backstory
- **Stat Management**: Track HP, mana, experience, and level progression
- **Multiple Characters**: Players can have multiple characters across different campaigns
- **Character Sheet**: View detailed character information with `/character sheet`

### ⚔️ Combat System
- **Turn-Based Combat**: Initiative tracking with automatic turn order
- **Actions**: Attack, defend, cast spells, use items, or flee
- **Status Effects**: Poison, stun, buff/debuff tracking
- **Combat Log**: Detailed combat narration by the AI DM

### 🎒 Inventory System
- **Item Management**: Collect, use, and trade items
- **Equipment Slots**: Weapon, armor, accessory slots with stat bonuses
- **Gold Economy**: Earn and spend gold at shops
- **Crafting**: Combine items to create new ones
- **Auto-Equip**: Starter kits and purchased equipment can be automatically equipped to appropriate slots (e.g., weapons to main hand, armor to body).

### 📜 Quest System
- **Quest Planning**: DMs can create detailed quest plans with objectives
- **Quest Progress**: Track objectives and milestones
- **Rewards**: Automatic reward distribution on completion
- **Branching Paths**: Multiple quest outcomes based on player choices

### 🗣️ NPC System
- **Interactive NPCs**: AI-powered dialogue with persistent NPCs
- **Relationships**: Track player-NPC relationships and reputation
- **Merchants**: Buy and sell items with NPCs
- **Quest Givers**: NPCs can offer and track quests
- **NPC Party Members**: Recruit NPCs as companions who travel with you
- **Loyalty System**: NPC companions have loyalty (0-100) that changes based on party actions
- **Combat Assistance**: Party NPCs can attack, defend, heal, and use abilities in combat

### 🌍 Generative AI Worldbuilding
- **Campaign Initialization**: One command generates starting location, key NPCs, and quest hooks
- **World Generation**: Create regions, cities, dungeons with thematic content
- **Dynamic NPCs**: Generate key NPCs (allies, villains, mentors) that fit your campaign theme
- **Quest Generation**: Auto-generate quests with objectives and scaled rewards
- **Encounter Generation**: Create combat, social, puzzle, or trap encounters scaled to party
- **Backstory Generation**: Expand character backstories with plot connections
- **Loot Generation**: Context-appropriate loot scaled to party level
- **Theme Support**: All generation respects campaign theme (Duke Nukem style, fantasy, grimdark, etc.)

### 🎲 Dice Rolling
- **Standard Dice**: Roll any dice (d4, d6, d8, d10, d12, d20, d100)
- **Modifiers**: Add bonuses from stats or equipment
- **Advantage/Disadvantage**: Roll with advantage or disadvantage
- **Interactive Rolls**: Buttons for quick re-rolls

### 👥 Multiplayer Sessions
- **Campaign Management**: Create and join campaigns
- **Session Tracking**: Track active sessions and participants
- **Party System**: Form adventuring parties
- **Shared Progress**: All players see the same story progression
- **Session Isolation**: Multiple games can run simultaneously without context bleed - the AI DM correctly tracks which characters belong to which session
- **Interactive Session Menu**: Use `/game list` to browse, select, join, and manage sessions using a comprehensive session UI with per-session controls.

### 🤖 AI Dungeon Master
- **Dynamic Narration**: AI generates immersive story descriptions
- **Contextual Responses**: Remembers campaign history and character actions
- **NPC Dialogue**: Generates unique dialogue for NPCs
- **Combat Descriptions**: Dramatic combat narration
- **Retry Logic**: Automatic retry with exponential backoff for API reliability
- **API Tools & Spells Support**: The AI DM can cast spells, call spell/ability tool actions, and manage character resources programmatically.

### 🪄 Spells & Abilities
- **Spellcasting**: Classes that cast spells (Mage, Cleric, Bard, Warlock, Paladin, Ranger, etc.) have cantrips and leveled spells, spell slots, and upcasting support.
- **Spellbook**: Characters can learn and prepare spells. Use `/spell learn` to add spells appropriate for your class and level.
- **Spell Slots**: Spell slots are tracked and used when casting. Recover slots via long rest or through DM control. Use `/spell slots` to view available spell slots.
- **Casting**: `/spell cast` supports cantrips (no slots), leveled spells with slot selection and upcasting, damage/healing/result summarization, and short description UI.
- **Class Abilities**: Abilities like Second Wind, Action Surge, Sneak Attack, and Divine Smite are available and tracked with use counts.

### 🌐 Web Dashboard
- **Game Management**: View and edit sessions, characters, quests, NPCs from a web browser
- **Data Editors**: Edit character classes, races, items, and spells
- **Real-time Sync**: Changes made in the web interface are immediately available in Discord
- **REST API**: Full API access for custom integrations (~76 endpoints)
- **Coming Soon**: Browser-based chat interface to play without Discord


## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Discord Bot Token
- Requesty.ai API Key (for AI features)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rpg-dm-bot.git
cd rpg-dm-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your tokens
```

4. Run the bot:
```bash
python run.py
```

5. Run the web dashboard (optional, separate terminal):
```bash
cd web && uvicorn api:app --reload --port 8000
# Open http://localhost:8000 in your browser
```

## 🌐 Web Dashboard

The web dashboard provides a browser-based interface for game management:

### Accessing the Dashboard
1. Start the API server: `cd web && uvicorn api:app --port 8000`
2. Open http://localhost:8000 in your browser

### Available Pages
- **Dashboard**: Overview of active sessions, characters, and recent activity
- **Sessions**: Create, view, and manage game sessions
- **Characters**: View and edit character details, stats, inventory
- **Quests**: Manage quest definitions and track progress
- **NPCs**: Create and edit NPCs, view relationships
- **Locations**: Build your world map with connected locations
- **Classes/Races**: Edit character class and race definitions with full CRUD operations
- **Skill Trees**: Browse and edit class skill trees and branches
- **Items/Spells**: Browse and search the item and spell databases with filtering

### REST API
The web dashboard is powered by a full REST API with ~80 endpoints. See `web/api.py` for the complete API reference. Key endpoints:
- `GET/POST /api/sessions` - Session management
- `GET/POST /api/characters` - Character CRUD
- `GET/POST /api/quests` - Quest management
- `GET/POST /api/npcs` - NPC management
- `GET/POST /api/locations` - World building
- `GET/PUT /api/gamedata/classes` - Class editor (full CRUD)
- `GET/PUT /api/gamedata/races` - Race editor (full CRUD)
- `GET/PUT /api/gamedata/skills/trees/{class}` - Skill tree editor
- `GET /api/gamedata/items` - Item database with filtering
- `GET /api/gamedata/spells` - Spell database with filtering

## 📚 Commands

### Character Commands (`/character`)
| Command | Description |
|---------|-------------|
| `/character create` | Create a new character |
| `/character sheet` | View your character sheet |
| `/character stats` | View detailed stats |
| `/character levelup` | Level up (if eligible) |
| `/character switch` | Switch active character |
| `/character list` | List all your characters |

### Combat Commands (`/combat`)
| Command | Description |
|---------|-------------|
| `/combat start` | Start combat encounter |
| `/combat attack` | Attack a target |
| `/combat defend` | Take defensive stance |
| `/combat spell` | Cast a spell |
| `/combat item` | Use an item |
| `/combat flee` | Attempt to flee |
| `/combat status` | View combat status |

### Spells (`/spell`)
| Command | Description |
|---------|-------------|
| `/spell cast` | Cast a spell from your known spells (opens a selection UI if unspecified) |
| `/spell list` | View all spells your character knows and their prepared state |
| `/spell learn` | Learn a new spell from your class spell list based on your level |
| `/spell info` | Get detailed spell info (damage, saving throw, components, upcasting) |
| `/spell slots` | View and manage your spell slots |


### Inventory Commands (`/inventory`)
| Command | Description |
|---------|-------------|
| `/inventory view` | View your inventory |
| `/inventory use` | Use an item |
| `/inventory equip` | Equip an item |
| `/inventory unequip` | Unequip an item |
| `/inventory drop` | Drop an item |
| `/inventory give` | Give item to player |

### Quest Commands (`/quest`)
| Command | Description |
|---------|-------------|
| `/quest list` | View available/active quests |
| `/quest info` | Get quest details |
| `/quest accept` | Accept a quest |
| `/quest complete` | Complete a quest objective |
| `/quest abandon` | Abandon a quest |

### DM Commands (`/dm`)
| Command | Description |
|---------|-------------|
| `/dm quest create` | Create a new quest plan |
| `/dm quest edit` | Edit existing quest |
| `/dm npc create` | Create an NPC |
| `/dm spawn` | Spawn enemies |
| `/dm reward` | Give rewards to players |
| `/dm narrate` | Add story narration |

### Session Commands (`/session`)
| Command | Description |
|---------|-------------|
| `/session create` | Create a campaign |
| `/session join` | Join a campaign |
| `/session start` | Start a session |
| `/session end` | End current session |
| `/session players` | View party members |
| `/game list` | Browse and manage available games using an interactive UI |

### Dice Commands (`/roll`)
| Command | Description |
|---------|-------------|
| `/roll dice` | Roll dice (e.g., 2d6+3) |
| `/roll attack` | Roll attack with bonuses |
| `/roll save` | Roll saving throw |
| `/roll skill` | Roll skill check |
| `/roll initiative` | Roll initiative |

### Utility Commands
| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/menu` | Interactive menu |
| `/ping` | Check bot latency |
| `/game start` | Start a game session (interviews for missing character info) |
| `/game stop` | End current game session |
| `/game status` | View current game state |
| `/game quick_start` | Create random character and start immediately |
| `/action` | Quick action buttons (Explore, Talk, Search, Rest, Continue) |

## 🎮 Getting Started Guide

### For Players

1. **Create a Character**: Use `/character create` to make your first character
2. **Join a Campaign**: Use `/session join` to join an existing campaign
3. **Interact with the World**: @mention the bot to talk to the DM
4. **Roll Dice**: Use `/roll dice 1d20` for any rolls needed
5. **Learn & Cast Spells**: If your class supports magic, use `/spell learn` to pick spells and `/spell cast` to cast them during play.

### For Dungeon Masters

1. **Create a Campaign**: Use `/session create` to start a new campaign
2. **Plan Quests**: Use `/dm quest create` to set up adventures
3. **Create NPCs**: Use `/dm npc create` to populate your world
4. **Run Sessions**: Use `/session start` when ready to play
5. **Manage Sessions**: Use `/game list` for a UI-driven game management experience including join, begin, pause, and reset conversation history.

## 🏗️ Project Structure

```
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

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

MIT License - feel free to use this for your own RPG adventures!

## 🙏 Acknowledgments

- Built with [discord.py](https://discordpy.readthedocs.io/)
- AI powered by [Requesty.ai](https://requesty.ai)
- Inspired by classic tabletop RPGs
- Originally transformed from [ussybot](https://github.com/kyleawayan/ussybot) by Claude Opus 4.5
