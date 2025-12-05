# RPG DM Bot - Database Architecture

**Last Updated:** December 4, 2025  
**Database Type:** SQLite (async via aiosqlite)  
**Location:** `data/rpg.db`

---

## 🔄 Database Migrations

The database uses an automatic migration system to handle schema changes. Migrations are run at initialization time via `_run_migrations()` in `database.py`.

### Migration System Design
- Migrations check if columns/tables exist before attempting to add them
- Uses `PRAGMA table_info()` to introspect existing schema
- Graceful fallbacks if migration fails (error logging, no crash)
- Runs automatically when Database class is instantiated

### Applied Migrations
| Migration | Table | Change | Date Added |
|-----------|-------|--------|------------|
| Add `priority` column | `story_events` | `ALTER TABLE story_events ADD COLUMN priority INTEGER DEFAULT 0` | Dec 4, 2025 |
| Add `triggered_at` column | `story_events` | `ALTER TABLE story_events ADD COLUMN triggered_at TEXT` | Dec 4, 2025 |
| Add `resolved_at` column | `story_events` | `ALTER TABLE story_events ADD COLUMN resolved_at TEXT` | Dec 4, 2025 |
| Add `resolution_outcome` column | `story_events` | `ALTER TABLE story_events ADD COLUMN resolution_outcome TEXT` | Dec 4, 2025 |
| Add `points_of_interest` column | `locations` | `ALTER TABLE locations ADD COLUMN points_of_interest TEXT DEFAULT '[]'` | Dec 4, 2025 |
| Add `is_party_member` column | `npcs` | `ALTER TABLE npcs ADD COLUMN is_party_member INTEGER DEFAULT 0` | Dec 4, 2025 |
| Add `party_role` column | `npcs` | `ALTER TABLE npcs ADD COLUMN party_role TEXT` | Dec 4, 2025 |
| Add `loyalty` column | `npcs` | `ALTER TABLE npcs ADD COLUMN loyalty INTEGER DEFAULT 50` | Dec 4, 2025 |
| Add `combat_stats` column | `npcs` | `ALTER TABLE npcs ADD COLUMN combat_stats TEXT DEFAULT '{}'` | Dec 4, 2025 |

### Adding New Migrations
To add a new migration, edit `_run_migrations()` in `database.py`:
```python
async def _run_migrations(self):
    """Run database migrations for schema changes."""
    async with aiosqlite.connect(self.db_path) as db:
        # Check if column exists before adding
        cursor = await db.execute("PRAGMA table_info(table_name)")
        columns = {row[1] for row in await cursor.fetchall()}
        
        if 'new_column' not in columns:
            await db.execute("ALTER TABLE table_name ADD COLUMN new_column TYPE DEFAULT value")
            await db.commit()
```

---

## 📊 Entity Relationship Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    RPG DM BOT DATABASE SCHEMA                                       │
│                                                                                                     │
│  ┌─────────────────────┐          ┌─────────────────────┐          ┌─────────────────────┐         │
│  │      sessions       │          │      characters     │          │       users         │         │
│  │─────────────────────│          │─────────────────────│          │  (Discord Users)    │         │
│  │ id (PK)             │◄────────┐│ id (PK)             │          │                     │         │
│  │ guild_id            │         ││ user_id ────────────┼──────────►│ user_id            │         │
│  │ name                │         ││ guild_id            │          │                     │         │
│  │ description         │         ││ session_id (FK) ────┼──────────┤                     │         │
│  │ dm_user_id          │         ││ name                │          └─────────────────────┘         │
│  │ status              │         ││ race, class         │                                          │
│  │ max_players         │         ││ level, experience   │                                          │
│  │ setting             │         ││ hp, max_hp          │                                          │
│  │ world_state (JSON)  │         ││ mana, max_mana      │                                          │
│  │ session_notes       │         ││ STR,DEX,CON,INT,WIS │                                          │
│  │ created_at          │         ││ gold, backstory     │                                          │
│  └──────────┬──────────┘         ││ current_location_id─┼──────────► locations.id                  │
│             │                    ││ is_active           │                                          │
│             │                    │└──────────┬──────────┘                                          │
│             │                    │           │                                                     │
│             │                    │           │ 1:N relationships                                   │
│             ▼                    │           ▼                                                     │
│  ┌─────────────────────┐         │┌─────────────────────┐      ┌─────────────────────┐            │
│  │session_participants │         ││      inventory      │      │  character_spells   │            │
│  │─────────────────────│         ││─────────────────────│      │─────────────────────│            │
│  │ id (PK)             │         ││ id (PK)             │      │ id (PK)             │            │
│  │ session_id (FK)─────┼─────────┘│ character_id (FK)───┼──────┤ character_id (FK)───┼────────┐   │
│  │ user_id             │          │ item_id             │      │ spell_id            │        │   │
│  │ character_id (FK)───┼──────────┤ item_name           │      │ spell_name          │        │   │
│  │ joined_at           │          │ item_type           │      │ spell_level         │        │   │
│  └─────────────────────┘          │ quantity            │      │ is_prepared         │        │   │
│                                   │ is_equipped         │      │ is_cantrip          │        │   │
│                                   │ slot                │      │ source              │        │   │
│                                   │ properties (JSON)   │      └─────────────────────┘        │   │
│                                   └─────────────────────┘                                     │   │
│                                                                                               │   │
│  ┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐           │   │
│  │ character_abilities │      │ character_skills    │      │    spell_slots      │           │   │
│  │─────────────────────│      │─────────────────────│      │─────────────────────│           │   │
│  │ id (PK)             │      │ id (PK)             │      │ id (PK)             │           │   │
│  │ character_id (FK)───┼──────┤ character_id (FK)───┼──────┤ character_id (FK)───┼───────────┘   │
│  │ ability_id          │      │ skill_id            │      │ slot_level          │               │
│  │ ability_name        │      │ skill_name          │      │ total               │               │
│  │ ability_type        │      │ skill_branch        │      │ remaining           │               │
│  │ uses_remaining      │      │ skill_tier          │      └─────────────────────┘               │
│  │ max_uses            │      │ is_passive          │                                            │
│  │ recharge            │      │ cooldown_remaining  │      ┌─────────────────────┐               │
│  │ properties (JSON)   │      │ uses_remaining      │      │character_skill_pts  │               │
│  └─────────────────────┘      │ unlocked_at         │      │─────────────────────│               │
│                               └─────────────────────┘      │ character_id (FK)───┼───────────────┤
│                                                            │ total_points        │               │
│  ┌─────────────────────┐                                   │ spent_points        │               │
│  │char_status_effects  │                                   └─────────────────────┘               │
│  │─────────────────────│                                                                         │
│  │ id (PK)             │                                                                         │
│  │ character_id (FK)───┼─────────────────────────────────────────────────────────────────────────┘
│  │ effect_id           │
│  │ effect_name         │
│  │ effect_type         │
│  │ duration_remaining  │
│  │ stacks              │
│  └─────────────────────┘
│
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    QUEST & NPC SUBSYSTEM                                           │
│                                                                                                     │
│  ┌─────────────────────┐          ┌─────────────────────┐          ┌─────────────────────┐         │
│  │       quests        │          │   quest_progress    │          │        npcs         │         │
│  │─────────────────────│          │─────────────────────│          │─────────────────────│         │
│  │ id (PK)             │◄─────────┤ quest_id (FK)       │          │ id (PK)             │         │
│  │ guild_id            │          │ character_id (FK)───┼─────────►│ guild_id            │         │
│  │ session_id (FK)     │          │ objectives_complete │          │ session_id (FK)─────┼──►sessions│
│  │ title               │          │ status              │          │ name                │         │
│  │ description         │          │ started_at          │          │ description         │         │
│  │ objectives (JSON)   │          │ completed_at        │          │ personality         │         │
│  │ rewards (JSON)      │          └─────────────────────┘          │ location            │         │
│  │ status              │                                           │ location_id (FK)────┼──►locations│
│  │ difficulty          │          ┌─────────────────────┐          │ npc_type            │         │
│  │ quest_giver_npc_id──┼──────────┼─────────────────────┼─────────►│ is_merchant         │         │
│  │ dm_notes            │          │  npc_relationships  │          │ merchant_inventory  │         │
│  │ dm_plan             │          │─────────────────────│          │ dialogue_context    │         │
│  │ created_by          │          │ id (PK)             │          │ stats (JSON)        │         │
│  └─────────────────────┘          │ npc_id (FK)─────────┼──────────┤ is_alive            │         │
│                                   │ character_id (FK)   │          │ is_party_member     │◄── NEW  │
│                                   │ reputation          │          │ party_role          │◄── NEW  │
│                                   │ relationship_notes  │          │ loyalty             │◄── NEW  │
│                                   │ last_interaction    │          │ combat_stats (JSON) │◄── NEW  │
│                                   └─────────────────────┘          │ created_by          │         │
│                                                                    └─────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    COMBAT SUBSYSTEM                                                │
│                                                                                                     │
│  ┌─────────────────────┐          ┌─────────────────────┐                                          │
│  │  combat_encounters  │          │combat_participants  │                                          │
│  │─────────────────────│          │─────────────────────│                                          │
│  │ id (PK)             │◄─────────┤ encounter_id (FK)   │                                          │
│  │ guild_id            │          │ participant_type    │ ◄── "character" or "enemy"               │
│  │ channel_id          │          │ participant_id ─────┼───► characters.id (if player)            │
│  │ session_id (FK)─────┼──►sessions│ name               │                                          │
│  │ status              │          │ current_hp          │ ◄── syncs to characters.hp               │
│  │ current_turn        │          │ max_hp              │                                          │
│  │ initiative_order    │          │ initiative          │                                          │
│  │ combatants (JSON)   │          │ is_player           │                                          │
│  │ combat_log (JSON)   │          │ status_effects      │                                          │
│  │ round_number        │          │ turn_order          │                                          │
│  │ created_at          │          └─────────────────────┘                                          │
│  │ ended_at            │                                                                           │
│  └─────────────────────┘                                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  WORLD & STORY SUBSYSTEM                                           │
│                                                                                                     │
│  ┌─────────────────────┐          ┌─────────────────────┐          ┌─────────────────────┐         │
│  │     locations       │          │    story_items      │          │    story_events     │         │
│  │─────────────────────│          │─────────────────────│          │─────────────────────│         │
│  │ id (PK)             │◄────┬────┤ location_id (FK)    │    ┌────►│ id (PK)             │         │
│  │ session_id (FK)─────┼──►sessions session_id (FK)     │    │     │ session_id (FK)─────┼──►sessions│
│  │ guild_id            │     │    │ guild_id            │    │     │ guild_id            │         │
│  │ name                │     │    │ name                │    │     │ name                │         │
│  │ description         │     │    │ description         │    │     │ description         │         │
│  │ location_type       │     │    │ item_type           │    │     │ event_type          │         │
│  │ parent_location_id──┼─────┘    │ lore                │    │     │ trigger_conditions  │         │
│  │ danger_level        │          │ discovery_conditions│    │     │ status              │         │
│  │ current_weather     │          │ is_discovered       │    │     │ priority            │         │
│  │ hidden_secrets      │          │ discovered_by (FK)──┼──►characters│ location_id (FK)──┼─────┐   │
│  │ connected_locations │          │ current_holder_id───┼──►characters│ involved_npcs      │     │   │
│  │ npcs_present        │          │ dm_notes            │    │     │ involved_items      │     │   │
│  └──────────┬──────────┘          │ properties (JSON)   │    │     │ involved_characters │     │   │
│             │                     └─────────────────────┘    │     │ outcomes (JSON)     │     │   │
│             │                                                │     │ dm_notes            │     │   │
│             │                                                │     │ triggered_at        │     │   │
│             ▼                                                └─────┤ resolved_at         │     │   │
│  ┌─────────────────────┐                                          └─────────────────────┘     │   │
│  │location_connections │                                                     ▲                 │   │
│  │─────────────────────│                                                     │                 │   │
│  │ id (PK)             │                                                     └─────────────────┘   │
│  │ from_location_id(FK)┼──► locations                                                              │
│  │ to_location_id (FK) ┼──► locations                                                              │
│  │ direction           │                                                                           │
│  │ travel_time         │                                                                           │
│  │ requirements        │                                                                           │
│  │ hidden              │                                                                           │
│  │ bidirectional       │                                                                           │
│  └─────────────────────┘                                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              MEMORY & HISTORY SUBSYSTEM                                            │
│                                                                                                     │
│  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐   ┌────────────────┐  │
│  │    user_memories    │   │conversation_history │   │     story_log       │   │   dice_rolls   │  │
│  │─────────────────────│   │─────────────────────│   │─────────────────────│   │────────────────│  │
│  │ id (PK)             │   │ id (PK)             │   │ id (PK)             │   │ id (PK)        │  │
│  │ user_id             │   │ user_id             │   │ session_id (FK)─────┼──►sessions        │  │
│  │ guild_id            │   │ guild_id            │   │ entry_type          │   │ user_id        │  │
│  │ memory_key          │   │ channel_id          │   │ content             │   │ guild_id       │  │
│  │ memory_value        │   │ role                │   │ participants (JSON) │   │ session_id(FK)─┼──►sessions│
│  │ context             │   │ content             │   │ created_at          │   │ character_id(FK)─►characters│
│  │ created_at          │   │ created_at          │   └─────────────────────┘   │ roll_type      │  │
│  │ updated_at          │   └─────────────────────┘                             │ dice_expression│  │
│  └─────────────────────┘                                                       │ individual_roll│  │
│                                                                                │ modifier       │  │
│  ┌─────────────────────┐   ┌─────────────────────┐                             │ total          │  │
│  │     game_state      │   │ session_snapshots   │                             │ purpose        │  │
│  │─────────────────────│   │─────────────────────│                             └────────────────┘  │
│  │ id (PK)             │   │ id (PK)             │                                                 │
│  │ session_id (FK) ────┼──►│ session_id (FK)─────┼──►sessions                                      │
│  │ current_scene       │   │ name                │                                                 │
│  │ current_location    │   │ description         │                                                 │
│  │ dm_notes            │   │ snapshot_data (JSON)│ ◄── Full serialized game state                 │
│  │ last_activity       │   │ created_by          │                                                 │
│  │ turn_count          │   │ created_at          │                                                 │
│  │ game_data (JSON)    │   └─────────────────────┘                                                 │
│  └─────────────────────┘                                                                           │
│                                                                                                     │
│  ┌─────────────────────────────────┐                                                               │
│  │    character_interviews         │ ◄── Tracks character creation wizard progress                 │
│  │─────────────────────────────────│                                                               │
│  │ id (PK)                         │                                                               │
│  │ user_id, guild_id               │                                                               │
│  │ dm_channel_id                   │                                                               │
│  │ current_field, responses (JSON) │                                                               │
│  │ stage, started_at, completed    │                                                               │
│  └─────────────────────────────────┘                                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Complete Table Reference

### Core Tables (27 total)

| # | Table Name | Purpose | Key Relationships |
|---|------------|---------|-------------------|
| 1 | `characters` | Player characters with stats, HP, class, race | → sessions, locations ← inventory, spells, abilities, skills |
| 2 | `inventory` | Items owned by characters | → characters |
| 3 | `quests` | Quest definitions | → sessions, npcs, ← quest_progress |
| 4 | `quest_progress` | Per-character quest tracking | → quests, characters |
| 5 | `npcs` | Non-player characters | → sessions, locations ← npc_relationships |
| 6 | `npc_relationships` | Character-NPC reputation | → npcs, characters |
| 7 | `combat_encounters` | Active/past combat sessions | → sessions, ← combat_participants |
| 8 | `combat_participants` | Characters/enemies in combat | → combat_encounters, characters |
| 9 | `sessions` | Game campaigns | ← characters, participants, game_state |
| 10 | `session_participants` | Players in sessions | → sessions, characters |
| 11 | `dice_rolls` | Roll history | → sessions, characters |
| 12 | `user_memories` | AI context memory | (standalone) |
| 13 | `conversation_history` | Chat history for AI | (standalone) |
| 14 | `story_log` | Adventure narrative | → sessions |
| 15 | `character_interviews` | Character creation wizard | (standalone) |
| 16 | `game_state` | Current game state | → sessions |
| 17 | `character_spells` | Known/prepared spells | → characters |
| 18 | `character_abilities` | Class features, traits | → characters |
| 19 | `spell_slots` | Spell slot tracking | → characters |
| 20 | `character_skills` | Skill tree unlocks | → characters |
| 21 | `character_status_effects` | Buffs/debuffs | → characters |
| 22 | `character_skill_points` | Available skill points | → characters |
| 23 | `locations` | World locations | → sessions, self (parent) |
| 24 | `location_connections` | Travel paths between locations | → locations (both ends) |
| 25 | `story_items` | Key items, artifacts | → sessions, locations, characters |
| 26 | `story_events` | Plot events, triggers | → sessions, locations |
| 27 | `session_snapshots` | Save game snapshots | → sessions |

---

## 🔗 Relationship Types

### One-to-Many (1:N)
```
sessions ──────< characters         (A session has many characters)
sessions ──────< session_participants
sessions ──────< story_log
sessions ──────< quests
sessions ──────< npcs
sessions ──────< combat_encounters
sessions ──────< locations
sessions ──────< story_items
sessions ──────< story_events
sessions ──────< session_snapshots

characters ────< inventory          (A character has many items)
characters ────< character_spells
characters ────< character_abilities
characters ────< character_skills
characters ────< character_status_effects
characters ────< quest_progress
characters ────< npc_relationships

quests ────────< quest_progress     (A quest has progress per character)
npcs ──────────< npc_relationships
combat_encounters ─< combat_participants
locations ─────< story_items        (Items can be at locations)
locations ─────< story_events       (Events happen at locations)
locations ─────< locations          (Self-referencing: parent locations)
```

### One-to-One (1:1)
```
sessions ──────── game_state        (Each session has one game state)
characters ────── character_skill_points
```

### Many-to-Many (via junction tables)
```
characters ◄──► quests              (via quest_progress)
characters ◄──► npcs                (via npc_relationships)
users ◄──────► sessions             (via session_participants)
```

---

## 📁 JSON Data Files (Static Game Data)

These files define game content and are loaded at runtime:

| File | Purpose | Key Data |
|------|---------|----------|
| `data/game_data/items.json` | Item definitions | Weapons, armor, potions, accessories with stats |
| `data/game_data/enemies.json` | Enemy templates | HP, AC, attacks, abilities, loot tables |
| `data/game_data/classes.json` | Character classes | Hit dice, abilities by level, spell slots |
| `data/game_data/races.json` | Playable races | Stat bonuses, traits, languages |
| `data/game_data/spells.json` | Spell definitions | Level, damage, effects, components |
| `data/game_data/skills.json` | Skill trees per class | Branches, tiers, prerequisites |
| `data/game_data/npc_templates.json` | NPC templates | Personalities, dialogue styles |
| `data/game_data/starter_kits.json` | Starting equipment per class | Weapons, armor, items |

---

## 🔄 Data Flow Diagrams

### Character Creation Flow
```
User Input ──► character_interviews ──► characters ──► inventory (starter kit)
                     │                       │
                     │                       └──► character_skill_points
                     │                       └──► spell_slots (if caster)
                     └──► session_participants (if in session)
```

### Combat Flow
```
/combat start ──► combat_encounters
                       │
                       └──► combat_participants (add characters)
                       └──► combat_participants (add enemies from enemies.json)
                       │
                  Initiative Roll
                       │
                       └──► dice_rolls (recorded)
                       │
                  Attack/Damage
                       │
                       └──► characters.hp updated
                       └──► combat_participants.current_hp updated
                       └──► character_status_effects (if applicable)
                       │
                  End Combat
                       │
                       └──► characters.experience updated
                       └──► inventory (loot added)
```

### Session/Game Flow
```
/game start ──► sessions (created)
                   │
                   └──► session_participants (DM joined)
                   └──► game_state (initialized)
                   │
              Other Players Join
                   │
                   └──► session_participants
                   └──► characters (linked to session)
                   │
              Game Begins
                   │
                   └──► story_log (entries added)
                   └──► conversation_history (AI context)
                   └──► user_memories (facts stored)
                   │
              Quest/NPC/Combat as needed
                   │
              /save
                   │
                   └──► session_snapshots (full state serialized)
```

---

## 🛠️ Key Database Methods by Category

### Character Management
- `create_character()` - Create new character
- `get_character()` / `get_active_character()` - Retrieve character
- `update_character()` / `update_character_hp()` - Modify character
- `add_experience()` / `level_up_character()` - Progression

### Inventory
- `add_item()` / `remove_item()` - Item management
- `get_inventory()` - List items
- `equip_item()` / `unequip_item()` - Equipment slots

### Sessions
- `create_session()` / `get_session()` - Session CRUD
- `add_session_participant()` - Join session
- `get_user_active_session()` - Get user's current session (isolation)
- `get_full_session_state()` - Complete state for save/load

### Combat
- `start_combat()` / `end_combat()` - Combat lifecycle
- `add_participant()` / `deal_damage()` - Combat actions
- `get_active_combat()` - Current encounter

### Quests & NPCs
- `create_quest()` / `update_quest_progress()` - Quest management
- `create_npc()` / `get_npc()` - NPC management
- `add_relationship_change()` - NPC relationships
- `add_npc_to_party()` - Add NPC as party member (NEW)
- `remove_npc_from_party()` - Remove NPC from party (NEW)
- `get_party_npcs()` - Get all NPC party members (NEW)
- `update_npc_loyalty()` - Adjust NPC loyalty score (NEW)

### World Building
- `get_locations()` / `create_location()` - Location management
- `connect_locations()` / `get_location_connections()` - Travel paths
- `get_story_items()` / `create_story_item()` - Key items
- `get_story_events()` / `create_story_event()` - Plot events

### Memory & History
- `add_memory()` / `get_recent_memories()` - AI context
- `add_conversation()` / `get_conversation_history()` - Chat history
- `add_story_entry()` - Narrative log
- `log_dice_roll_with_session()` / `get_session_roll_history()` - Session-aware dice rolls

### Cross-System Wiring Methods (NEW)
These methods handle the integration between subsystems:

#### Character-Location Integration
- `move_character_to_location()` - Move character and log to story
- `get_characters_at_location()` - Find all characters at a location
- `explore_location()` - Full exploration revealing NPCs, items, connections

#### NPC-Location Integration
- `move_npc_to_location()` - Place NPC at a location
- `get_npcs_at_location()` - Find NPCs at a specific location

#### Combat-Character Sync
- `sync_combat_damage_to_character()` - Sync participant HP back to character
- `sync_all_combat_to_characters()` - Sync all players after combat
- `award_combat_experience()` - Grant XP to surviving players
- `end_combat_with_rewards()` - Complete combat flow with XP, gold, loot

#### Quest Rewards Integration
- `complete_quest_with_rewards()` - Complete quest and auto-grant XP, gold, items

#### Story Item Integration
- `pickup_story_item()` - Character picks up story item (adds to inventory)
- `drop_story_item()` - Character drops story item at location

#### Story Event Integration
- `add_character_to_event()` - Link character to a story event
- `get_events_for_character()` - Get all events involving a character

#### Session Management
- `initialize_session()` - Ensure game_state exists
- `start_session_with_init()` - Start session with full initialization
- `get_comprehensive_session_state()` - Complete state for AI context or saves


#### Recovery Methods
- `long_rest()` - Full recovery (HP, spell slots, abilities, skills)
- `short_rest()` - Partial recovery

#### Generative AI Worldbuilding Tools (NEW)
These tools enable AI-driven procedural content generation:
- `generate_world()` - Generate world settings, factions, history, locations
- `generate_quest_hook()` - Create dynamic quest hooks based on context
- `generate_character_backstory()` - Generate NPC or PC backstories
- `generate_encounter()` - Create contextual encounters (combat/social/puzzle)
- `generate_loot()` - Generate loot drops based on context
- `initialize_campaign()` - Full campaign setup with world, NPCs, starting quests

---

## 🔧 Wiring Checklist (MVP Verification)

**Last Verified:** December 4, 2025  
**Test Results:** ✅ 127 tests pass

Use this checklist to verify all systems are properly connected:

### ✅ Core Systems (VERIFIED)
- [x] Characters link to sessions via `session_id`
- [x] Characters link to locations via `current_location_id`
- [x] Session participants link characters to sessions
- [x] Game state exists for each active session (auto-created via `initialize_session()`)
- [x] Story log records events per session

### ✅ Character Subsystems (VERIFIED)
- [x] Inventory items link to character
- [x] Spells link to character
- [x] Abilities link to character
- [x] Skills link to character
- [x] Spell slots link to character
- [x] Skill points link to character
- [x] Status effects link to character

### ✅ Quest System (VERIFIED)
- [x] Quests link to session
- [x] Quest progress links quest ↔ character
- [x] Quest giver NPC links quest ↔ NPC
- [x] Quest completion auto-grants rewards via `complete_quest_with_rewards()`

### ✅ NPC System (VERIFIED)
- [x] NPCs link to session
- [x] NPCs link to locations via `location_id`
- [x] NPC relationships link NPC ↔ character
- [x] NPC relationship values capped at ±100

### ✅ Combat System (VERIFIED)
- [x] Combat encounters link to session
- [x] Combat participants link to encounter
- [x] Combat participants reference characters via `participant_id`
- [x] Damage syncs to character HP via `sync_combat_damage_to_character()`
- [x] Combat end awards XP/gold/loot via `end_combat_with_rewards()`
- [x] `get_active_combat(channel_id=)` properly detects active combat

### ✅ World System (VERIFIED)
- [x] Locations link to session
- [x] Locations connect via `location_connections` table
- [x] Story items link to locations and characters
- [x] Story items can be picked up/dropped (inventory integration)
- [x] Story events link to locations
- [x] Story events track involved characters via `involved_characters`
- [x] Locations can have parent locations

### ✅ Dice System (VERIFIED)
- [x] Dice rolls link to sessions via `session_id`
- [x] Dice rolls link to characters via `character_id`
- [x] Session roll history available via `get_session_roll_history()`

### ✅ Tools System (VERIFIED - 67 tools)
- [x] All tool schemas in `tool_schemas.py` have implementations in `tools.py`
- [x] All tool implementations callable via `execute_tool()`
- [x] Tool argument validation working
- [x] Error handling returns user-friendly messages

### ✅ API Endpoints (VERIFIED - ~76 endpoints)
- [x] `/api/characters` - CRUD for characters
- [x] `/api/characters/{id}/spells` - Character spells
- [x] `/api/characters/{id}/abilities` - Character abilities
- [x] `/api/characters/{id}/skills` - Character skills
- [x] `/api/characters/{id}/status-effects` - Status effects
- [x] `/api/characters/{id}/rest/{type}` - Rest mechanics
- [x] `/api/sessions` - CRUD for sessions
- [x] `/api/inventory` - Item management
- [x] `/api/quests` - Quest management
- [x] `/api/npcs` - NPC management
- [x] `/api/npcs/{id}/relationships` - NPC relationships
- [x] `/api/locations` - Location management
- [x] `/api/locations/{id}/connections` - Travel paths
- [x] `/api/items` (story items) - Key item management
- [x] `/api/events` (story events) - Event management
- [x] `/api/combat` - Combat management
- [x] `/api/gamedata/*` - Static game data (classes, races, items, spells, skills)

### ✅ Frontend Pages (PARTIAL - API methods exist, some UI missing)
- [x] Dashboard - Overview
- [x] Sessions - Session management
- [x] Characters - Character list/edit
- [x] Quests - Quest management
- [x] NPCs - NPC management
- [x] Locations - Location management
- [x] Classes - Class editor (from JSON)
- [x] Races - Race editor (from JSON)
- [x] Skill Trees - Skill browser
- [x] Item Database - Item browser with search and filtering
- [x] Spellbook - Spell browser with filtering by school/level/class
- [x] Class Editor - Full CRUD with PUT /api/gamedata/classes
- [x] Skill Tree Editor - Edit branches via PUT /api/gamedata/skills/trees/{class}
- [ ] Combat viewer - UI not built (API ready)
- [ ] Spell management panel - UI not built (API ready)
- [ ] Location connection map - UI not built (API ready)
- [ ] Browser chat interface - Not implemented (see HANDOFF.md for plan)

---

## 🐛 Bug Fixes Applied (December 5, 2025 - Session 8)

| Bug | Location | Fix |
|-----|----------|-----|
| `no such column: priority` in `get_active_events()` | `database.py` | Added `_run_migrations()` to add missing column at init; added fallback query without ORDER BY priority |
| `get_pending_events()` same column error | `database.py` | Added same fallback pattern |
| Session isolation - characters from other sessions leaking | `tools.py` | Added `_get_session_for_context()` helper that prioritizes: `context['session_id']` → `get_user_active_session()` → `get_active_session()` |
| Tool context missing session_id | `cogs/dm_chat.py` | Added `'session_id': session_id` to context dict in both `process_batched_messages()` and `process_dm_message()` |
| 15+ tools using wrong session lookup | `tools.py` | Updated `_start_combat`, `_create_quest`, `_create_npc`, `_get_party_info`, `_add_story_entry`, `_get_story_log`, `_create_location`, `_move_party_to_location`, `_create_story_item`, `_get_story_items`, `_create_story_event`, `_get_active_events`, `_generate_npc`, `_long_rest`, `_end_combat_with_rewards` |

## 🐛 Bug Fixes Applied (December 4, 2025 - Session 7)

| Bug | Location | Fix |
|-----|----------|-----|
| `/api/gamedata/items` wrong response structure | `api.py` | Returns `{items: {...}}` instead of raw JSON |
| Classes display showing `Unknown` for primary stat | `main.ts` | Handle `primary_stat` field (not just `primary_ability`) |
| Abilities not rendering (object vs array) | `main.ts` | Flatten abilities object keyed by level for display |
| No PUT endpoints for classes/races/skills | `api.py` | Added PUT endpoints for bulk updates |
| Cannot edit skill tree branches | `main.ts` | Added `editSkillBranch()` and `saveSkillBranch()` functions |

## Bug Fixes Applied (December 4, 2025 - Session 6)

| Bug | Location | Fix |
|-----|----------|-----|
| Duplicate `update_gold()` returning `True` | `database.py:2441` | Removed duplicate, kept version returning gold amount |
| Missing `update_combatant_initiative()` | `database.py` | Added new method |
| NPC relationships not capped at ±100 | `database.py:update_npc_relationship()` | Added `max(-100, min(100, value))` for initial |
| `get_active_combat()` positional arg bug | `tools.py` (7 locations) | Changed to `channel_id=channel_id` keyword arg |
| `_roll_initiative()` broken async code | `tools.py:489` | Replaced with proper `update_combatant_initiative()` call |

---

## 📝 Notes

1. **JSON Columns**: Several tables use JSON for flexible data:
   - `properties`, `stats`, `objectives`, `rewards`, `world_state`
   - `involved_characters`, `involved_npcs`, `involved_items`
   - Always parse with `json.loads()` when reading

2. **Timestamps**: All use ISO format strings (`datetime.isoformat()`)

3. **IDs**: All use auto-increment integers, referenced in other tables

4. **Soft Deletes**: `is_active`, `is_alive` flags rather than hard deletes

5. **Session Isolation**: Tools use `_get_session_for_context()` helper to ensure operations stay within the correct session:
   - First checks `context['session_id']` (explicitly passed from dm_chat.py)
   - Falls back to `get_user_active_session(user_id, guild_id)` for user's specific session
   - Last resort: `get_active_session(guild_id)` for any active session
   - This prevents character/data leakage between concurrent sessions

6. **Story Logging**: Many wiring methods automatically log to `story_log` when changes occur

7. **Location Tracking**: Both characters and NPCs now have `location_id` foreign keys to the `locations` table

8. **Keyword Arguments**: When calling `get_active_combat()`, always use `channel_id=` or `guild_id=` keyword arguments, not positional

9. **Database Migrations**: Schema changes are handled via `_run_migrations()` at Database init. See Migration System section above. Queries that depend on migrated columns should have fallback handlers.

---

*Last Updated: December 5, 2025 - Session 8: Session isolation and migration fixes*
