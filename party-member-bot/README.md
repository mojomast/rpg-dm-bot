# 🎭 Party Member Bot

A Discord bot that acts as a player character in RPG sessions. Designed for automated testing of the RPG Dungeon Master Bot, but can also be used as a companion player in your games.

## ✨ Features

### 🤖 Automated Party Member
- Configurable characters that participate in RPG sessions
- Responds to DM bot prompts automatically
- Personality-based response generation

### 📱 DM-Based Configuration
- All configuration done via Discord DMs to the owner
- Secure - only the owner can control the bot
- Character creation interview process

### 🎮 Session Participation
- Join/leave game channels
- Auto-play mode for fully automated participation
- Manual control via owner commands

### 🧪 Testing Automation
- Run multiple instances with different characters
- Simulate player parties for testing
- Each bot maintains its own character data

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Discord Bot Token (one per party member bot)
- RPG DM Bot already running

### Installation

1. Copy this folder to create a new project:
```bash
cp -r party-member-bot my-party-member
cd my-party-member
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

5. Edit `.env` with your settings:
```env
DISCORD_TOKEN=your_bot_token_here
OWNER_ID=your_discord_user_id
DM_BOT_ID=the_dm_bot_user_id
```

6. Run the bot:
```bash
python run.py
```

## 📋 Commands

All commands are used via DM with the bot owner. Use the `!pm` prefix.

### Character Management
| Command | Description |
|---------|-------------|
| `!pm create` | Start the character creation interview |
| `!pm character` | View current character details |
| `!pm edit <field> <value>` | Edit character (name, backstory, personality, play_style) |
| `!pm register` | Get instructions to register with the DM bot |

### Session Management
| Command | Description |
|---------|-------------|
| `!pm join #channel` | Join a game session in a channel |
| `!pm leave #channel` | Leave a game session |
| `!pm autoplay on/off [#channel]` | Toggle auto-play mode |

### Communication
| Command | Description |
|---------|-------------|
| `!pm say #channel <message>` | Speak as your character |
| `!pm do #channel <action>` | Perform an action (sends `*Name action*`) |

### Information
| Command | Description |
|---------|-------------|
| `!pm status` | View bot and character status |
| `!pm help` | Show all commands |

## 🎭 Character Creation Interview

When you run `!pm create`, the bot will walk you through:

1. **Server Selection** - Choose which server this character will play in
2. **Race Selection** - Human, Elf, Dwarf, Halfling, Orc, Tiefling, Dragonborn, Gnome
3. **Class Selection** - Warrior, Mage, Rogue, Cleric, Ranger, Bard, Paladin, Warlock
4. **Stat Method** - Roll 4d6 drop lowest, or use standard array
5. **Character Name** - What to call your character
6. **Backstory** - Optional character history
7. **Personality** - How the bot should roleplay
8. **Play Style** - Aggressive, defensive, balanced, cautious, or reckless

## 🧪 Running Multiple Bots

To test with a full party, run multiple instances:

1. Create separate folders for each bot:
```bash
cp -r party-member-bot party-member-warrior
cp -r party-member-bot party-member-mage
cp -r party-member-bot party-member-cleric
```

2. Create separate Discord bot applications for each

3. Configure each with its own `.env` file

4. Run each in a separate terminal:
```bash
# Terminal 1
cd party-member-warrior && python run.py

# Terminal 2
cd party-member-mage && python run.py

# Terminal 3
cd party-member-cleric && python run.py
```

5. Create characters via DM for each bot

6. Have all bots join the same channel and enable auto-play

## 🔧 Play Styles

The `play_style` setting affects how the bot responds:

| Style | Behavior |
|-------|----------|
| **aggressive** | Attacks first, charges into battle |
| **defensive** | Protects allies, avoids risks |
| **balanced** | Adapts to situations |
| **cautious** | Careful, observant, avoids danger |
| **reckless** | Acts without thinking |

## 📁 Project Structure

```
party-member-bot/
├── run.py              # Entry point
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment config
├── .gitignore          # Git ignore rules
├── README.md           # This file
├── data/               # Character data storage
│   └── character.json  # Saved character (created on first save)
├── logs/               # Log files
└── src/
    ├── __init__.py
    ├── bot.py          # Main bot class
    ├── config.py       # Configuration management
    └── cogs/
        ├── __init__.py
        ├── interview.py      # Character creation interview
        ├── gameplay.py       # Session participation
        └── owner_commands.py # Owner control commands
```

## 🔒 Security

- Only the configured `OWNER_ID` can control the bot via DMs
- Bot tokens should never be shared
- Character data is stored locally in `data/character.json`

## 🐛 Troubleshooting

### Bot doesn't respond to DMs
- Make sure your Discord user ID is correctly set in `OWNER_ID`
- The bot must be running before you can DM it

### Can't join channels
- Ensure the bot is in the server
- Check that the bot has permission to send messages in the channel

### Auto-play not working
- Confirm the DM bot ID is correctly set in `DM_BOT_ID`
- Make sure auto-play is enabled: `!pm autoplay on #channel`
- The bot must be joined to the channel: `!pm join #channel`

## 📜 License

MIT License - Feel free to modify and use for your own testing!
