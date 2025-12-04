# 🎲 RPG Dungeon Master Bot

An AI-powered Discord bot that serves as a Dungeon Master for tabletop RPG games. Features persistent characters, combat mechanics, inventory management, interactive NPCs, multiplayer sessions, and AI-driven storytelling.

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

### 🤖 AI Dungeon Master
- **Dynamic Narration**: AI generates immersive story descriptions
- **Contextual Responses**: Remembers campaign history and character actions
- **NPC Dialogue**: Generates unique dialogue for NPCs
- **Combat Descriptions**: Dramatic combat narration

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

### For Dungeon Masters

1. **Create a Campaign**: Use `/session create` to start a new campaign
2. **Plan Quests**: Use `/dm quest create` to set up adventures
3. **Create NPCs**: Use `/dm npc create` to populate your world
4. **Run Sessions**: Use `/session start` when ready to play

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
