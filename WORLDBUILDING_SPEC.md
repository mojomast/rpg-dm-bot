# RPG DM Bot — Worldbuilding & Campaign Completeness Spec

## Executive Summary

This repo already contains a broad RPG feature surface: sessions, characters, inventory, quests, NPCs, combat, AI DM chat, world-generation tools, and a web dashboard. What it does not yet have is a coherent worldbuilding architecture that makes those systems compose cleanly across genres and across the full campaign lifecycle.

Top 10 gaps:

1. Theme is flavor, not first-class data. `world_theme` exists in web campaign generation, but persistence, content selection, tools, prompts, and mechanics do not consistently resolve against a real theme/content-pack model.
2. Static game data is fantasy-first and monolithic. `classes.json`, `races.json`, `spells.json`, `skills.json`, `items.json`, and `starter_kits.json` are designed around fantasy assumptions and cannot cleanly power sci-fi, horror, modern, or steampunk campaigns.
3. Location hierarchy is only partially modeled. `locations.parent_location_id` exists, but the runtime/API/tool layer still treats locations as mostly flat nodes with JSON blobs instead of a true world-region-zone-location-sublocation model.
4. Map and discovery systems are missing. Connections exist, but there is no proper map layer, no map nodes, no traversable visualization model, and no robust discovery/reveal tracking for hidden routes, secrets, clues, or player-known geography.
5. NPCs and monsters are split across incompatible models. Social NPCs live in `npcs`, combat enemies live in `enemies.json`, and boss/faction/reputation systems are only partial or absent.
6. Factions are generated as preview content but not persisted as relational gameplay data. There is no real faction table, no faction membership, and no player-to-faction reputation system.
7. Story architecture is flat. Quests, events, story items, and story log entries exist, but there is no campaign/arc/chapter/scene/beat graph, no quest prerequisites/branching/failure model, and no formal clue or revelation system.
8. Browser and Discord flows still do not form one canonical play loop. Web campaign creation can generate content, but the handoff into Discord session ownership, participants, channel anchoring, and resumed play remains partial.
9. Tooling breadth exceeds tool rigor. Many handlers and schemas exist, but core worldbuilding domains such as theme switching, faction management, map editing, clue discovery, and boss-phase control do not yet have first-class tools.
10. The project needs a phased implementation plan, not more isolated features. Without a common content-pack loader, narrative graph, and world model, new content will keep accumulating in incompatible shapes.

This spec recommends a unifying strategy:

- Treat `sessions` as the canonical campaign container.
- Add first-class `world_theme`, `content_pack_id`, and `rules_profile_id` to sessions.
- Move static content into per-theme content packs under `data/game_data/packs/`.
- Separate containment hierarchy, traversal graph, maps, and discovery state for locations.
- Introduce real faction, monster-template, boss-phase, and storyline graph schemas.
- Unify the happy path so the web dashboard prepares the world and Discord runs the live table.

## Section 1 — World Theming & Genre Separation

### 1. What data model changes are needed to support multiple world themes

Current state:

- Theme exists mostly as preview-generation flavor in `web/api.py` via `CampaignSettings.world_theme`, `magic_level`, `technology_level`, and `tone`.
- `sessions` only has `setting TEXT` and `world_state TEXT`, while `game_state` only has generic `game_data` and `dm_notes`.
- Static content is global and fantasy-centric.

Recommendation: make theme a first-class session identity and content-pack selection mechanism.

Add to `sessions`:

```sql
ALTER TABLE sessions ADD COLUMN world_theme TEXT NOT NULL DEFAULT 'fantasy';
ALTER TABLE sessions ADD COLUMN genre_family TEXT NOT NULL DEFAULT 'fantasy';
ALTER TABLE sessions ADD COLUMN content_pack_id TEXT NOT NULL DEFAULT 'fantasy_core';
ALTER TABLE sessions ADD COLUMN rules_profile_id TEXT DEFAULT 'd20_fantasy';
ALTER TABLE sessions ADD COLUMN theme_config TEXT NOT NULL DEFAULT '{}';
```

Add to `game_state`:

```sql
ALTER TABLE game_state ADD COLUMN active_content_pack_id TEXT;
ALTER TABLE game_state ADD COLUMN theme_state TEXT NOT NULL DEFAULT '{}';
ALTER TABLE game_state ADD COLUMN allowed_content_packs TEXT NOT NULL DEFAULT '[]';
```

Recommended purpose split:

- `sessions.world_theme`: canonical campaign theme, e.g. `fantasy`, `scifi`, `horror`, `modern`, `steampunk`
- `sessions.content_pack_id`: which content library is loaded
- `sessions.rules_profile_id`: mechanics mode, e.g. `d20_fantasy`, `stress_horror`, `ammo_scifi`
- `sessions.theme_config`: campaign-specific toggles and options
- `game_state.theme_state`: mutable runtime theme conditions such as corruption, heat, dread, oxygen, or faction alertness

Migration notes:

- Backfill `world_theme` from `sessions.setting` or `world_state.world_setting.theme` where present.
- Backfill `content_pack_id` using a map like `fantasy -> fantasy_core`, `sci-fi -> scifi_core`, `horror -> horror_core`, `modern -> modern_core`, `steampunk -> steampunk_core`.
- Keep `world_state` for generated campaign specifics, but treat the new columns as the source of truth after migration.

### 2. Should classes/races/items/spells/skills be tagged by theme or split by separate JSON files

Audit summary:

- `data/game_data/classes.json` is fantasy-only.
- `data/game_data/races.json` is fantasy-only.
- `data/game_data/spells.json` is fantasy magic only.
- `data/game_data/skills.json` mixes fantasy MMO-style class trees, passives, and statuses.
- `data/game_data/items.json` contains reusable primitives such as `ammunition`, `charges`, and `effect`, but the catalog is still medieval-fantasy.

Recommendation: use separate files per theme/content-pack, with optional tags inside entries for cross-pack reuse.

Use tags only where an entry is intentionally reusable across themes, for example:

- `common`
- `low_magic`
- `urban`
- `modern_firearms`
- `steampunk`
- `scifi`
- `horror`

Do not keep one giant unified `items.json` or `spells.json` containing every genre. The current schema is already too fantasy-shaped for that to remain maintainable.

### 3. What is the minimum viable set of content per theme to run a campaign

Minimum viable means “short campaign playable,” not feature parity.

Per theme, ship at least:

- 4-6 player archetypes/classes
- 4-6 ancestries/origins/background packages
- 20-40 core items
- 15-30 powers/spells/abilities where the theme supports them
- 10-15 enemy entries
- 1 NPC template library
- 1 starter kit library
- 1 world template library

Theme-by-theme MVP:

- Fantasy: classes, ancestries, spells, monsters, weapons/armor, settlements, factions
- Sci-fi: archetypes, species/origins, guns, gadgets, vehicles, alien enemies, stations/planets, factions
- Horror: occupations/origins, gear, sanity/stress conditions, mysteries, monsters, low-combat NPC templates
- Modern: careers/backgrounds, firearms, surveillance/gadgets, vehicles, criminal/corporate factions, urban locations
- Steampunk: hybrid archetypes, gadgets, pressure/fuel mechanics, automata, industrial city locations, guild factions

### 4. What schema changes are needed in `sessions` and `game_state`

Summary recommendation:

- Add `world_theme`, `genre_family`, `content_pack_id`, `rules_profile_id`, `theme_config` to `sessions`
- Add `active_content_pack_id`, `theme_state`, `allowed_content_packs` to `game_state`
- Add indexes on `world_theme` and `content_pack_id`

This gives the runtime a stable way to answer:

- what kind of world is this?
- which content files should be loaded?
- which mechanical rules apply?
- which dynamic theme variables are active right now?

### 5. What new tool schemas and handlers are needed for theme-switching

Current tool surface includes worldbuilding handlers like:

- `_generate_world`
- `_generate_key_npcs`
- `_generate_location`
- `_generate_quest`
- `_generate_encounter`
- `_generate_backstory`
- `_generate_loot`
- `_initialize_campaign`

There are no first-class theme management tools yet.

Add tool schemas and matching handlers for:

- `get_session_theme`
- `set_session_theme`
- `list_content_packs`
- `switch_content_pack`
- `get_theme_rules`
- `get_theme_content`
- `validate_theme_content`

Responsibilities:

- `get_session_theme`: return canonical theme/profile/pack for the current session
- `set_session_theme`: DM-only update of theme/profile/config
- `list_content_packs`: list installed packs and metadata
- `switch_content_pack`: swap active pack without destroying campaign state
- `get_theme_rules`: return rule-profile semantics for prompts and tools
- `get_theme_content`: resolve classes/items/powers/enemies/templates scoped to the active pack
- `validate_theme_content`: reject fantasy-only content inside a sci-fi campaign unless explicitly shared

### 6. Full file/folder structure for theme content under `data/game_data/`

Recommended target:

```text
data/game_data/
├── manifests/
│   ├── content_packs.json
│   ├── rules_profiles.json
│   └── themes.json
├── shared/
│   ├── common/
│   │   ├── tags.json
│   │   ├── status_effects.json
│   │   ├── conditions.json
│   │   ├── generic_skills.json
│   │   ├── generic_items.json
│   │   └── prompt_fragments.json
│   └── editor_schema/
│       ├── archetypes.schema.json
│       ├── items.schema.json
│       ├── powers.schema.json
│       └── world_templates.schema.json
├── packs/
│   ├── fantasy/
│   │   └── core/
│   │       ├── manifest.json
│   │       ├── archetypes.json
│   │       ├── ancestries.json
│   │       ├── items.json
│   │       ├── powers.json
│   │       ├── skills.json
│   │       ├── enemies.json
│   │       ├── npc_templates.json
│   │       ├── starter_kits.json
│   │       ├── factions.json
│   │       ├── locations.json
│   │       ├── encounters.json
│   │       └── world_templates.json
│   ├── scifi/
│   │   └── core/
│   │       ├── manifest.json
│   │       ├── archetypes.json
│   │       ├── origins.json
│   │       ├── items.json
│   │       ├── powers.json
│   │       ├── skills.json
│   │       ├── enemies.json
│   │       ├── npc_templates.json
│   │       ├── starter_kits.json
│   │       ├── factions.json
│   │       ├── locations.json
│   │       ├── vehicles.json
│   │       └── world_templates.json
│   ├── horror/
│   │   └── core/
│   │       ├── manifest.json
│   │       ├── archetypes.json
│   │       ├── backgrounds.json
│   │       ├── items.json
│   │       ├── powers.json
│   │       ├── skills.json
│   │       ├── enemies.json
│   │       ├── npc_templates.json
│   │       ├── starter_kits.json
│   │       ├── mysteries.json
│   │       ├── locations.json
│   │       └── world_templates.json
│   ├── modern/
│   │   └── core/
│   │       ├── manifest.json
│   │       ├── archetypes.json
│   │       ├── backgrounds.json
│   │       ├── items.json
│   │       ├── powers.json
│   │       ├── skills.json
│   │       ├── enemies.json
│   │       ├── npc_templates.json
│   │       ├── starter_kits.json
│   │       ├── factions.json
│   │       ├── locations.json
│   │       ├── vehicles.json
│   │       └── world_templates.json
│   └── steampunk/
│       └── core/
│           ├── manifest.json
│           ├── archetypes.json
│           ├── origins.json
│           ├── items.json
│           ├── powers.json
│           ├── skills.json
│           ├── enemies.json
│           ├── npc_templates.json
│           ├── starter_kits.json
│           ├── factions.json
│           ├── locations.json
│           ├── vehicles.json
│           └── world_templates.json
└── legacy/
    ├── classes.json
    ├── races.json
    ├── items.json
    ├── spells.json
    ├── skills.json
    ├── enemies.json
    ├── npc_templates.json
    └── starter_kits.json
```

Migration path:

- Move current root JSON into `packs/fantasy/core/`
- Keep compatibility loaders for the old flat files during transition
- Update editor/API loaders to use `content_pack_id`

## Section 2 — Locations, Maps & Lore

### 1. What is missing from the current locations table and location system

Current strengths:

- `locations` has `parent_location_id`
- `location_connections` exists
- `story_items` and `story_events` can point at `location_id`

Current gaps:

- hierarchy exists in schema but not in tooling or API
- `points_of_interest` is effectively broken/misaligned
- travel ignores adjacency and requirements
- NPC placement is split between `location` text and `location_id`
- secrets/lore are trapped in raw text blobs
- there is no real discovery or map model

Specific repo issues:

- `locations.parent_location_id` exists, but create/update methods and APIs do not expose a real containment tree.
- `create_location` and `update_location` misuse JSON location fields and do not normalize reads consistently.
- `move_party_to_location` and `move_character_to_location` act like teleportation instead of traversing the connection graph.
- `connect_locations` in DB and the web API are mismatched in required arguments.

### 2. Full location hierarchy schema

Use one normalized location tree for containment:

`world/setting -> plane -> continent/ocean -> nation/realm -> region/province -> subregion/frontier -> settlement/site -> district/zone -> structure/interior -> room/sublocation`

Recommended `locations` shape:

```sql
CREATE TABLE locations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER,
  guild_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  parent_location_id INTEGER,
  root_location_id INTEGER,
  hierarchy_kind TEXT NOT NULL,
  geography_type TEXT NOT NULL,
  canonical_path TEXT NOT NULL,
  depth INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER NOT NULL DEFAULT 0,
  summary TEXT,
  description TEXT,
  climate TEXT,
  terrain TEXT,
  tags TEXT DEFAULT '[]',
  population_text TEXT,
  faction_owner_id INTEGER,
  map_default_id INTEGER,
  is_hidden INTEGER NOT NULL DEFAULT 0,
  discoverability TEXT NOT NULL DEFAULT 'visible',
  dm_notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (parent_location_id) REFERENCES locations(id),
  FOREIGN KEY (root_location_id) REFERENCES locations(id)
);
```

Recommendation:

- stop treating points of interest as JSON strings
- represent taverns, districts, ruins, rooms, and landmarks as real child locations

### 3. How lore, history, and secrets attach to locations

Use dedicated lore tables instead of `hidden_secrets TEXT` on `locations`.

Recommended tables:

```sql
CREATE TABLE lore_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER,
  guild_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  lore_type TEXT NOT NULL,
  body_markdown TEXT NOT NULL,
  truth_status TEXT NOT NULL DEFAULT 'true',
  visibility TEXT NOT NULL DEFAULT 'public',
  era_label TEXT,
  source_label TEXT,
  discovery_rule_id INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE location_lore_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  location_id INTEGER NOT NULL,
  lore_entry_id INTEGER NOT NULL,
  relation_type TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  UNIQUE(location_id, lore_entry_id)
);
```

Use cases:

- `history`
- `culture`
- `rumor`
- `legend`
- `secret`
- `hazard`
- `hook`

### 4. How location discovery works

Discovery should be a persistent overlay, not a boolean on the entity itself.

Recommended tables:

```sql
CREATE TABLE discovery_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER,
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  trigger_type TEXT NOT NULL,
  skill_name TEXT,
  dc INTEGER,
  requirements_json TEXT DEFAULT '{}',
  rewards_json TEXT DEFAULT '{}',
  once_per_scope INTEGER NOT NULL DEFAULT 1,
  scope TEXT NOT NULL DEFAULT 'party',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE discoveries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  scope TEXT NOT NULL,
  character_id INTEGER,
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  discovered_by INTEGER,
  discovery_method TEXT,
  notes TEXT,
  discovered_at TEXT NOT NULL,
  UNIQUE(session_id, scope, character_id, entity_type, entity_id)
);
```

Rules:

- entering a location can auto-discover it
- searching/exploring can reveal child locations, hidden exits, lore, items, and clues
- discovery can be party-scoped or character-scoped
- `explore_location` should actually evaluate discovery rules using the provided roll data

### 5. What a map looks like in this system

Treat maps as canvases and location connections as traversal edges.

Recommended tables:

```sql
CREATE TABLE maps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER,
  guild_id INTEGER NOT NULL,
  root_location_id INTEGER NOT NULL,
  parent_map_id INTEGER,
  map_type TEXT NOT NULL,
  name TEXT NOT NULL,
  background_asset_url TEXT,
  width INTEGER,
  height INTEGER,
  grid_type TEXT,
  scale_label TEXT,
  fog_enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE map_location_nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  map_id INTEGER NOT NULL,
  location_id INTEGER NOT NULL,
  x REAL NOT NULL,
  y REAL NOT NULL,
  shape_type TEXT NOT NULL DEFAULT 'point',
  shape_data TEXT,
  icon TEXT,
  label TEXT,
  floor_level INTEGER DEFAULT 0,
  is_default_entry INTEGER NOT NULL DEFAULT 0,
  UNIQUE(map_id, location_id)
);
```

Extend `location_connections` with:

- `connection_type`
- `distance_text`
- `travel_mode`
- `lock_state`
- `map_path_data`
- `discovery_rule_id`

### 6. What new DB tables, tool schemas, and handlers are needed

Add/extend DB tables:

- extend `locations`
- extend `location_connections`
- add `maps`
- add `map_location_nodes`
- add `lore_entries`
- add `location_lore_links`
- add `discovery_rules`
- add `discoveries`

Add DB methods such as:

- `get_location_tree`
- `move_location`
- `create_location_connection`
- `get_location_map`
- `create_lore_entry`
- `mark_discovered`
- `evaluate_discovery_rules`

Add tool schemas/handlers:

- `create_location_connection`
- `update_location_connection`
- `get_location_tree`
- `move_location`
- `create_location_lore`
- `get_location_lore`
- `search_location`
- `discover_location`
- `create_map`
- `update_map`
- `place_location_on_map`
- `get_map`

### 7. What new API endpoints are needed for the location editor

Recommended endpoints:

- `GET /api/locations/tree?session_id=...`
- `POST /api/locations/{location_id}/move`
- `GET /api/locations/{location_id}/connections`
- `POST /api/location-connections`
- `PATCH /api/location-connections/{connection_id}`
- `DELETE /api/location-connections/{connection_id}`
- `GET /api/locations/{location_id}/lore`
- `POST /api/locations/{location_id}/lore`
- `GET /api/locations/{location_id}/discovery-rules`
- `POST /api/locations/{location_id}/discover`
- `GET /api/maps?session_id=...`
- `POST /api/maps`
- `GET /api/maps/{map_id}`
- `POST /api/maps/{map_id}/nodes`
- `GET /api/locations/{location_id}/editor`

The aggregated editor payload should include:

- location
- ancestors
- children
- connections
- maps
- map nodes
- lore
- discovery rules
- discovery state
- NPCs here
- story items here

## Section 3 — NPCs, Monsters, Bosses & Factions

### 1. Design a complete NPC/Monster taxonomy

Current state:

- `npcs` is a generic social/hybrid actor table
- `enemies.json` is the only monster stat-block source
- `npc_templates.json` is roleplay-focused and not combat/faction aware

Recommended unified taxonomy:

- `actor_kind`: `npc`, `monster`, `beast`, `humanoid_enemy`, `boss`, `companion`, `merchant`, `quest_giver`, `faction_leader`
- `role`: `social`, `combat`, `hybrid`
- `disposition`: `friendly`, `neutral`, `hostile`
- `creature_family`: `humanoid`, `undead`, `construct`, `dragon`, `fiend`, etc.
- `creature_tags`: freeform tags like `goblinoid`, `cultist`, `underground`, `swarm`

Recommended additional fields beyond the current schema:

- `slug`
- `actor_kind`
- `role`
- `creature_family`
- `creature_tags`
- `size`
- `alignment`
- `backstory`
- `goals`
- `ideals`
- `bonds`
- `flaws`
- `voice`
- `portrait_url`
- `home_location_id`
- `faction_id`
- `faction_role`
- `challenge_rating`
- `armor_class`
- `hit_points`
- `hit_dice`
- `speed`
- `ability_scores`
- `saving_throws`
- `skills`
- `senses`
- `languages`
- `damage_vulnerabilities`
- `damage_resistances`
- `damage_immunities`
- `condition_immunities`
- `traits`
- `actions`
- `bonus_actions`
- `reactions`
- `legendary_actions`
- `lair_actions`
- `spellcasting`
- `encounter_role`
- `resource_pools`
- `sheet_data`

Recommendation:

- keep `npcs` for persistent social/hybrid actors
- add `monster_templates` for reusable stat blocks
- add `actor_stat_blocks` or expand combat participants for instantiated monsters/bosses

### 2. Design boss fight mechanics

Current gaps:

- no boss phase storage
- no legendary actions
- no lair actions
- no reinforcement triggers
- no encounter objectives beyond “reduce HP to zero”

Recommended boss mechanics:

- HP-threshold phases
- per-round legendary action pool
- lair action initiative triggers
- mythic second form / partial reset
- objective-based encounter layers
- boss resource pools
- reinforcement wave triggers
- telegraphed environmental hazards

Recommended tables:

```sql
CREATE TABLE monster_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  creature_family TEXT,
  challenge_rating REAL,
  stat_block_json TEXT NOT NULL,
  source TEXT
);

CREATE TABLE boss_phases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  boss_actor_id INTEGER NOT NULL,
  phase_order INTEGER NOT NULL,
  trigger_type TEXT NOT NULL,
  trigger_value TEXT,
  name TEXT NOT NULL,
  transition_text TEXT,
  phase_state_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE boss_abilities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  boss_actor_id INTEGER NOT NULL,
  ability_type TEXT NOT NULL,
  name TEXT NOT NULL,
  cost INTEGER DEFAULT 0,
  initiative_count INTEGER,
  data_json TEXT NOT NULL DEFAULT '{}'
);
```

Minimum migration option:

- extend `combat_encounters` with `encounter_type`, `location_id`, `boss_state`, `lair_state`, `environment_state`
- extend `combat_participants` with `template_id`, `combat_stats`, `resource_state`, `phase_state`, `is_boss`, `legendary_actions_remaining`, `legendary_resistances_remaining`

### 3. Design faction system

Current state:

- factions are generated in web previews/finalization but not stored relationally
- only `npc_relationships` exists, and it is per-character-to-NPC

Recommended faction tables:

```sql
CREATE TABLE factions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER NOT NULL,
  session_id INTEGER,
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  faction_type TEXT,
  alignment TEXT,
  description TEXT,
  goals TEXT,
  methods TEXT,
  resources TEXT,
  territory TEXT,
  visibility TEXT,
  parent_faction_id INTEGER,
  is_secret INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE faction_memberships (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  faction_id INTEGER NOT NULL,
  member_type TEXT NOT NULL,
  member_id INTEGER NOT NULL,
  role TEXT,
  rank TEXT,
  status TEXT,
  joined_at TEXT,
  left_at TEXT
);

CREATE TABLE character_faction_reputation (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  character_id INTEGER NOT NULL,
  faction_id INTEGER NOT NULL,
  reputation INTEGER DEFAULT 0,
  standing TEXT DEFAULT 'neutral',
  favor INTEGER DEFAULT 0,
  renown INTEGER DEFAULT 0,
  last_change_at TEXT,
  notes TEXT,
  UNIQUE(character_id, faction_id)
);
```

Recommended effects of faction reputation:

- quest availability
- NPC disposition changes
- merchant pricing / access
- access to safehouses/services
- reinforcements or bounty risk
- branching story consequences

### 4. What new tool schemas and handlers are needed

Add:

- `create_monster`
- `spawn_monster`
- `get_stat_block`
- `update_stat_block`
- `start_boss_encounter`
- `advance_boss_phase`
- `use_legendary_action`
- `trigger_lair_action`
- `create_faction`
- `update_faction`
- `get_factions`
- `set_npc_faction`
- `update_faction_reputation`
- `get_character_faction_reputation`
- `record_faction_event`

Also fix existing handlers:

- `_create_npc` should accept/persist `location_id`, `stats`, `faction_id`, `tags`, `goals`, `secrets`
- `_generate_npc` should load `npc_templates.json` instead of hardcoded template data
- `_add_enemy` should persist full combat stats and template references

### 5. What new API endpoints are needed

Recommended endpoints:

- `GET /api/npcs`
- `POST /api/npcs`
- `GET /api/npcs/{npc_id}/stat-block`
- `PATCH /api/npcs/{npc_id}/stat-block`
- `POST /api/npcs/{npc_id}/relationships`
- `GET /api/monsters`
- `POST /api/monsters`
- `GET /api/monster-templates`
- `GET /api/encounters/{encounter_id}/boss-state`
- `POST /api/encounters/{encounter_id}/boss-phase/advance`
- `POST /api/encounters/{encounter_id}/legendary-action`
- `POST /api/encounters/{encounter_id}/lair-action`
- `GET /api/factions`
- `POST /api/factions`
- `GET /api/factions/{faction_id}`
- `PATCH /api/factions/{faction_id}`
- `GET /api/factions/{faction_id}/members`
- `POST /api/factions/{faction_id}/members`
- `GET /api/characters/{character_id}/factions`
- `PATCH /api/characters/{character_id}/factions/{faction_id}`

### 6. What changes to `npc_templates.json` structure are needed

Current templates are strong for persona generation, but weak for gameplay semantics.

Add per-template:

- `template_id`
- `actor_kind`
- `role`
- `creature_family`
- `default_size`
- `default_alignment`
- `faction_archetypes`
- `location_types`
- `encounter_role`
- `tags`
- `ideals`
- `bonds`
- `flaws`
- `hooks`
- `combat_profile`
- `companion_profile`
- `elite_profile`
- `boss_profile`
- `default_faction_roles`
- `reputation_biases`

Also expand name generators beyond human/elf/dwarf.

## Section 4 — Storylines, Plot Points & Quest Wiring

### 1. What is missing from the current quest and story system

Current state:

- `quests` is a flat record with JSON objectives and rewards
- `quest_progress` tracks completed objectives but not graph position
- `story_events`, `story_log`, and `story_items` exist, but not as a connected narrative graph
- there is no clue/revelation system
- there is no branching/failure model
- some story methods already mismatch the live schema

Observed problems:

- no quest prerequisites
- no branching outcomes
- no fail-forward logic
- no top-level story arc hierarchy
- no normalized quest-to-location/NPC/item wiring
- no plot-point or clue model
- `story_log` is flat and under-typed
- event status semantics are inconsistent (`triggered` vs `active`)
- some code expects quest stage fields that do not exist in schema

### 2. Design a complete storyline architecture

Recommended hierarchy:

`Campaign -> Act -> Chapter -> Scene -> Beat`

Implementation model:

- use `sessions` as the campaign container
- add `storylines` for arcs/acts/chapters/questlines
- add `storyline_nodes` for beats/scenes/decisions/revelations
- add `storyline_edges` for branches and conditional transitions
- add `storyline_progress` for runtime state

Recommended tables:

```sql
CREATE TABLE storylines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  parent_storyline_id INTEGER,
  title TEXT NOT NULL,
  storyline_type TEXT NOT NULL DEFAULT 'arc',
  storyline_level TEXT NOT NULL DEFAULT 'storyline',
  status TEXT NOT NULL DEFAULT 'planned',
  premise TEXT,
  stakes TEXT,
  theme TEXT,
  summary TEXT,
  primary_antagonist_npc_id INTEGER,
  primary_location_id INTEGER,
  start_node_id INTEGER,
  sequence_index INTEGER DEFAULT 0,
  variables_json TEXT NOT NULL DEFAULT '{}',
  clocks_json TEXT NOT NULL DEFAULT '{}',
  tags_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE storyline_nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  storyline_id INTEGER NOT NULL,
  quest_id INTEGER,
  plot_point_id INTEGER,
  location_id INTEGER,
  title TEXT NOT NULL,
  node_type TEXT NOT NULL,
  summary TEXT,
  content_json TEXT NOT NULL DEFAULT '{}',
  entry_conditions_json TEXT NOT NULL DEFAULT '{}',
  exit_effects_json TEXT NOT NULL DEFAULT '{}',
  fail_forward_json TEXT NOT NULL DEFAULT '{}',
  is_optional INTEGER NOT NULL DEFAULT 0,
  sequence_index INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE storyline_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  storyline_id INTEGER NOT NULL,
  from_node_id INTEGER NOT NULL,
  to_node_id INTEGER NOT NULL,
  edge_type TEXT NOT NULL DEFAULT 'default',
  label TEXT,
  priority INTEGER DEFAULT 0,
  condition_json TEXT NOT NULL DEFAULT '{}',
  effects_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);
```

### 3. Design quest wiring

Keep `quests` as player-facing contracts, but let graph progression live in storyline nodes/edges.

Add to `quests`:

- `storyline_id`
- `primary_location_id`
- `start_node_id`
- `success_node_id`
- `failure_node_id`
- `quest_type`
- `availability_rules_json`
- `failure_rules_json`
- `branching_rules_json`
- `time_limit_turns`
- `visibility`

Extend `quest_progress` with:

- `session_id`
- `current_node_id`
- `branch_path_json`
- `variables_json`
- `blocked_reasons_json`
- `failed_at`
- `failure_reason`
- `last_advanced_at`

Add normalized join tables:

- `quest_prerequisites`
- `quest_locations`
- `quest_npcs`
- `quest_story_items`

Behavior:

- quest B can require quest A completion or a plot point revelation
- quest B or C can unlock from different `storyline_edges`
- failure states can route to failure nodes or complication nodes instead of dead ends

### 4. Design plot point / clue system

Plot points are revelations; clues are discoverable sources.

Recommended tables:

```sql
CREATE TABLE plot_points (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  storyline_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  question TEXT,
  answer TEXT,
  importance TEXT NOT NULL DEFAULT 'major',
  status TEXT NOT NULL DEFAULT 'hidden',
  reveal_threshold INTEGER NOT NULL DEFAULT 1,
  fallout_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE plot_clues (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plot_point_id INTEGER NOT NULL,
  storyline_id INTEGER NOT NULL,
  source_type TEXT NOT NULL,
  source_id INTEGER NOT NULL,
  modality TEXT NOT NULL,
  clue_text TEXT NOT NULL,
  fidelity TEXT NOT NULL DEFAULT 'full',
  discover_conditions_json TEXT NOT NULL DEFAULT '{}',
  effects_json TEXT NOT NULL DEFAULT '{}',
  redundancy_group TEXT,
  is_core INTEGER NOT NULL DEFAULT 1,
  discovered_at TEXT,
  discovered_by_character_id INTEGER,
  created_at TEXT NOT NULL
);
```

Three-clue rule recommendation:

- every critical plot point should have at least 3 clues
- those clues should span at least 2 source types and preferably 3 modalities
- failed checks should reduce fidelity, not erase access forever

### 5. Design storyline NPC roles

Add `storyline_npc_roles`:

```sql
CREATE TABLE storyline_npc_roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  storyline_id INTEGER NOT NULL,
  npc_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  allegiance TEXT,
  secrets_json TEXT NOT NULL DEFAULT '[]',
  knowledge_json TEXT NOT NULL DEFAULT '[]',
  availability_rules_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(storyline_id, npc_id, role)
);
```

Suggested roles:

- patron
- witness
- gatekeeper
- rival
- antagonist
- lieutenant
- victim
- clue_holder
- false_ally
- fallback_source

### 6. What new DB tables, tool schemas, handlers, and API endpoints are needed

Add DB tables:

- `storylines`
- `storyline_nodes`
- `storyline_edges`
- `storyline_progress`
- `plot_points`
- `plot_clues`
- `plot_point_progress`
- `storyline_npc_roles`
- `quest_prerequisites`
- `quest_locations`
- `quest_npcs`
- `quest_story_items`
- `story_event_npcs`
- `story_event_items`

Extend:

- `quests`
- `quest_progress`
- `story_log`
- `story_items`

Add/extend tool schemas and handlers:

- `create_storyline`
- `update_storyline`
- `create_story_node`
- `connect_story_nodes`
- `advance_quest_progress`
- `fail_quest`
- `create_plot_point`
- `create_plot_clue`
- `discover_plot_clue`
- `assign_storyline_npc_role`
- `audit_storyline_clues`
- extend `create_quest`
- extend `create_story_event`
- extend `add_story_entry`
- extend `get_story_log`

Add API endpoints:

- `POST /sessions/{session_id}/storylines`
- `GET /sessions/{session_id}/storylines`
- `GET /storylines/{storyline_id}`
- `POST /storylines/{storyline_id}/nodes`
- `POST /storylines/{storyline_id}/edges`
- `POST /quests`
- `PATCH /quests/{quest_id}`
- `POST /quests/{quest_id}/progress/advance`
- `POST /quests/{quest_id}/fail`
- `POST /story-events`
- `POST /story-events/{event_id}/trigger`
- `POST /story-events/{event_id}/resolve`
- `POST /plot-points`
- `POST /plot-clues`
- `POST /plot-clues/{clue_id}/discover`
- `GET /sessions/{session_id}/story-log`
- `GET /storylines/{storyline_id}/audit/clues`

## Section 5 — Multi-Theme Content Library

### 1. Theme content recommendations

Audit snapshot:

- `classes.json` assumes fantasy class identity, hit dice, and spell slots
- `races.json` assumes fantasy ancestries
- `spells.json` assumes D&D-like spell structure
- `items.json` has reusable mechanics but a fantasy catalog
- prompts still mostly frame the bot as a fantasy DM even when `world_theme` changes

Recommendation: use per-theme JSON files initially, not one giant tagged file.

This allows non-fantasy themes to rename core concepts cleanly:

- `classes` -> `archetypes`
- `races` -> `origins` or `backgrounds`
- `spells` -> `powers`, `rituals`, `gadgets`, or `procedures`

### Sci-Fi

Classes/Roles:

- Spacer Warrior
- Void Scout
- Tech Specialist
- Psychic Adept
- Ship Pilot
- Corporate Agent
- Combat Medic
- Smuggler

Races/Origins:

- Baseline Human
- Voidborn Human
- Gene-Tailored Human
- Android
- Clone
- Uplift
- Alien Drifter
- Infomorph Shell

Starting Items:

- ballistic pistol
- energy carbine
- spare ammo pack
- battery cell
- medpatch
- toolkit
- datapad
- comms earpiece
- vacc suit
- ration bricks
- flashlight
- breaching charge

Spell Equivalents:

- Telepathy Surge
- Precognition Flash
- Kinetic Push
- Neural Stun
- Cloaking Field
- Drone Swarm Command
- Emergency Nanite Repair
- System Breach

Enemy Types:

- corporate security team
- pirate boarders
- feral androids
- alien swarmers
- rogue psychic
- void parasite
- mercenary exosuit trooper

Sample DM prompt opening:

You are an experienced science-fiction game master running a dangerous, player-driven campaign of frontier survival, cold corporate power, and strange psychic phenomena. Favor concrete sensory detail, hard choices, and practical consequences over fantasy heroics; track ammunition, batteries, pressure, and stress through tools whenever they matter, and always end on a tactical question, discovery, or threat that demands action.

### Horror

Classes/Roles:

- Federal Agent
- Occult Scholar
- Field Medic
- Survivor
- Investigator
- Ex-Soldier
- Medium
- Cult Defector

Races/Origins:

- Small-Town Local
- Government Operative
- Academic
- Veteran
- Street Survivor
- Occult Bloodline
- Immigrant Witness
- Blacksite Escapee

Starting Items:

- revolver
- ammo box
- flashlight
- camera
- notebook
- lockpick set
- medkit
- burner phone
- holy token
- tape recorder
- crowbar
- stimulant vial

Spell Equivalents:

- Protective Ward
- Banishing Rite
- Scry the Trace
- Compel Truth
- Blood Seal
- Dream Intrusion
- Speak with the Dead
- Circle of Containment

Enemy Types:

- cult cell
- possessed civilian
- mimic entity
- skinless stalker
- deep-one hybrid
- parasitic swarm
- avatar of the unknowable

Sample DM prompt opening:

You are an experienced horror game master running an investigation where truth is costly and survival is uncertain. Write with restraint, dread, and specificity; treat violence as sudden and ugly, treat rituals as dangerous exceptions rather than routine magic, track sanity, stress, and contamination through tools, and keep pushing the players toward revelation, denial, or collapse.

### Modern

Classes/Roles:

- Detective
- Special Operator
- Investigative Journalist
- Hacker
- Paramedic
- Con Artist
- Bounty Hunter
- Urban Mystic

Races/Origins:

- Civilian Professional
- Federal Agent
- Street Kid
- Veteran
- Trust-Fund Heir
- First-Generation Immigrant
- Rural Outsider
- Paranormal Survivor

Starting Items:

- handgun
- spare magazine
- smartphone
- laptop
- charger pack
- multitool
- lockpick set
- medkit
- flashlight
- tactical vest
- cash envelope
- fake ID

Spell Equivalents:

- Adrenaline Rush
- Tactical Scan
- Social Override
- Remote Breach
- Predictive Insight
- Healing Stimulant
- Ghost Sight
- Counter-Surveillance Pulse

Enemy Types:

- gang crew
- private security squad
- corrupt cops
- serial predator
- drone operator
- conspiracy cleaner
- paranormal intruder

Sample DM prompt opening:

You are an experienced modern-day game master running a fast, grounded campaign of investigations, shootouts, conspiracies, and uneasy alliances. Prefer contemporary language, real-world logistics, and escalating pressure; use tools for ammo, gadgets, surveillance, vehicles, and exposure, and keep every scene pointed toward a decision, complication, or leverage point.

### Steampunk

Classes/Roles:

- Airship Corsair
- Mechanist
- Clockwork Duelist
- Alchemical Savant
- Inspector
- Whisper Medium
- Sapper
- Guild Scoundrel

Races/Origins:

- Industrial Human
- Noble Lineage
- Dockborn
- Wasteland Scavenger
- Brass Automaton
- Chimera Experiment
- Aether-Touched
- Factory Orphan

Starting Items:

- steam pistol
- ammo tins
- pressure saber
- goggles
- wrench set
- alchemical grenades
- coil lantern
- respirator
- grapnel launcher
- pocket watch
- field journal
- brass badge

Spell Equivalents:

- Galvanic Arc
- Smoke Veil
- Aether Sight
- Magnetized Pull
- Clockwork Familiar
- Boiler Burst
- Phasic Step
- Spark Restoration

Enemy Types:

- clockwork hounds
- rival guild toughs
- armored constables
- rogue automata
- chimney ghouls
- alchemical mutants
- cult engineers

Sample DM prompt opening:

You are an experienced steampunk game master running a campaign of soot, brass, occult industry, and faction intrigue. Blend vivid machinery, social maneuvering, and dangerous invention; use tools to track stress, heat, pressure, gadget charges, and faction clocks, and frame scenes so the players always feel the next risk, bargain, or mechanism ready to break.

### 2. Recommend whether to use JSON files per theme or a tagged unified file

Recommendation: per-theme files first, optional tags second.

Why:

- current schemas are fantasy-shaped
- non-fantasy themes need different top-level nouns and mechanics
- editor/API/runtime complexity stays lower with clean pack boundaries

### 3. Spec out mechanical differences that need new tool handlers

Sci-fi:

- `update_ammo`
- `reload_weapon`
- `drain_battery`
- `recharge_item`
- `track_oxygen`
- `apply_radiation`
- `install_cybernetic`
- `hack_system`
- `manage_vehicle_or_ship`

Horror:

- `update_sanity`
- `update_stress`
- `trigger_panic`
- `damage_bond_or_stability`
- `apply_contamination`
- `resolve_ritual_cost`

Modern:

- `update_ammo`
- `reload_weapon`
- `use_gadget`
- `set_heat_or_exposure`
- `manage_contacts`
- `hack_system`
- `track_vehicle_state`

Steampunk:

- `update_stress`
- `advance_clock`
- `set_faction_heat`
- `consume_fuel_or_pressure`
- `repair_device`
- `use_gadget`
- `overcharge_device`

## Section 6 — End-to-End Campaign Flow Audit

### 1. Complete end-to-end flow diagram

```text
[1] Bot boots and loads cogs
    Status: ✅

[2] DM creates campaign in web dashboard
    Status: ⚠️

[3] Finalize writes session/world data to DB
    Status: ❌

[4] Players discover session in Discord
    Status: ✅

[5] Players create characters
    Status: ⚠️

[6] Players join the session
    Status: ⚠️

[7] DM starts play in a Discord channel
    Status: ✅

[8] Table talks to DM in Discord
    Status: ⚠️

[9] Exploration / quest progression / NPC interaction
    Status: ⚠️

[10] Combat starts
     Status: ⚠️

[11] Rewards, XP, quest completion, level-up
     Status: ⚠️

[12] Save / pause / resume
     Status: ⚠️

[13] Resume back into Discord DM chat
     Status: ❌
```

### 2. Per-step status

✅ Works:

- bot startup and cog loading
- session listing in Discord
- `/game begin` channel anchoring for live Discord play

⚠️ Partial:

- web campaign creator flow
- character creation (two competing entry points)
- session joining (duplicated command surfaces)
- DM chat session resolution when not channel-bound
- browser chat shared world state but separate memory model
- quest progression
- combat (two overlapping implementations)
- XP/rewards/level-up consistency
- save/resume

❌ Broken or missing:

- clean web-to-Discord handoff after campaign finalization
- automatic restoration of DM-chat channel continuity on resume
- fully canonical one-path campaign lifecycle

### 3. Prioritized list of what must be fixed/built to run one complete campaign session end-to-end

1. Fix the web-to-Discord handoff.
2. Bind resumed sessions back to the current Discord channel.
3. Standardize on one session-management surface for v1.
4. Standardize on one combat entry path for v1.
5. Fix web campaign finalization to populate session-ready state correctly.
6. Fix character gold consistency in interview creation.
7. Remove broken user guidance around rewards.
8. Unify quest/session context assumptions.

### 4. Recommended happy path

Recommended v1.0 play loop:

1. Use the web dashboard for world/session generation only.
2. Finalization creates prepared campaign data, not live play state.
3. Players create characters through one canonical character flow.
4. Players join via `/game join`.
5. DM begins the session in the actual play channel with `/game begin`.
6. Live play proceeds through `DMChat` + `ChatHandler` + tools.
7. Combat uses the same session-resolution model as DM chat.
8. Save/resume restores both session state and channel anchoring.

## Implementation Roadmap

The work should be delivered in phases that reduce architectural drift rather than adding isolated features.

### Phase 1 — Canonical Theme & Content Pack Foundation

Goal:

- make theme/profile/pack first-class and loadable

Files to modify:

- `src/database.py`
- `src/tools.py`
- `src/tool_schemas.py`
- `src/prompts.py`
- `web/api.py`
- `web/frontend/src/main.ts`

Files to create:

- `data/game_data/manifests/content_packs.json`
- `data/game_data/manifests/rules_profiles.json`
- `data/game_data/manifests/themes.json`
- `src/content_loader.py`

Deliverables:

- new session/game_state theme columns
- content-pack manifest loader
- theme management tools
- theme-aware prompt resolution

### Phase 2 — Move Fantasy Data Into Pack Structure

Goal:

- migrate current flat fantasy data into `packs/fantasy/core`

Files to create:

- `data/game_data/packs/fantasy/core/manifest.json`
- `data/game_data/packs/fantasy/core/archetypes.json`
- `data/game_data/packs/fantasy/core/ancestries.json`
- `data/game_data/packs/fantasy/core/items.json`
- `data/game_data/packs/fantasy/core/powers.json`
- `data/game_data/packs/fantasy/core/skills.json`
- `data/game_data/packs/fantasy/core/enemies.json`
- `data/game_data/packs/fantasy/core/npc_templates.json`
- `data/game_data/packs/fantasy/core/starter_kits.json`

Files to modify:

- loaders in `src/cogs/*.py`
- `src/tools.py`
- `web/api.py`

Deliverables:

- backward-compatible fantasy pack loading
- legacy flat-file compatibility layer

### Phase 3 — Location Hierarchy, Lore, Discovery, and Maps

Goal:

- turn locations into a true world model

Files to modify:

- `src/database.py`
- `src/tools.py`
- `src/tool_schemas.py`
- `web/api.py`
- `web/frontend/src/main.ts`
- `web/frontend/index.html`
- `web/frontend/styles.css`

DB additions:

- extend `locations`
- extend `location_connections`
- add `maps`
- add `map_location_nodes`
- add `lore_entries`
- add `location_lore_links`
- add `discovery_rules`
- add `discoveries`

Deliverables:

- traversable tree+graph world model
- map visualization API
- lore editor
- discovery tracking

### Phase 4 — NPC/Monster/Faction Unification

Goal:

- unify social NPCs, monsters, bosses, and faction state

Files to modify:

- `src/database.py`
- `src/tools.py`
- `src/tool_schemas.py`
- `src/cogs/npcs.py`
- `src/cogs/combat.py`
- `web/api.py`

Files to create:

- `data/game_data/packs/fantasy/core/factions.json`
- optional `src/monster_loader.py`

DB additions:

- `factions`
- `faction_memberships`
- `character_faction_reputation`
- `monster_templates`
- `boss_phases`
- `boss_abilities`

Deliverables:

- faction-aware NPCs
- monster template pipeline
- boss state and phase mechanics

### Phase 5 — Storyline Graph, Plot Points, and Quest Wiring

Goal:

- replace flat quest flow with a narrative graph

Files to modify:

- `src/database.py`
- `src/tools.py`
- `src/tool_schemas.py`
- `src/chat_handler.py`
- `src/cogs/quests.py`
- `src/cogs/dm_chat.py`
- `web/api.py`

DB additions:

- `storylines`
- `storyline_nodes`
- `storyline_edges`
- `storyline_progress`
- `plot_points`
- `plot_clues`
- `plot_point_progress`
- `storyline_npc_roles`
- `quest_prerequisites`
- `quest_locations`
- `quest_npcs`
- `quest_story_items`

Deliverables:

- branching quest logic
- clue tracking
- fail-forward story state
- proper quest/world entity wiring

### Phase 6 — Web-to-Discord Canonical Campaign Lifecycle

Goal:

- make campaign generation, session start, play, pause, and resume one coherent path

Files to modify:

- `web/api.py`
- `web/frontend/src/main.ts`
- `src/cogs/game_master.py`
- `src/cogs/sessions.py`
- `src/cogs/game_persistence.py`
- `src/cogs/dm_chat.py`
- `src/cogs/combat.py`

Deliverables:

- web-created campaigns finalize into a prepared session state
- Discord begins live play explicitly in a chosen channel
- one canonical session-management path
- one canonical combat/session resolution path
- `/resume` restores channel/session continuity

### Phase 7 — Multi-Theme Content Expansion

Goal:

- ship playable non-fantasy starter packs

Files to create:

- `data/game_data/packs/scifi/core/*`
- `data/game_data/packs/horror/core/*`
- `data/game_data/packs/modern/core/*`
- `data/game_data/packs/steampunk/core/*`

Files to modify:

- `src/prompts.py`
- `src/tools.py`
- `src/tool_schemas.py`
- `src/cogs/spells.py`
- any new theme mechanics modules

Deliverables:

- 4 playable non-fantasy starter content packs
- theme-specific DM prompt blocks
- ammo/stress/battery/pressure/faction-heat mechanics where appropriate

### Phase 8 — Audit, Compatibility, and Tooling Cleanup

Goal:

- remove duplicate paths, schema drift, and dead assumptions

Files to review broadly:

- all `src/cogs/*.py`
- `src/database.py`
- `src/tools.py`
- `src/tool_schemas.py`
- `web/api.py`
- `tests/`

Deliverables:

- remove or demote redundant command families
- fix mismatched DB/API assumptions
- update tests for narrative graph and theme packs
- add migration verification and content validation scripts

This roadmap intentionally prioritizes foundational schema and content-pack work before feature growth. Without those layers, every additional worldbuilding feature would continue to increase inconsistency across Discord commands, web APIs, tool handlers, prompts, and static data.
