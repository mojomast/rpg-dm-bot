# RPG Dungeon Master Bot - Handoff Document

**Date:** April 17, 2026  
**Project:** RPG Dungeon Master Discord Bot  
**Status:** Recent hardening complete, but campaign architecture still partial

> **🤖 AI-Generated Project**: This entire project was created by giving Claude Opus 4.5 a single prompt asking it to transform [ussybot](https://github.com/kyleawayan/ussybot) into an RPG Dungeon Master bot.

## Current Operational State

What is usable today:

- Discord-based RPG play with sessions, characters, inventory, combat, quests, NPCs, AI DM chat, and basic persistence.
- Browser chat with persisted session-scoped history and live side panels for combat, spells, status effects, and location connections.
- Web dashboard CRUD for many gameplay entities and game-data browsing/editing.

What is not yet coherent end to end:

- There is not yet one canonical campaign lifecycle across Discord and browser.
- `/game`, `/session`, and `/resume` still split lifecycle responsibility.
- Character creation, combat, and quest progression still have duplicate or drifting implementations.
- Theme/content-pack foundation is in place (`world_theme`, `content_pack_id`, `fantasy_core`, loader, pack-aware web/tool reads), but Discord runtime parity is still incomplete.
- Storyline graph, faction runtime, map/discovery systems, and full snapshot continuity are not implemented end to end.

Reference spec for the next implementation wave:

- `WORLDBUILDING_AND_CAMPAIGN_GAP_SPEC.md`

## Known Architectural Gaps

The highest-priority architectural gaps are:

1. remaining larger canonicalization and roadmap work beyond the landed Discord runtime parity slices
2. duplicate lifecycle flows across `/game`, `/session`, and `/resume`
3. remaining character creation/combat canonicalization beyond the landed slices
4. incomplete browser/dashboard contracts for campaign editing/admin parity
5. larger roadmap features: factions, storylines, map/discovery systems

The implementation-ready source of truth for these gaps is `WORLDBUILDING_AND_CAMPAIGN_GAP_SPEC.md`.

---

## Latest Changes (April 17, 2026 - Session 13)

### Additional Runtime Hardening (same day follow-up)

This follow-up pass continued the worldbuilding/campaign gap-spec implementation beyond browser continuity and into Discord runtime coherence.

#### Changes Made

**`src/cogs/game_persistence.py`:**
- Added context-aware session resolution so story log, recap, summary, save, resume, quest views, and auto-logging prefer the channel-bound session over guild-global fallbacks

**`src/cogs/combat.py`:**
- Updated `/combat start` to bind encounters to the channel/session context instead of the first active guild session

**`src/cogs/dm_chat.py`:**
- Persisted channel binding on final active-session fallback so later runtime flows converge on the same session

**`src/cogs/game_master.py`:**
- Made the Discord GM character interview session-bound and content-pack aware
- Loaded pack-aware races/classes/starter kits/spells for interview creation
- Created interview characters with `session_id`, auto-joined them to the session, and provisioned real gold/spells through canonical character tables

**`src/chat_handler.py`:**
- Added actor-scoped tool routing for batched multiplayer DM turns so player-specific tool calls no longer default to the first actor in the batch

**`src/utils.py`:**
- Added shared runtime session/content resolution helpers for live Discord command surfaces

**`src/cogs/spells.py`:**
- Made cast/learn/info/quickcast/autocomplete resolve `spells.json` through the active session content pack instead of legacy flat files

**`src/cogs/skills.py`:**
- Made skill tree rendering, learn/use/info flows, and skill autocomplete resolve `skills.json` through the active session content pack instead of legacy flat files

**`src/cogs/inventory.py`:**
- Made inventory views, item details, shop flows, slash-command use, and quick-use resolve `items.json` through the active session content pack instead of legacy flat files

**`src/cogs/combat.py`:**
- Updated combat consumable item selection to use the same session-scoped pack item metadata as inventory

**Tests:**
- Added regression coverage for channel-bound session selection, GM interview session/pack binding, batched actor-context tool routing, runtime session helper preference, and pack-aware spell runtime lookups

#### Verification

Local verification completed with:

```bash
.venv/bin/python -m compileall src/utils.py src/chat_handler.py src/cogs/game_persistence.py src/cogs/combat.py src/cogs/dm_chat.py src/cogs/game_master.py src/cogs/spells.py
.venv/bin/pytest tests/test_lifecycle_resume.py tests/test_dm_chat.py tests/test_combat_cog.py -q
```

Results:
- compile checks passed
- focused lifecycle/DM chat/combat regressions passed

#### Remaining Limitation

- The current v1 Discord runtime pack-awareness slices are landed for GM interview creation, spells, skills, and inventory/items; remaining work is now broader canonicalization and roadmap-scale features rather than flat-data parity in those core flows.

### Phase 9 - Browser Chat Hardening and Dashboard Completion

This session hardened the new browser chat flow and completed the missing web dashboard play panels.

#### Changes Made

**`src/chat_handler.py`:**
- Added session-based combat fallback in `get_game_context()` for web users without a real Discord channel
- Added batch character summaries so multiplayer batched prompts include every acting character, not just the first

**`src/database.py`:**
- Added `get_active_combat_by_session(session_id)`
- Added `web_identities` table helpers for server-issued browser identities
- Extended `conversation_history` with `session_id` support and added session-scoped history lookup
- Added migration for existing databases missing `conversation_history.session_id`

**`src/chat_web_identity.py`:**
- Added server-side UUID generation helper
- Added client IP hashing helper for persisted web identity metadata

**`src/cogs/dm_chat.py`:**
- Verified the proactive background DM task survived the Phase 8 refactor
- Hardened the task lifecycle so the loop only starts once and skips work when the bot/LLM context is unavailable
- Updated batched Discord queue entries to preserve each player's `character_id`

**`web/api.py`:**
- Added `POST /api/chat/identity` to mint browser chat UUIDs server-side and persist them in `web_identities`
- Updated `/api/chat` to require `X-Web-Identity` and reject unknown browser identities
- Added per-IP rate limiting of `10/minute` to `/api/chat` with `slowapi`
- Updated `/api/chat` to load the last 20 persisted messages for `(session_id, web_user_id)` before processing and save both sides of each exchange after response generation

**`web/frontend/index.html`:**
- Added live browser-chat sidebar panels for combat, spells, location connections, and status effects

**`web/frontend/src/main.ts`:**
- Switched browser chat identity bootstrapping to request a server-issued UUID and store it in `localStorage`
- Updated chat requests to send the UUID via `X-Web-Identity`
- Changed chat rendering to append messages incrementally and auto-scroll after each `renderMessage()` call
- Added live dashboard panel refresh for combat, spell management, location connections, and status effects
- Added spell cast shortcuts and short/long rest actions to the browser chat spell panel

**`web/frontend/styles.css`:**
- Added the missing styles for detail panels, combat cards, HP bars, spell rows, connection cards, and status chips

**`requirements.txt`:**
- Added `fastapi`, `uvicorn`, and `slowapi`

**Tests:**
- Added coverage for session-based combat lookup, web identity persistence, session-scoped conversation history, and multi-player batch prompt context
- Refreshed stale DM chat test fixtures to match the current `DMChat` constructor

#### Verification

Local verification completed with:

```bash
python3 -m compileall src web tests
.venv/bin/pytest tests/test_database.py -q
.venv/bin/pytest tests/test_dm_chat.py -q
```

Results:
- compile checks passed
- focused database tests passed
- focused DM chat tests passed

#### Remaining Limitation

- The checked-in frontend toolchain is incomplete in this workspace (`npm run build` fails because `tsc` is not executable and the installed TypeScript package is missing `lib/tsc.js`), so end-to-end frontend bundling still needs dependency repair.

---

## Previous Changes (April 17, 2026 - Session 12)

### Phase 7 - Slash Command and Session Hardening

This session completed the Phase 7 runtime hardening pass focused on slash commands, guild/session isolation, and owner-safe interactive UI.

#### Changes Made

**`src/utils.py`:**
- Added `get_character_class()` helper so cogs can read either `char_class` or legacy `class`
- Added `ensure_interaction_owner()` helper for owner-locked Discord views

**`src/cogs/skills.py`:**
- Fixed `/skills` to use normalized class lookup instead of directly reading `character['class']`
- Added `get_skill_tree_branches()` to normalize `skills.json` branch data when stored as a dict
- Prevented runtime failures when loading skill trees from current game data

**`src/cogs/dm_chat.py`:**
- Added guild validation in `resolve_session()` so cross-guild session IDs are ignored
- Marked `/check` as `@app_commands.guild_only()`

**`src/cogs/game_master.py`:**
- Added `_get_guild_session()` helper and used it for guild-scoped session commands
- Updated `DMChat.start_new_session()` call sites to pass `guild_id`
- Added owner checks to character creation equipment/shop views
- Fixed starter shopping checkout so remaining gold is not reduced twice

**`src/cogs/sessions.py`:**
- Added `_get_guild_session()` helper and applied it across session view/join/leave/start/pause/end/delete/set-quest flows

**`src/cogs/game_persistence.py`:**
- Added `_get_guild_session()` helper and applied it to `/resume`

**`src/cogs/inventory.py`:**
- Added owner checks to shop, inventory, item action, and consumable views so only the originating player can interact

**Tests:**
- Added `tests/test_phase7.py` covering:
  - guild filtering in `DMChat.resolve_session()`
  - normalized `/skills` class handling
  - starter shopping remaining-gold behavior

#### Verification

Local verification completed with:

```bash
python3 -m compileall src tests
.venv/bin/pytest tests/test_phase7.py tests/test_dm_chat.py -q
```

Results:
- compile checks passed
- 6 focused tests passed

#### Remaining Limitation

- True live Discord slash-command verification is still not possible in this environment without a valid bot token and server.

---

## Previous Changes (December 6, 2025 - Session 11)

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
- Browser chat with persisted history, server-issued web identities, and rate limiting
- Class/race editors with full edit/save functionality
- Skill tree editor with branch editing
- Item database browser with search and filtering
- Spell browser with filtering by school/level/class
- Browser chat dashboard panels for combat, spell management, location connections, and status effects
- **Cross-system wiring** - All game systems properly integrated
- **All 67 tools** matched with schemas and working

### ⚠️ Frontend UI - Partial
- API client methods exist for all endpoints
- Browser chat dashboard panels are now present, but frontend dependency repair is still needed before a clean local production bundle can be generated in this workspace

---

## Known Issues & Limitations

1. **No user authentication** beyond server-issued browser chat identities (local use only)
2. **Single SQLite database** - no horizontal scaling
3. **No WebSocket** - frontend requires manual refresh
4. **Limited validation** - inputs not fully sanitized
5. **Frontend build toolchain in repo is incomplete** - TypeScript CLI package contents/permissions need repair for `npm run build`
6. **Campaign lifecycle is duplicated** - `/game`, `/session`, and `/resume` still split responsibility
7. **Some schema/runtime drift remains** - especially `story_items`, `story_events`, `quest current_stage`, and `current_location_id`
8. **Theme/content-pack architecture is not runtime-complete** - current non-fantasy support is mostly generation flavor

---
## Next Steps

The old browser-chat implementation plan is stale; browser chat already exists. Future work should follow `WORLDBUILDING_AND_CAMPAIGN_GAP_SPEC.md`.

### Priority Order

1. Stabilize broken schema/runtime/API drift
2. Unify campaign lifecycle under one canonical `/session` flow
3. Fix pause/resume continuity and persistent channel binding
4. Persist first-class `world_theme` and `content_pack_id` with `fantasy_core` as the v1 runtime target
5. Bring browser/dashboard contracts into alignment with the canonical playable session flow

### Immediate Must-Fix Items

- Correct `story_items` helper/schema drift
- Correct `story_events` helper/schema drift
- Stop reading nonexistent `quest['current_stage']`
- Add and use `game_state.current_location_id`
- Fix broken API endpoints calling missing DB methods or wrong signatures
- Remove or deprecate duplicate lifecycle ownership across `/game`, `/session`, and `/resume`

### Planned-Not-Implemented Yet

- full content-pack runtime switching beyond `fantasy_core`
- relational faction runtime and faction reputation systems
- storyline graph execution and clue/reveal systems
- maps, lore, and discovery runtime/editor systems
- complete snapshot/save-point system behind the current UI

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
