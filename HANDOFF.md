# RPG Dungeon Master Bot - Handoff Document

**Date:** December 6, 2025  
**Project:** RPG Dungeon Master Discord Bot  
**Status:** Phase 6 Complete - Enhanced UI (Mechanics Display, Discord Buttons, Web Campaign Creator)

> **🤖 AI-Generated Project**: This entire project was created by giving Claude Opus 4.5 a single prompt asking it to transform [ussybot](https://github.com/kyleawayan/ussybot) into an RPG Dungeon Master bot.

---

## Latest Changes (December 6, 2025 - Session 11)

### Session Context Isolation Fix (Critical Bug Fix)

**Problem:** When starting a new game, the LLM model retained context from previous games. For example, "bingo" references from an old game would appear in a completely different church escape adventure.

**Root Cause:** The `get_user_active_session()` function was ordering by `last_played DESC` instead of `s.id DESC`, causing older but recently-played sessions to take precedence over newly created sessions in the same channel.

#### Changes Made

**`src/database.py`:**
- Changed `get_user_active_session()` to order by `s.id DESC` instead of `s.last_played DESC NULLS LAST`
- This ensures the most recently CREATED session takes priority, not most recently played

**`src/cogs/dm_chat.py`:**
- Added `get_channel_session_id(channel_id)` helper function to retrieve stored session ID for a channel
- Modified `get_active_session_id()` to prioritize the channel's stored `session_id` before falling back to database lookup
- Updated `get_game_context()` to accept optional `session_id` parameter for explicit session targeting
- Added debug logging for session resolution

### LLM Model Configuration Fix

**Problem:** "Provider blocked by policy" error when using the LLM.

**Solution:** Changed `LLM_MODEL` from `openai/gpt-5-nano` (blocked) to `openai/gpt-4o-mini` in `.env` and `web/api.py` defaults.

### Campaign Finalization Database Schema Fixes

**Problem:** Web-created campaigns failed to save with database errors due to schema mismatches between code and actual database structure.

#### Issues Fixed in `web/api.py`:

| Issue | Fix |
|-------|-----|
| Missing `created_by` in locations INSERT | Added `created_by` column with value `'ai'` |
| Missing `updated_at` in locations INSERT | Added `updated_at` column |
| Wrong column `location_id` in npcs INSERT | Changed to `location` (TEXT type) |
| Missing `is_party_member` in npcs INSERT | Re-added column with value `0` |
| Missing `created_at` in quests INSERT | Added `created_at` column |
| Sessions created as 'setup' status | Changed to 'active' status so game starts immediately |

#### Database Schema Notes
The actual database schema differs from `src/database.py` in several ways:
- `locations` table has NOT NULL `created_by` column
- `npcs` table uses `location` (TEXT) instead of `location_id` (INTEGER FK)
- `npcs` table has `is_party_member` column

---

## Previous Changes (December 5, 2025 - Session 10)

### Mechanics Visibility System (New Feature)

Game mechanics (dice rolls, skill checks, etc.) are now displayed with styled formatting in Discord responses.

#### New File: `src/mechanics_tracker.py`
A thread-local tracker system that captures game mechanics during tool execution:

```python
# MechanicType enum includes:
# DICE_ROLL, SKILL_CHECK, SAVING_THROW, ATTACK_ROLL, DAMAGE_ROLL,
# ITEM_GAINED, ITEM_LOST, GOLD_CHANGE, XP_GAINED, LEVEL_UP,
# HP_CHANGE, STATUS_EFFECT, QUEST_UPDATE, LOCATION_CHANGE, NPC_INTERACTION

# Usage pattern:
tracker = new_tracker()  # Start fresh tracker
# ... execute tools ...
result = get_tracker()
mechanics_text = result.format_all()  # Styled output
```

#### Tracking Methods
| Method | What It Tracks |
|--------|----------------|
| `track_dice_roll()` | Dice rolls with results, modifiers, crits |
| `track_skill_check()` | Skill checks with DC, success/fail |
| `track_saving_throw()` | Save rolls with DC, success/fail |
| `track_attack()` | Attack rolls with hit/miss, damage |
| `track_damage()` | Damage dealt with type |
| `track_item_gained()` | Items acquired (name, quantity, rarity) |
| `track_item_lost()` | Items lost or used |
| `track_gold_change()` | Gold gained/spent |
| `track_xp_gained()` | Experience points earned |
| `track_level_up()` | Level advancement |
| `track_hp_change()` | HP damage/healing |
| `track_status_effect()` | Buffs/debuffs applied/removed |
| `track_quest_update()` | Quest progress |
| `track_location_change()` | Location transitions |
| `track_npc_interaction()` | NPC conversations |

#### Tools Updated
- `_roll_dice()` - Now tracks dice rolls
- `_roll_skill_check()` - Now tracks skill checks
- `_roll_save()` - Now tracks saving throws

### Discord Interactive Buttons (New Feature)

Bot responses now include clickable buttons for quick actions and information display.

#### New UI Components in `src/cogs/dm_chat.py`
| Component | Purpose |
|-----------|---------|
| `PlayerActionButton` | Execute quick player actions (option choices, look around, continue) |
| `InfoButton` | View game info (character sheet, quest, location, inventory, party) |
| `GameActionsView` | Combined view with action + info buttons |
| `QuickActionsView` | Simplified view for exploration |

#### Info Button Actions
- **📜 Character** - Shows character sheet embed (stats, HP, gold, XP)
- **📋 Quest** - Shows active quest details and progress
- **🗺️ Location** - Shows current location description and danger level
- **🎒 Inventory** - Shows inventory items and equipped gear
- **👥 Party** - Shows party composition including NPC companions

#### Integration
- `process_dm_message()` now returns tuple: `(response_text, mechanics_text)`
- `_delayed_process_queue()` creates styled embed with mechanics and attaches button views
- Buttons work with ephemeral responses for info (only requestor sees it)

### Web Campaign Creator (New Feature)

Full web-based campaign creation workflow with AI worldbuilding integration.

#### New API Endpoints (`web/api.py`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/campaign/generate-preview` | POST | Generate campaign preview without committing |
| `/api/campaign/finalize` | POST | Commit generated campaign to database |
| `/api/campaign/templates` | GET | Get predefined campaign templates |

#### CampaignSettings Model
```python
class CampaignSettings(BaseModel):
    guild_id: int
    dm_user_id: int
    name: str
    world_theme: str = "fantasy"  # fantasy, sci-fi, horror, modern, steampunk
    world_scale: str = "regional"  # local, regional, continental, world
    magic_level: str = "high"  # none, low, medium, high
    technology_level: str = "medieval"  # primitive to futuristic
    tone: str = "heroic"  # gritty, heroic, comedic, horror, mystery
    num_locations: int = 5
    num_npcs: int = 8
    num_factions: int = 3
    num_quest_hooks: int = 3
    world_description: Optional[str] = None
    key_events: Optional[str] = None
```

#### Frontend Campaign Creator (`web/frontend/`)
4-step wizard workflow:

1. **Settings** - Campaign name, Discord IDs, template selection, world settings
2. **Generate** - Loading animation with progress while generating
3. **Review** - Preview all generated content, edit/remove items
4. **Success** - Confirmation with stats and navigation

#### Template Presets
- Classic Fantasy (sword & sorcery)
- Dark Fantasy (gritty survival)
- Steampunk Adventure (Victorian intrigue)
- Cosmic Horror (forbidden knowledge)
- Space Opera (galactic adventures)
- Custom (build your own)

### CSS Styles Added (`web/frontend/styles.css`)
- Campaign wizard steps with active/completed states
- Template card selection grid
- Generation loading animation (orb + ring)
- Progress bar with gradient
- Preview cards with edit/remove actions
- Success screen with stats display
- Form row layouts
- Range slider styling

### TypeScript Updates (`web/frontend/src/main.ts`)
- Added campaign API functions: `generateCampaignPreview`, `finalizeCampaign`, `getCampaignTemplates`
- New page loader: `loadCampaignCreator()`
- Template selection with auto-fill
- Step navigation: `goToStep()`
- Preview population: `populatePreview()`
- Item editing/removal functions
- Campaign finalization with API call

---

## Previous Changes (December 4, 2025 - Session 9)

### Critical Bug Fixes - Bot Not Responding

#### Root Cause
The bot was failing with "The application did not respond" error when players interacted after game start. Two main issues:
1. **Missing database column** - `priority` column in `story_events` table didn't exist in databases created before schema update
2. **Session isolation failure** - Tools were using `get_active_session(guild_id)` which returns ANY active session in the guild, not the specific session the user is in

#### Database Migration Fix
- **Added `_run_migrations()` method to `database.py`** - Automatically adds missing columns to existing databases
- Migration adds `priority` column to `story_events` table if missing
- Migration adds `points_of_interest` column to `locations` table if missing
- Uses `PRAGMA table_info()` to check for existing columns before altering

#### Session Isolation Fix  
- **Fixed query error handling in `get_active_events()`** - Now uses `COALESCE(priority, 0)` and has fallback query
- **Fixed query error handling in `get_pending_events()`** - Same fix as above
- **Added `_get_session_for_context()` helper in `tools.py`** - Proper session lookup:
  1. First checks `context['session_id']` if passed
  2. Then checks `get_user_active_session(guild_id, user_id)` for user's session
  3. Finally falls back to `get_active_session(guild_id)` as last resort
- **Updated all tool functions** to use `_get_session_for_context()` instead of `get_active_session()`
- **Added `session_id` to context** in `dm_chat.py` when executing tools

#### Tools Updated for Session Isolation
| Tool | Change |
|------|--------|
| `_start_combat` | Now uses session from context, adds only party members from THAT session |
| `_create_quest` | Uses session from context |
| `_create_npc` | Uses session from context |
| `_get_party_info` | Uses session from context |
| `_add_story_entry` | Uses session from context |
| `_get_story_log` | Uses session from context |
| `_create_location` | Uses session from context |
| `_move_party_to_location` | Uses session from context |
| `_create_story_item` | Uses session from context |
| `_get_story_items` | Uses session from context |
| `_create_story_event` | Uses session from context |
| `_get_active_events` | Uses session from context |
| `_generate_npc` | Uses session from context |
| `_long_rest` | Uses session from context |
| `_end_combat_with_rewards` | Uses session from context |

#### DM Capabilities Prompt Update
- **Added Spell & Ability Tools section** - Documents `get_character_spells`, `cast_spell`, `get_character_abilities`, `use_ability`
- **Added Skill Check Tools section** - Documents `roll_skill_check`
- **Added Leveling & Progression section** - Explains automatic level ups and XP thresholds
- **Added 3 new critical rules** - Guidance on spell/ability usage and XP rewards

---

## Previous Changes (December 4, 2025 - Session 7)

### Frontend & API Fixes

#### API Endpoint Fixes
- **Fixed `/api/gamedata/items` response structure** - Now returns `{items: {weapons: [...], armor: [...], ...}}` instead of raw JSON, fixing item database display
- **Added `PUT /api/gamedata/classes`** - Bulk update endpoint for saving class edits from frontend
- **Added `PUT /api/gamedata/races`** - Bulk update endpoint for saving race edits from frontend  
- **Added `PUT /api/gamedata/skills/trees/{class_id}`** - Update skill tree for a specific class
- **Added `PUT /api/gamedata/skills`** - Bulk update all skills data

#### Frontend TypeScript Fixes
- **Fixed classes display** - Now handles `primary_stat` field (was expecting `primary_ability`)
- **Fixed abilities rendering** - Classes in data use abilities as object keyed by level, now properly flattens for display
- **Fixed class editing** - Edit form now properly populates and saves class data
- **Added skill tree editing** - New `editSkillBranch()` and `saveSkillBranch()` functions for modifying skill branches
- **Item database now loads correctly** - Frontend properly reads `data.items` from API response

#### Test Results
✅ **127 tests pass** - All existing tests continue to pass

---

## Previous Changes (December 4, 2025 - Session 6)

### Phase 4 Completion - Integration Verification & Bug Fixes

#### Database Bug Fixes
- **Removed duplicate `update_gold()` method** - Second definition was returning `True` instead of the new gold amount, breaking gold transactions
- **Added `update_combatant_initiative()` method** - Was being called by `_roll_initiative` tool but didn't exist
- **Fixed NPC relationship capping** - Initial relationships weren't being capped at ±100, now uses `max(-100, min(100, value))`

#### Tool Implementation Fixes
- **Fixed all `get_active_combat()` calls** - 7 calls in `tools.py` were passing `channel_id` as positional argument but method expects `channel_id=` keyword argument (first param is `guild_id`)
- **Fixed `_roll_initiative()`** - Had broken code `async with self.db.db_path as conn:` which tried to use a string as async context manager

#### Test Fixes  
- **Fixed `test_save_memory` assertion** - Was checking for "saved" but output says "Remembered"
- **Fixed test `get_active_combat` calls** - Same positional/keyword arg bug

#### Integration Test Results
✅ **127 tests pass** - Full coverage across database, dice, tools, and integration scenarios

---

## Project Architecture

### Directory Structure
```
c:\Users\kyle\projects\rpg-dm-bot\
├── run.py                 # Entry point
├── requirements.txt       # Python dependencies
├── pytest.ini             # Test configuration
├── HANDOFF.md             # This file
├── README.md              # User documentation
├── docs/
│   └── DATABASE_ARCHITECTURE.md  # Database diagrams & relationships
├── data/
│   ├── rpg.db             # SQLite database (runtime)
│   └── game_data/
│       ├── classes.json   # 7 character classes
│       ├── races.json     # 13+ playable races
│       ├── items.json     # ~100 items (weapons, armor, potions)
│       ├── enemies.json   # Enemy templates
│       ├── spells.json    # Spell definitions
│       ├── skills.json    # Skill trees per class
│       ├── npc_templates.json
│       └── starter_kits.json
├── src/
│   ├── __init__.py
│   ├── bot.py             # Main Discord bot class
│   ├── database.py        # All database operations (~3800 lines)
│   ├── llm.py             # LLM client with retry logic
│   ├── prompts.py         # AI DM system prompts
│   ├── tool_schemas.py    # OpenAI function definitions (~60 tools)
│   ├── tools.py           # Tool executor (~67 implementations)
│   └── cogs/
│       ├── characters.py  # Character commands
│       ├── combat.py      # Combat system
│       ├── inventory.py   # Inventory management
│       ├── quests.py      # Quest system
│       ├── npcs.py        # NPC interactions
│       ├── sessions.py    # Session/campaign management
│       ├── dice.py        # Dice rolling
│       ├── dm_chat.py     # AI DM conversation
│       ├── game_master.py # Game flow control
│       ├── game_persistence.py  # Save/load/story
│       ├── spells.py      # Spell system
│       └── skills.py      # Skill tree system
├── web/
│   ├── __init__.py
│   ├── api.py             # FastAPI REST API (~1400 lines, ~76 endpoints)
│   └── frontend/
│       ├── index.html     # Main HTML (~1200 lines)
│       ├── styles.css     # CSS (~1450 lines)
│       ├── package.json   # TypeScript config
│       ├── tsconfig.json
│       └── src/
│           └── main.ts    # TypeScript (~2200 lines)
├── tests/
│   ├── conftest.py        # Test fixtures
│   ├── test_database.py   # 48 database tests
│   ├── test_dice.py       # 27 dice tests
│   ├── test_integration.py # 10 integration tests
│   └── test_tools.py      # 42 tool tests
└── logs/                  # Runtime logs
```

### Tech Stack
| Component | Technology |
|-----------|------------|
| Discord | discord.py 2.3+ with slash commands |
| Database | SQLite via aiosqlite (async) |
| LLM | Requesty.ai (OpenAI-compatible) |
| Web API | FastAPI on port 8000 |
| Frontend | TypeScript compiled to JS |
| Testing | pytest with pytest-asyncio |

---

## Database Schema Summary

**27 Tables** organized into subsystems:

### Core Subsystem
- `sessions` - Game campaigns
- `session_participants` - Players in sessions
- `characters` - Player characters
- `game_state` - Current game state per session

### Character Subsystem
- `inventory` - Items owned
- `character_spells` - Known spells
- `character_abilities` - Class features
- `character_skills` - Skill tree unlocks
- `spell_slots` - Spell slot tracking
- `character_skill_points` - Available skill points
- `character_status_effects` - Buffs/debuffs

### Quest & NPC Subsystem
- `quests` - Quest definitions
- `quest_progress` - Per-character progress
- `npcs` - NPC definitions
- `npc_relationships` - Character-NPC reputation

### Combat Subsystem
- `combat_encounters` - Combat sessions
- `combat_participants` - Characters/enemies in combat

### World Subsystem
- `locations` - World locations
- `location_connections` - Bidirectional location links
- `story_items` - Key items/artifacts
- `story_events` - Plot events

### Memory Subsystem
- `user_memories` - AI context
- `conversation_history` - Chat history
- `story_log` - Narrative log
- `dice_rolls` - Roll history
- `session_snapshots` - Save states
- `character_interviews` - Character creation wizard

**See `docs/DATABASE_ARCHITECTURE.md` for full diagrams and relationships.**

---

## API Endpoints Overview (~80 endpoints)

### Core Endpoints (`/api/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET/POST | `/api/sessions` | Session CRUD |
| GET/POST | `/api/characters` | Character CRUD |
| GET/POST | `/api/quests` | Quest CRUD |
| GET/POST | `/api/npcs` | NPC CRUD |
| GET/POST | `/api/locations` | Location CRUD |
| GET/POST | `/api/items` | Story items CRUD |
| GET/POST | `/api/events` | Story events CRUD |
| GET/POST | `/api/combat` | Combat management |

### Character Detail Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/characters/{id}/spells` | Character's spells |
| GET | `/api/characters/{id}/abilities` | Character's abilities |
| GET | `/api/characters/{id}/skills` | Character's skills |
| GET | `/api/characters/{id}/status-effects` | Active status effects |
| POST | `/api/characters/{id}/rest/{type}` | Short/long rest |

### Relationship Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET/POST | `/api/locations/{id}/connections` | Location travel paths |
| GET | `/api/npcs/{id}/relationships` | NPC-character relationships |

### Game Data Endpoints (`/api/gamedata/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET/PUT | `/api/gamedata/classes` | Character classes (edit all) |
| GET/PATCH/POST/DELETE | `/api/gamedata/classes/{id}` | Single class CRUD |
| GET/PUT | `/api/gamedata/races` | Playable races (edit all) |
| GET/PATCH/POST/DELETE | `/api/gamedata/races/{id}` | Single race CRUD |
| GET/PUT | `/api/gamedata/skills` | All skill data |
| GET/PUT | `/api/gamedata/skills/trees/{class}` | Skill tree per class |
| GET/PATCH | `/api/gamedata/skills/{id}` | Single skill CRUD |
| GET | `/api/gamedata/items` | Item database (with filtering) |
| GET | `/api/gamedata/spells` | Spell definitions |
| GET | `/api/gamedata/enemies` | Enemy templates |

---

## What's Working

### ✅ Complete & Verified (127 tests pass)
- Character creation with interview wizard
- Session/campaign management with player isolation
- Combat system with initiative and turn tracking
- Inventory with equipment slots and starter kits
- Quest system with objectives and auto-reward distribution
- NPC system with relationships and location tracking
- Dice rolling with advantage/disadvantage and session history
- AI DM chat with tool calling and comprehensive context
- Spell system with slots and casting
- Skill trees with points and unlocks
- Game persistence with save/load
- Web API for all CRUD operations (~80 endpoints)
- Frontend dashboard and management pages
- Class/race editors with full edit/save functionality
- Skill tree editor with branch editing
- Item database browser with search and filtering
- Spell browser with filtering by school/level/class
- **Cross-system wiring** - All game systems properly integrated
- **All 67 tools** matched with schemas and working

### ⚠️ Frontend UI - Partial
- API client methods exist for all endpoints
- **Missing UI components**: Combat viewer, spell management panels, location connection map, status effects display

---

## Known Issues & Limitations

1. **No authentication** on web API (local use only)
2. **Single SQLite database** - no horizontal scaling
3. **No WebSocket** - frontend requires manual refresh
4. **No browser chat** - can only interact with DM via Discord
5. **Limited validation** - inputs not fully sanitized
6. **No rate limiting** - API can be overwhelmed

---
## Next Steps (Phase 5 - Browser Chat Feature)

### Goal
Enable users to interact with the AI Dungeon Master from within the browser instead of requiring Discord.

### Implementation Plan

#### 1. Backend: Add Chat API Endpoint
Create `/api/chat` endpoint in `web/api.py`:

```python
@app.post("/api/chat")
async def chat_with_dm(request: ChatRequest):
    """
    Send a message to the AI DM and get a response.
    
    Request body:
    - session_id: int - Active game session
    - user_id: int - User identifier (can be generated for web users)
    - message: str - User's message to the DM
    
    Response:
    - response: str - DM's narrative response
    - tool_results: list - Any game state changes made
    - updated_state: dict - Current game state after changes
    """
```

This endpoint should:
1. Load the session and character context (reuse `get_game_context()` from `dm_chat.py`)
2. Build the system prompt (reuse `build_dm_system_prompt()` from `prompts.py`)  
3. Call the LLM with tools enabled (reuse logic from `handle_mention()` in `dm_chat.py`)
4. Execute any tool calls (reuse `ToolExecutor` from `tools.py`)
5. Return the response and any state changes

#### 2. Backend: Add WebSocket Support (Optional but Recommended)
For real-time updates during tool execution:

```python
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: int):
    """
    WebSocket endpoint for streaming DM responses and real-time updates.
    """
```

#### 3. Frontend: Chat Interface Component
Add to `web/frontend/src/main.ts`:

```typescript
class ChatInterface {
    private sessionId: number;
    private chatHistory: ChatMessage[];
    private websocket?: WebSocket;
    
    async sendMessage(message: string): Promise<void>;
    renderMessage(message: ChatMessage): void;
    renderToolResult(result: ToolResult): void;
    updateGameState(state: GameState): void;
}
```

#### 4. Frontend: Chat UI
Add to `web/frontend/index.html`:
- Chat panel (collapsible sidebar or dedicated tab)
- Message input with send button
- Message history display with DM/player distinction
- Typing indicator during LLM response
- Tool execution feedback (dice rolls, damage, etc.)
- Quick action buttons (Attack, Defend, Cast Spell, etc.)

#### 5. User Identity for Web
Options:
- **Simple**: Generate UUID on first visit, store in localStorage
- **Better**: Add simple username registration (no password)
- **Full**: Discord OAuth integration (reuse Discord identity)

### Files to Create/Modify

| File | Changes |
|------|---------|
| `web/api.py` | Add `/api/chat` endpoint, optionally WebSocket `/ws/chat/{session_id}` |
| `src/chat_handler.py` | NEW: Extract DM chat logic from `dm_chat.py` into reusable class |
| `web/frontend/src/main.ts` | Add `ChatInterface` class and chat rendering |
| `web/frontend/index.html` | Add chat panel HTML structure |
| `web/frontend/styles.css` | Add chat panel styling |

### Key Code to Reuse

From `src/cogs/dm_chat.py`:
- `get_game_context()` - Gathers all game state for AI context
- `handle_mention()` - Main chat loop with tool execution

From `src/prompts.py`:
- `build_dm_system_prompt()` - Creates the AI DM personality and instructions
- `DM_CAPABILITIES` - Tool usage guidance for the AI

From `src/tools.py`:
- `ToolExecutor.execute_tool()` - Executes game state changes

From `src/llm.py`:
- `LLMClient.chat_completion_with_tools()` - LLM API call with function calling

### Architecture Decision: Stateless vs Stateful

**Recommended: Stateless HTTP**
- Each POST to `/api/chat` is independent
- Session context loaded from database each request
- Simpler to implement, works with existing database layer
- Frontend stores chat history display locally

**Alternative: WebSocket (Stateful)**
- Persistent connection per session
- Better for streaming responses
- More complex server-side state management
- Consider for Phase 6 if needed

---

## Environment Setup

```bash
# Clone and setup
cd c:\Users\kyle\projects\rpg-dm-bot
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with:
# - DISCORD_TOKEN=your_bot_token
# - REQUESTY_API_KEY=your_api_key
# - REQUESTY_BASE_URL=https://router.requesty.ai/v1

# Run tests
pytest tests/ -v

# Run bot
python run.py

# Run API (separate terminal)
cd web && uvicorn api:app --reload --port 8000
```

---

## Important Code Locations

| Purpose | File | Key Functions |
|---------|------|---------------|
| Database schema | `src/database.py` | Lines 20-550 (CREATE TABLE statements) |
| Database methods | `src/database.py` | Lines 550-3800 (~160 async methods) |
| API endpoints | `web/api.py` | Entire file (~80 endpoints) |
| Frontend TypeScript | `web/frontend/src/main.ts` | API object, page handlers |
| Tool definitions | `src/tool_schemas.py` | `TOOLS_SCHEMA` list (~60 tools) |
| Tool implementations | `src/tools.py` | `execute_tool()` and `_*` methods |
| DM chat loop | `src/cogs/dm_chat.py` | `handle_mention()`, `get_game_context()` |
| AI prompts | `src/prompts.py` | `build_dm_system_prompt()`, `DM_CAPABILITIES` |
| LLM client | `src/llm.py` | `chat_completion_with_tools()` |

---

## File Changes This Session (Session 8)

| File | Changes |
|------|---------|
| `src/database.py` | Added `_run_migrations()` method for schema updates, fixed `get_active_events()` and `get_pending_events()` with error handling |
| `src/tools.py` | Added `_get_session_for_context()` helper, updated 15+ tool functions to use proper session isolation |
| `src/cogs/dm_chat.py` | Added `session_id` to tool execution context in both `process_batched_messages()` and `process_dm_message()` |
| `src/prompts.py` | Added Spell & Ability Tools, Skill Check Tools, and Leveling sections to DM_CAPABILITIES |
| `HANDOFF.md` | Updated with Session 8 changes |
| `docs/DATABASE_ARCHITECTURE.md` | Updated with session isolation notes |

## File Changes Previous Session (Session 7)

| File | Changes |
|------|---------|
| `web/api.py` | Fixed `/api/gamedata/items` response structure, added PUT endpoints for classes/races/skills |
| `web/frontend/src/main.ts` | Fixed class display (primary_stat), fixed abilities rendering, added skill tree editing |
| `README.md` | Updated web dashboard section with new endpoints |
| `HANDOFF.md` | Updated with Session 7 changes |

## File Changes Session 6

| File | Changes |
|------|---------|
| `src/database.py` | Removed duplicate `update_gold()`, added `update_combatant_initiative()`, fixed NPC relationship capping |
| `src/tools.py` | Fixed 7 `get_active_combat()` calls to use `channel_id=` keyword, fixed `_roll_initiative()` broken async code |
| `tests/test_tools.py` | Fixed `test_save_memory` assertion, fixed `get_active_combat` test calls |

---

## Questions Resolved This Session

1. ✅ Bot not responding after game start - **Fixed missing `priority` column with database migration**
2. ✅ Characters from other sessions appearing - **Fixed session isolation with `_get_session_for_context()`**
3. ✅ Tools not documented for spells/skills - **Added to DM_CAPABILITIES prompt**

## Questions for Next Session

1. Should the browser chat use HTTP POST or WebSocket?
2. How should web users be identified (UUID, username, Discord OAuth)?
3. Should chat history be persisted to database or just frontend?
4. Do we need streaming responses for better UX?

---

**End of Handoff Document**
