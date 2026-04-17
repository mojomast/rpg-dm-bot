# 🎲 RPG Dungeon Master Bot

An AI-powered Discord bot that serves as a Dungeon Master for tabletop RPG games. Features persistent characters, combat mechanics, inventory management, interactive NPCs, multiplayer sessions, AI-driven storytelling, and a web dashboard for game management.

> **🤖 AI-Generated Project**: This entire project was created by giving Claude Opus 4.5 a single prompt asking it to transform [ussybot](https://github.com/kyleawayan/ussybot) into an RPG Dungeon Master bot. The AI designed the architecture, implemented all features, wrote tests, and created documentation autonomously.

## Current State

The repo already has substantial working systems for Discord play, browser chat, persistence, combat, quests, NPCs, and dashboard administration. It does not yet have one fully unified campaign architecture across Discord, browser, DB, tools, and worldbuilding content.

Implementation planning and remaining gap details live in:

- `WORLDBUILDING_AND_CAMPAIGN_GAP_SPEC.md`

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
- **Defend & Item Actions**: Defend now applies a real temporary combat bonus and combat item use supports simple consumables

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
- **Branching Paths**: Some branching and generative quest behavior exists, but canonical branching quest-state modeling is still in progress

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
- **Theme-Aware Generation**: Campaign preview/generation supports multiple themes, but first-class runtime content-pack switching is still planned work

### 🎲 Dice Rolling
- **Standard Dice**: Roll any dice (d4, d6, d8, d10, d12, d20, d100)
- **Modifiers**: Add bonuses from stats or equipment
- **Advantage/Disadvantage**: Roll with advantage or disadvantage
- **Interactive Rolls**: Buttons for quick re-rolls

### 👥 Multiplayer Sessions
- **Campaign Management**: Create and join campaigns
- **Session Tracking**: Track active sessions and participants
- **Party System**: Form adventuring parties
- **Shared Progress**: Players can share one session, though the canonical campaign lifecycle is still being consolidated
- **Session Isolation**: Multiple games can run simultaneously without context bleed - the AI DM correctly tracks which characters belong to which session
- **Guild-Scoped Session Commands**: Session/game resume, join, pause, end, and quest actions now reject session IDs from other servers
- **Interactive Session Menu**: Use `/game list` to browse, select, join, and manage sessions using a comprehensive session UI with per-session controls.

### 🤖 AI Dungeon Master
- **Dynamic Narration**: AI generates immersive story descriptions
- **Contextual Responses**: Remembers campaign history and character actions
- **NPC Dialogue**: Generates unique dialogue for NPCs
- **Combat Descriptions**: Dramatic combat narration
- **Retry Logic**: Automatic retry with exponential backoff for API reliability
- **API Tools & Spells Support**: The AI DM can cast spells, call spell/ability tool actions, and manage character resources programmatically.
- **Slash Command Hardening**: Guild-only DM skill checks, safer session resolution, and normalized class handling for skill trees

### 🪄 Spells & Abilities
- **Spellcasting**: Classes that cast spells (Mage, Cleric, Bard, Warlock, Paladin, Ranger, etc.) have cantrips and leveled spells, spell slots, and upcasting support.
- **Spellbook**: Characters can learn and prepare spells. Use `/spell learn` to add spells appropriate for your class and level.
- **Spell Slots**: Spell slots are tracked and used when casting. Recover slots via long rest or through DM control. Use `/spell slots` to view available spell slots.
- **Casting**: `/spell cast` supports cantrips (no slots), leveled spells with slot selection and upcasting, damage/healing/result summarization, and short description UI.
- **Class Abilities**: Abilities like Second Wind, Action Surge, Sneak Attack, and Divine Smite are available and tracked with use counts.

### 🌐 Web Dashboard
- **Game Management**: View and edit sessions, characters, quests, NPCs from a web browser
- **Data Editors**: Edit character classes, races, items, and spells
- **Shared Data Store**: Changes made in the web interface are available to Discord-backed play through the same database
- **REST API**: Full API access for custom integrations (~76 endpoints)
- **Browser Chat**: Talk to the AI Dungeon Master from the web UI with persisted history and live session panels
- **Play Panels**: Browser chat includes combat viewer, spell management, location connections, and status effects panels
- **Basic Web Hardening**: Browser chat uses server-issued identities and per-IP rate limiting on `/api/chat`

## Content Packs

The long-term content direction is theme-separated content packs under `data/game_data/packs/<theme>/<pack>/`.

Planned pack structure:

- `archetypes.json`
- `origins.json`
- `items.json`
- `powers.json`
- `skills.json`
- `enemies.json`
- `npc_templates.json`
- `starter_kits.json`
- `world_templates.json`
- `factions.json`

Runtime target:

- sessions persist `world_theme` and `content_pack_id`
- v1 runtime target is `fantasy_core`
- legacy flat files under `data/game_data/` are expected to migrate into `fantasy_core`


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
- **Browser Chat**: Play through the web UI with DM responses, tool feedback, and live play-state panels
- **Characters**: View and edit character details, stats, inventory
- **Quests**: Manage quest definitions and track progress
- **NPCs**: Create and edit NPCs, view relationships
- **Locations**: Build your world map with connected locations
- **Classes/Races**: Edit character class and race definitions with full CRUD operations
- **Skill Trees**: Browse and edit class skill trees and branches
- **Items/Spells**: Browse and search the item and spell databases with filtering

Current limitation:

- Browser play exists, but some dashboard management/editor flows are still incomplete or placeholder-backed.

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
- `POST /api/chat/identity` - Issue a server-generated browser chat identity
- `POST /api/chat` - Send a browser chat message to the DM

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
| `/inventory shop` | Open the general store with owner-locked interaction controls |

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

## Recent Hardening

- `/skills` now works with normalized character rows that use `char_class` and with the current `skills.json` branch structure.
- `/check` is guild-only, matching the rest of the DM session flow.
- Session lookup paths in DM chat, game management, session commands, and resume flow now verify that the session belongs to the current guild.
- Character creation shop flows and inventory/shop views reject clicks from other users, preventing accidental or malicious cross-user purchases.
- Starter-kit shopping no longer subtracts gold twice at checkout.

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

### Canonical Campaign Flow

1. The DM creates a campaign with `/session create`.
2. Each player joins with `/session join`.
3. Each player selects or creates one character for that campaign.
4. The DM launches the campaign in one play channel.
5. Players use the DM chat and the normal gameplay commands against that shared session state.
6. The DM can pause and later resume the campaign without resetting progress.
7. Players can continue the same campaign from browser chat by selecting the same session and character.

### For Players

1. Create or select your character.
2. Join the campaign shared by the DM.
3. Wait for the DM to launch the campaign.
4. Play in the campaign's channel or continue through browser chat with the same character.
5. Use quest, inventory, spell, and combat commands as the story progresses.

### For Dungeon Masters

1. Create the campaign.
2. Wait for players to join and bind characters.
3. Launch the campaign in one play channel.
4. Use the session status/lobby tools to track readiness, active quest, and continuity.
5. Pause and resume the campaign as needed until the final quest is complete.

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
