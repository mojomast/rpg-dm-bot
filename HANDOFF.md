# RPG Dungeon Master Bot - Handoff Document

**Date:** December 4, 2025  
**Project:** RPG Dungeon Master Discord Bot (adapted from ussybot)  
**Status:** Core implementation complete, tests passing (127 tests, some pre-existing failures)

> **🤖 AI-Generated Project**: This entire project was created by giving Claude Opus 4.5 a single prompt asking it to transform [ussybot](https://github.com/kyleawayan/ussybot) into an RPG Dungeon Master bot.

---

## Latest Changes (December 4, 2025 - Session 3)

### Bug Fixes:

1. **KeyError: 'character_id' Fix**
   - Players could join sessions without a character properly assigned, causing `KeyError: 'character_id'` when iterating through session participants
   - Added defensive checks (`if not p.get('character_id'): continue`) throughout the codebase to skip participants without assigned characters
   - **Files modified:**
     - `src/cogs/dm_chat.py` - `get_game_context()` party members loop and combat participants loop
     - `src/cogs/sessions.py` - `view_players()` and session status display
     - `src/cogs/game_master.py` - Multiple places: session management, join checks, party info building
     - `src/cogs/game_persistence.py` - Story summary, resume, and save commands

2. **Session Context Isolation (Game Mixing Bug)**
   - **Problem:** When multiple games were running in a guild, the bot was mixing up game contexts (e.g., "Big Bingo" context bleeding into "bobs bob" game)
   - **Root Cause:** `get_active_session_id()` returned the first active session for the guild, not the one the player was actually in
   - **Solution:** 
     - Added `get_user_active_session()` method to `database.py` that joins `sessions` with `session_participants` to find the user's specific session
     - Updated `get_active_session_id()` in `dm_chat.py` to take optional `user_id` parameter
     - Updated `get_game_context()` to use user's session instead of first active session
   - **Files modified:**
     - `src/database.py` - Added `get_user_active_session(guild_id, user_id)` method
     - `src/cogs/dm_chat.py` - Updated `get_active_session_id()`, `process_batched_messages()`, `process_dm_message()`, and `get_game_context()`

3. **LLM API Retry Logic**
   - **Problem:** 503 errors from LLM provider caused immediate failures
   - **Solution:** Added retry logic with exponential backoff (1s, 2s, 4s) for transient errors (503, 502, 429) and timeouts
   - **Files modified:**
     - `src/llm.py` - Updated `_api_call()` with `max_retries` parameter and retry loop

### Files Modified This Session:
- `src/database.py` - Added `get_user_active_session()` method
- `src/llm.py` - Added retry logic with exponential backoff
- `src/cogs/dm_chat.py` - Session isolation fixes, defensive character_id checks
- `src/cogs/sessions.py` - Defensive character_id checks  
- `src/cogs/game_master.py` - Defensive character_id checks
- `src/cogs/game_persistence.py` - Defensive character_id checks

---

## Previous Changes (December 3, 2025 - Session 2)

### Issues Fixed:

1. **Verbose Logging for API Requests**
   - Updated `src/llm.py` to log full API request/response details at INFO level
   - Logs now show: message contents (truncated at 500 chars), tool calls, responses
   - Updated `src/bot.py` to show DEBUG level logs in console for rpg.llm logger

2. **Game Start - Dungeon Master Silent Issue**
   - The DM wasn't doing anything when a game started because the `begin_game` method wasn't properly passing game context
   - Fixed `begin_game` in `src/cogs/game_master.py` to:
     - Use `build_game_start_prompt()` which includes game name, description, and full party info with backstories
     - Pass character backstories to the DM for quest crafting
     - Save game state to database for persistence
     - Log detailed info about game start

3. **Character Info in DM Prompts**
   - Updated `get_game_context()` in `src/cogs/dm_chat.py` to include:
     - Game name and description
     - All party members with HP and backstories
     - Current game state (scene, location, DM notes)
     - Session quest information

4. **Created Game Persistence Cog** (`src/cogs/game_persistence.py`)
   - New cog for managing game persistence between sessions
   - **Story Commands** (`/story`):
     - `/story log` - Add events to story log with type (combat, dialogue, discovery, quest, location, note)
     - `/story recap` - View recent story events
     - `/story summary` - AI-generated summary of adventure so far
   - **Game State Commands**:
     - `/resume` - Resume a paused/inactive game with full context restoration and AI recap
     - `/save` - Manually save current game state with optional notes
   - **Quest Commands** (`/quest`):
     - `/quest current` - View current active quest with objectives
     - `/quest list` - List all quests for the session
   - **Auto-logging**: Automatically logs combat events, discoveries, and location changes from DM responses

5. **Database Updates**
   - Added `save_game_state()` method for create-or-update game state
   - Updated `get_quests()` to accept optional `session_id` parameter

### Files Modified:
- `src/llm.py` - Verbose API logging
- `src/bot.py` - Console log level, added game_persistence cog
- `src/cogs/game_master.py` - Fixed begin_game to pass full context
- `src/cogs/dm_chat.py` - Enhanced get_game_context with party/session info
- `src/cogs/game_persistence.py` - **NEW** - Game/quest persistence cog
- `src/database.py` - Added save_game_state(), updated get_quests()

---

## Previous Bug Fixes (December 3, 2025 - Session 1)

### Fixed Issues:
1. **KeyError: 'char_class'** - The database stores character class in a column named `class`, but code inconsistently used `char['char_class']`. Fixed by adding a `_normalize_character()` helper method.

2. **TypeError: 'Command' object is not callable** - In `bot.py`, the `/menu` command tried to call `game_master.game_menu(interaction)` but `game_menu` is a discord command object. Fixed by calling callback properly.

3. **'str' object has no attribute 'get'** - In `game_master.py`, the `llm.chat()` method returns a string directly, but the code tried to call `.get('content', '')` on it. Fixed to handle the string return type.

4. **AttributeError: 'NoneType' object has no attribute 'get_member'** - Commands crashed in DMs. Fixed by adding `guild_only=True` to all command groups.

---

## Project Overview

A Discord bot that enables multiplayer RPG gaming with an AI Dungeon Master powered by Requesty.ai (OpenAI-compatible LLM). The bot manages characters, combat, inventory, quests, NPCs, sessions, and AI-driven storytelling through Discord slash commands and mentions.

**Repository Path:** `c:\Users\kyle\projects\rpg-dm-bot\`

---

## Architecture Summary

### Tech Stack
- **Discord Framework:** discord.py >= 2.3.0 (slash commands, cogs, intents)
- **Database:** aiosqlite (async SQLite3)
- **LLM:** Requesty.ai (OpenAI-compatible API at https://router.requesty.ai/v1)
- **HTTP Client:** aiohttp
- **Config:** python-dotenv for environment variables

### Key Design Patterns
- **Cog Architecture:** 10 modular cogs for different gameplay systems
- **Database Abstraction:** Single `Database` class with async methods for all persistence
- **LLM Integration:** Tool-based function calling (OpenAI format) with multi-round execution loops
- **Tool Executor:** `ToolExecutor` class processes LLM function calls and executes game mechanics

---

## Completed Implementation

### 1. Core Files
- **`run.py`** - Entry point, initializes bot with intents and runs event loop
- **`requirements.txt`** - Dependencies (discord.py, aiosqlite, python-dotenv, aiohttp)
- **`.env.example`** - Template for DISCORD_TOKEN, REQUESTY_API_KEY, REQUESTY_BASE_URL
- **`README.md`** - User-facing documentation with setup instructions

### 2. Core Modules

#### `src/database.py` (~1600 lines)
**Purpose:** All RPG data persistence via async SQLite  
**Tables:** 12+ tables covering all game systems
- `characters` - User characters with stats, HP, XP, level
- `inventory` - Items owned by characters
- `quests` - Quest definitions managed by DM
- `quest_progress` - Player progress on quests with objectives
- `npcs` - NPC definitions with personality/relationships
- `npc_relationships` - Track relationship points between players and NPCs
- `combat_encounters` - Active combat sessions
- `combat_participants` - Characters/enemies in combat with HP/initiative
- `sessions` - Game sessions with max_players support
- `session_participants` - Track which users are in which sessions
- `dice_rolls` - Historical record of all dice rolls
- `user_memories` - Context for DM conversation memory
- `conversation_history` - Chat history for DM continuity
- `story_log` - Adventure narrative timeline

**Key Methods:**
- Character: `create_character()`, `get_active_character()`, `update_character_hp()`, `add_experience()`, `level_up_character()`
- Inventory: `add_item()`, `remove_item()`, `get_inventory()`, `equip_item()`, `unequip_item()`
- Combat: `start_combat()`, `get_active_combat()` (accepts guild_id or channel_id), `add_participant()`, `deal_damage()`, `get_turn_order()`
- Quests: `create_quest()`, `get_active_quest()`, `add_quest_objective()`, `update_quest_progress()`
- NPCs: `create_npc()`, `get_npc()`, `add_relationship_change()`
- Sessions: `create_session()` (with max_players), `add_session_participant()`, `get_active_sessions()`
- Memory: `add_memory()`, `get_recent_memories()`, `add_conversation()`, `get_conversation_history()`

#### `src/llm.py` (~450 lines)
**Purpose:** LLM client for AI DM integration  
**Key Methods:**
- `dm_chat(messages, system_prompt)` - Get DM narration/response
- `dm_chat_with_tool_results(messages, tool_results, system_prompt)` - Continue chat after tool execution
- `chat_with_tools(messages, tools)` - Get response with function calls (returns dict with 'content' and 'tool_calls')
- `describe_scene(prompt)` - Generate descriptive narrative text

#### `src/prompts.py` (~500 lines)
**Purpose:** AI DM personality, behavior, and system prompts  
**Exports:** `Prompts` class with:
- `get_dm_system_prompt()` - Main DM personality prompt
- `DM_PERSONALITY` - Describes DM as creative, engaging, fair
- `DM_CAPABILITIES` - Lists available mechanics and tools
- `DM_NARRATION_STYLE` - Guides descriptive storytelling

#### `src/tool_schemas.py` (~1050 lines)
**Purpose:** OpenAI function calling schema definitions  
**Exports:** `ToolSchemas` class with:
- `get_all_tools()` - Returns full tool definitions
- `get_tool_names()` - Returns list of tool names

**Tool Categories:**
1. **Character Tools** (7 tools)
   - `get_character_info` - Retrieve full character sheet
   - `update_character_hp` - Modify HP (healing/damage)
   - `update_character_stat` - Adjust ability scores
   - `add_experience` - Grant XP
   - `level_up_character` - Advance level
   - `revive_character` - Bring character back from 0 HP
   - `get_all_characters` - List all characters in session

2. **Inventory Tools** (4 tools)
   - `give_item` - Add item to inventory
   - `remove_item` - Remove/consume item
   - `get_inventory` - List items owned
   - `equip_item` - Set as equipped

3. **Combat Tools** (6 tools)
   - `start_combat` - Initialize encounter
   - `add_combat_participant` - Add character/enemy to combat
   - `roll_initiative` - Determine turn order
   - `deal_damage` - Apply damage to participant
   - `get_active_combat` - Retrieve current combat state
   - `end_combat` - Conclude encounter

4. **Dice Tools** (3 tools)
   - `roll_dice` - Roll arbitrary dice (e.g., "2d6+3")
   - `roll_attack` - Roll with advantage/disadvantage
   - `roll_saving_throw` - Roll ability check with DC

5. **Quest Tools** (4 tools)
   - `create_quest` - Define new quest
   - `add_quest_objective` - Add milestone to quest
   - `update_quest_progress` - Mark objective complete
   - `get_active_quests` - List current quests

6. **NPC Tools** (3 tools)
   - `talk_to_npc` - Get NPC dialogue response
   - `give_to_npc` - Gift item to NPC
   - `get_npc_info` - Retrieve NPC details

7. **Session Tools** (3 tools)
   - `create_session` - Start new game session
   - `add_participant` - Invite player to session
   - `get_session_info` - Retrieve session details

8. **Memory Tools** (2 tools)
   - `remember` - Store contextual fact
   - `recall_memories` - Retrieve relevant context

#### `src/tools.py` (~400 lines)
**Purpose:** Execute LLM tool calls and implement game mechanics  
**Key Components:**
- `ToolExecutor` class with `execute_tool(tool_name, tool_args, context)` method
- `DiceRoller` class supporting:
  - Standard notation: "2d6", "4d20"
  - Modifiers: "1d20+5", "2d8-2"
  - Keep/drop mechanics: "4d6kh3" (keep highest 3)
  - Advantage/disadvantage: automatic advantage/disadvantage handling
- Tool implementations for all 32 tools calling appropriate database methods

#### `src/bot.py` (~300 lines)
**Purpose:** Main bot class and initialization  
**Features:**
- `RPGBot` class extending `commands.Bot`
- Loads 8 cogs (characters, combat, inventory, quests, npcs, sessions, dice, dm_chat)
- Initializes database, LLM client, tool executor, tool schemas
- Sets up Discord intents (message_content, members, guilds)
- Channel-level locks for concurrent safety
- Event handlers: on_ready, on_message

### 3. Cogs (8 slash command modules)

#### `src/cogs/characters.py`
**Commands:**
- `/character create` - Create new character with name, class, race
- `/character info` - Display character sheet (stats, HP, XP, level)
- `/character stats` - List all ability scores
- `/character inventory` - Show equipped items
- `/character level_up` - Advance to next level

#### `src/cogs/combat.py`
**Commands:**
- `/combat start` - Initialize combat encounter
- `/combat add` - Add character or enemy to combat
- `/combat initiative` - Roll and determine turn order
- `/combat attack` - Perform attack action (uses roll_attack)
- `/combat damage` - Apply damage to target
- `/combat status` - Show current HP/status of all combatants
- `/combat end` - Conclude combat, distribute XP/rewards

#### `src/cogs/inventory.py`
**Commands:**
- `/inventory view` - Display character's items
- `/inventory add` - Give item to character
- `/inventory remove` - Remove item from inventory
- `/inventory equip` - Set item as equipped
- `/inventory shop` - Browse and purchase items from game data

#### `src/cogs/quests.py`
**Commands:**
- `/quest available` - List all available quests
- `/quest active` - Show active quests with objectives
- `/quest info` - Detailed quest information
- `/quest create` - DM command to create quest (modal-based input)
- `/quest update` - Update quest objective completion status

#### `src/cogs/npcs.py`
**Commands:**
- `/npc create` - Create new NPC with personality
- `/npc talk` - Get NPC dialogue response
- `/npc info` - Display NPC details
- `/npc relationship` - Check relationship points with NPC

#### `src/cogs/sessions.py`
**Commands:**
- `/session create` - Start new game session
- `/session join` - Player joins session
- `/session info` - Show session details and participants
- `/session end` - End active session

#### `src/cogs/dice.py`
**Commands:**
- `/roll` - Roll arbitrary dice (e.g., "2d6+3")
- `/attack` - Roll attack with advantage/disadvantage
- `/save` - Roll saving throw against DC

#### `src/cogs/dm_chat.py`
**Purpose:** AI DM conversation with multi-round tool execution  
**Trigger:** User mentions bot or replies to bot message  
**Features:**
- Extracts conversation context from recent messages
- Passes to LLM with all available tools
- Executes tool calls returned by LLM
- Re-sends tool results to LLM for follow-up
- Continues until LLM returns only text (no more tool calls)
- Posts final narrative response to Discord
- `/action` command for quick action buttons (Explore, Talk to NPC, Search, Rest, Continue)

#### `src/cogs/game_master.py` (NEW)
**Purpose:** Game flow management and character interviews  
**Commands:**
- `/game start` - Start game session with character interview for incomplete characters
- `/game stop` - End current game session
- `/game status` - View current game state
- `/game quick_start` - Create random character and start immediately
**Features:**
- Interactive character interview via Discord modals
- DM private messaging for game initiator (meta information)
- Proactive game flow management
- Keeps the DM driving the narrative forward

### 4. Game Data Files (JSON)

#### `data/game_data/items.json`
**Categories:** weapons, armor, potions, accessories  
**Example Items:**
- Weapons: rusty_sword, iron_sword, steel_sword, magic_sword, legendary_blade
- Armor: leather_armor through plate_armor
- Potions: health_potion, mana_potion, strength_potion
- Accessories: ring_protection, amulet_wisdom, boots_speed
**Fields per item:** id, name, type, subtype, damage/defense, price, rarity, properties

#### `data/game_data/enemies.json`
**10 Enemy Types:** goblin, goblin_boss, skeleton, zombie, wolf, dire_wolf, orc, orc_warchief, bandit, bandit_captain, giant_spider, troll, young_dragon
**Fields per enemy:** hp, ac, stats (all 6 abilities), attacks, special_abilities, xp_reward, gold_reward, loot_table, challenge_rating
**Special Abilities:** undead_fortitude, aggressive, spider_climb, regeneration, breath_weapon, etc.

#### `data/game_data/classes.json`
**7 Classes:** warrior, mage, rogue, cleric, ranger, paladin, bard  
**Fields per class:** hit_die, primary_stat, saving_throws, starting_hp, hp_per_level, starting_equipment, abilities by level, spell_slots

#### `data/game_data/races.json`
**13+ Races:** human, elf (high/wood variants), dwarf (hill/mountain), halfling, dragonborn, tiefling, half_orc, gnome, half_elf  
**Fields per race:** stat_bonuses, speed, size, traits, languages
**Traits:** darkvision, keen_senses, fey_ancestry, trance, lucky, brave, etc.

---

## What Has NOT Been Implemented Yet

### 1. Testing Suite
- ✅ Unit tests written (104 passing)
- ✅ pytest-asyncio configured
- ✅ Test database fixtures with temp file
- Some integration tests need mock LLM responses

### 2. Error Handling & Validation
- Limited input validation in cogs
- No comprehensive error responses
- No rollback mechanisms for failed database operations
- No rate limiting for API calls

### 3. Logging & Monitoring
- Basic logging not configured
- No performance monitoring
- No audit trail for game actions
- No error tracking/alerting

### 4. Advanced Features
- No multi-round dialogue memory persistence
- No complex quest branching logic
- No dynamic NPC personality generation
- No spell/ability system implementation
- No complex movement/map system
- No voice channel integration

### 5. Documentation
- No API documentation for cogs
- No database schema diagrams
- No architecture decision records
- No troubleshooting guide

### 6. DevOps/Deployment
- No Docker setup
- No CI/CD pipeline
- No deployment scripts
- No configuration management

---

## Development Notes

### Known Limitations
1. **Concurrent Requests:** Channel-level locks prevent simultaneous commands in same channel
2. **LLM Context Window:** No sliding window implementation for long conversations
3. **Game State:** All game state in single SQLite database (no horizontal scaling)
4. **Tool Execution:** Linear execution only; no parallel tool calls

### Database Schema Notes
- All timestamps use ISO format strings
- All IDs are lowercase with underscores (snake_case)
- Combat initialized but participant status not fully tracked
- Quest objectives use list-based progress, not stages

### Important Code Locations
- Tool definitions: `src/tool_schemas.py` (~1050 lines)
- Tool execution: `src/tools.py` (~400 lines)
- LLM interaction: `src/llm.py` (~450 lines)
- Database methods: `src/database.py` (~1600 lines)
- DM chat loop: `src/cogs/dm_chat.py` handle_mention() method

---

## Next Steps for Fresh Context

### Priority 1: Testing Implementation
1. Set up pytest framework with fixtures for database, LLM, Discord mocks
2. Create unit tests for:
   - Database CRUD operations
   - Tool executor logic
   - Dice roller calculations
   - DM chat message parsing
3. Create integration tests for:
   - Full combat flow (start → roll initiative → attack → damage → end)
   - Character creation and leveling
   - Quest creation and progress tracking
   - Inventory management
4. Create mock LLM responses for deterministic testing
5. Set up test coverage reporting

### Priority 2: Error Handling
1. Add try-catch blocks in all cogs
2. Implement custom exception classes
3. Add user-friendly error messages
4. Add logging for debugging

### Priority 3: Validation
1. Add input validation for all commands
2. Validate game data files on startup
3. Add schema validation for database queries
4. Add permission checks (who can start combat, create quests, etc.)

### Questions for Next Context
1. Should tests focus on unit tests or integration tests first?
2. What's the desired test coverage percentage?
3. Should we add a test database or use in-memory SQLite?
4. Do we need performance benchmarks?

---

## File Manifest

```
c:\Users\kyle\projects\rpg-dm-bot\
├── run.py
├── requirements.txt
├── .env.example
├── README.md
├── HANDOFF.md (this file)
├── data/
│   ├── rpg.db (created at runtime)
│   └── game_data/
│       ├── items.json
│       ├── enemies.json
│       ├── classes.json
│       └── races.json
├── src/
│   ├── __init__.py
│   ├── bot.py
│   ├── database.py
│   ├── llm.py
│   ├── prompts.py
│   ├── tool_schemas.py
│   ├── tools.py
│   └── cogs/
│       ├── __init__.py
│       ├── characters.py
│       ├── combat.py
│       ├── inventory.py
│       ├── quests.py
│       ├── npcs.py
│       ├── sessions.py
│       ├── dice.py
│       ├── dm_chat.py
│       └── game_master.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_dice.py
│   ├── test_integration.py
│   └── test_tools.py
└── logs/ (created at runtime)
```

---

## Quick Start (For Reference)

```bash
cd c:\Users\kyle\projects\rpg-dm-bot
cp .env.example .env
# Edit .env with DISCORD_TOKEN and REQUESTY_API_KEY
pip install -r requirements.txt
python run.py
```

---

**End of Handoff Document**
