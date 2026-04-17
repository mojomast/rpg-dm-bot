# RPG DM Bot — Worldbuilding & Campaign Gap Spec

## Executive Summary

`mojomast/rpg-dm-bot` already has a broad feature surface: Discord slash commands, AI DM chat, session records, characters, inventory, combat, quests, NPCs, browser chat, and campaign preview/finalization. It does not yet support a fully coherent multiplayer campaign lifecycle end to end.

This document is an implementation-planning and gap-specification document. It describes:

- what is implemented today
- what is broken or incomplete today
- what should be treated as the v1 implementation boundary
- what is explicitly deferred to later phases

The main issue is not the absence of all features. The main issue is that many systems exist in parallel, in partial form, or with schema/runtime drift:

- Theme and genre support exists mostly as generation flavor, not as first-class runtime content selection.
- Worldbuilding data exists, but location hierarchy, discovery, maps, lore, factions, and storylines are not normalized enough to drive play.
- Multiplayer play exists, but the authoritative session lifecycle is split across duplicate command surfaces and inconsistent runtime flows.
- Browser chat works, but browser, Discord, DB, tools, and web UI do not yet share one canonical campaign state contract.
- Several subsystems are defined but miswired: story items, story events, snapshots, connection APIs, quest stage reads, prompt wrappers, and some frontend contracts.

Top missing systems and must-fix gaps:

1. Canonical campaign/session architecture.
2. Canonical world theme/content-pack architecture.
3. Canonical location/map/discovery model.
4. Canonical NPC/monster/boss/faction runtime model.
5. Canonical storyline/quest/clue/reveal model.
6. Canonical save/resume/snapshot continuity model.
7. Canonical API/frontend contracts for worldbuilding and browser play.
8. Removal of duplicate or conflicting command/runtime paths.

This spec builds on `WORLDBUILDING_SPEC.md` and extends it with a brute-force wiring audit of Discord, web, DB, tools, prompts, and tests.

### Reconciliation Notes

The cross-lane reconciliation decisions for this spec are:

1. `/session` is the canonical lifecycle namespace for v1.
2. `quest_progress.current_node_id` is the canonical quest progress pointer for forward-compatible quest state.
3. Content references should use `content_pack_id` plus local IDs in v1.
4. Clue discovery should be party/session-scoped in v1.
5. v1 is a fantasy-only runtime with `fantasy_core` persisted as the default content pack.
6. Dynamic factions, storyline graph execution, maps, boss phases, and multi-theme runtime switching are planned architecture, but not all are required for minimum playable v1.

## Current State Audit

### Working foundations

- `src/database.py` already persists the core gameplay entities:
  - `sessions`, `session_participants`, `characters`, `inventory`, `quests`, `quest_progress`, `npcs`, `npc_relationships`, `combat_encounters`, `combat_participants`, `story_log`, `game_state`, `locations`, `location_connections`, `story_items`, `story_events`, `session_snapshots`, `conversation_history`, `web_identities`, and progression tables.
- `src/tools.py` and `src/tool_schemas.py` already expose a large LLM tool surface, including combat, quest, NPC, location, rest, story item/event, party NPC, and world generation tools.
- Discord command coverage is broad across `src/cogs/characters.py`, `combat.py`, `dm_chat.py`, `game_master.py`, `game_persistence.py`, `inventory.py`, `npcs.py`, `quests.py`, `sessions.py`, `skills.py`, and `spells.py`.
- `web/api.py` exposes a large REST surface for sessions, characters, quests, NPCs, locations, combat, game data, browser chat, and campaign generation/finalization.
- `web/frontend/src/main.ts` implements a real browser UI, not just a placeholder shell.
- `tests/` covers many DB methods, tool flows, DM chat batching/session behavior, and some combat behavior.

### Incomplete or unwired subsystems

The following subsystems exist but are incomplete, duplicated, stubbed, or structurally unwired:

1. Theme/genre runtime support.
2. Content-pack loading and validation.
3. Location hierarchy and region containment.
4. Travel validation and traversal logic.
5. Discovery, lore, and clue state.
6. Maps and map editor/runtime.
7. Factions and faction reputation.
8. Monster template runtime and boss mechanics.
9. Storyline graph and campaign structure.
10. Save/resume/snapshot continuity.
11. Browser/Discord parity.
12. Duplicate session/combat/character-creation flows.
13. Prompt/runtime context consistency.
14. Story item/story event schema correctness.
15. Web API/frontend contract correctness.

### Current vs Planned

| Domain | Current | Planned | v1 Scope |
|---|---|---|---|
| Session lifecycle | Duplicate `/game` and `/session` flows | one canonical `/session` lifecycle | required |
| Character creation | split across command and interview flows | one canonical campaign-bound flow | required |
| Browser chat | usable attach-to-session path | full parity with canonical lifecycle | partial in v1 |
| Theme support | preview-generation flavor only | first-class content-pack architecture | persist `fantasy_core` only in v1 |
| World model | flat locations + connections | hierarchy, lore, discovery, maps | adjacency-only travel in v1 |
| Factions | generated flavor / JSON only | relational faction runtime | deferred after v1 |
| Storyline graph | flat quests + story log | storyline nodes, edges, clues, reveals | deferred after v1 |
| Boss mechanics | ad hoc enemies | template-driven bosses and phases | deferred after v1 |
| Snapshots | schema/UI present, runtime missing | implemented save/load/checkpoint system | deferred unless needed to support pause/resume |
| Browser admin/editoring | partially implemented | full campaign/world editors | deferred after v1 |

### Classification of observed issues

#### Missing

- No first-class `world_theme`, `content_pack_id`, or `rules_profile_id` in `sessions`.
- No faction tables.
- No storyline graph tables.
- No map tables.
- No discovery/lore tables.
- No snapshot DB methods.
- No theme-management tools.
- No faction tools/endpoints/commands.
- No boss runtime model.

#### Stubbed

- Browser campaign creator editing actions in `web/frontend/src/main.ts` are placeholder toasts.
- Snapshot UI exists, but the DB implementation is absent.
- Some prompt helper wrappers in `src/prompts.py` call missing builders.

#### Unwired

- Theme preview/finalization does not switch runtime content libraries.
- Campaign finalization does not create a fully playable browser-ready or Discord-ready campaign state.
- `/resume` restores some DB state but does not restore DM chat channel binding.
- `location_connections` exists, but travel and move-party logic do not actually enforce or traverse it.
- `conversation_history` exists, but Discord DM chat does not persist into it.

#### Broken

- `story_items` DB helper methods target wrong column names.
- `story_events` DB helper methods target wrong column names and wrong status semantics.
- Some web endpoints call missing DB methods or wrong DB signatures.
- DM chat and chat handler read `quest['current_stage']`, but that field does not exist.
- `game_state` consumers expect `current_location_id`, but schema only stores `current_location` text.

#### Duplicated

- Session lifecycle split between `/game ...` in `src/cogs/game_master.py` and `/session ...` in `src/cogs/sessions.py`.
- Combat flow split between `src/cogs/combat.py` and `src/tools.py`.
- Character creation split between `src/cogs/characters.py` and interview/game-master flow in `src/cogs/game_master.py`.
- NPC template logic split across hardcoded data and `data/game_data/npc_templates.json`.
- Prompt construction split across `src/prompts.py`, `src/llm.py`, `src/chat_handler.py`, and `src/cogs/dm_chat.py`.

## Theme and Genre Architecture

This section describes the target architecture. For minimum playable v1, the runtime should persist `world_theme='fantasy'` and `content_pack_id='fantasy_core'`, but runtime switching and non-fantasy parity are deferred.

### What exists

- `web/api.py` campaign preview/finalization accepts theme inputs such as `world_theme`, `magic_level`, `technology_level`, and `tone`.
- `web/api.py` and `web/frontend/src/main.ts` expose templates for fantasy, sci-fi, horror, and steampunk flavored campaign generation.
- `src/prompts.py` world-generation prompts interpolate theme-flavored text.
- `data/game_data/` contains a real content library.

### What is missing

- Runtime theme identity is not first-class in the DB.
- Static content remains a single fantasy-first root library.
- No content pack manifests or pack loader exist.
- No tool, API, or frontend surface switches runtime content by theme.
- Prompts remain fantasy-default in many live play paths.

### Evidence

- `sessions` only stores `setting` and `world_state` in `src/database.py`.
- `game_state` stores generic `game_data` and `dm_notes`, not theme state.
- `web/api.py` finalization stores theme/factions mostly inside JSON blobs.
- `classes.json`, `races.json`, `spells.json`, `skills.json`, `items.json`, `enemies.json`, and `starter_kits.json` are overwhelmingly fantasy-centric.
- `src/tools.py` has generation tools with freeform `theme` strings, but no first-class theme/content-pack management handlers.

### Required architecture

#### Session-level theme identity

Add to `sessions`:

- `world_theme TEXT NOT NULL DEFAULT 'fantasy'`
- `genre_family TEXT NOT NULL DEFAULT 'fantasy'`
- `content_pack_id TEXT NOT NULL DEFAULT 'fantasy_core'`
- `rules_profile_id TEXT NOT NULL DEFAULT 'd20_fantasy'`
- `theme_config TEXT NOT NULL DEFAULT '{}'`

Add to `game_state`:

- `current_location_id INTEGER`
- `active_content_pack_id TEXT`
- `theme_state TEXT NOT NULL DEFAULT '{}'`
- `allowed_content_packs TEXT NOT NULL DEFAULT '[]'`

V1 note:

- `world_theme` and `content_pack_id` are mandatory in v1.
- `genre_family`, `rules_profile_id`, `theme_config`, `active_content_pack_id`, `theme_state`, and `allowed_content_packs` can be added now if convenient, but only `fantasy_core` needs to be actively supported in v1 runtime behavior.

#### Content-pack filesystem

Replace flat-only runtime loading with:

```text
data/game_data/
├── manifests/
│   ├── themes.json
│   ├── content_packs.json
│   └── rules_profiles.json
├── shared/
│   └── common/
└── packs/
    ├── fantasy/core/
    ├── scifi/core/
    ├── horror/core/
    ├── modern/core/
    └── steampunk/core/
```

Each pack must define its own:

- archetypes/classes
- origins/races/backgrounds
- items
- powers/spells
- skills
- enemies
- npc templates
- starter kits
- world/location templates
- factions

### Minimum viable content per theme

Each theme needs at least:

- 4 to 6 playable archetypes
- 4 to 6 origins/backgrounds
- 20 to 40 core items
- 15 to 30 powers/spells/abilities where appropriate
- 10 to 15 enemies
- starter kits
- NPC templates
- world/location templates

Fantasy is closest to viable, but still internally inconsistent. `classes.json` does not align with `spells.json`, `skills.json`, and `starter_kits.json` for classes like `warlock` and `druid`.

### Theme-specific implementation requirements

- All character creation options must resolve through `content_pack_id`.
- All item, spell/power, skill, enemy, and starter-kit lookup must be pack-scoped.
- DM prompt construction must use session theme and rules profile.
- Content validation must reject fantasy-only entities in non-fantasy packs unless explicitly shared.

V1 requirement:

- All runtime reads must consistently resolve against `fantasy_core` rather than the current root flat files once the migration is complete.

## Worldbuilding Architecture

This section describes the target world model. Minimum playable v1 only requires connected-location travel with canonical `current_location_id`, not full hierarchy/maps/lore/discovery execution.

### What exists

- `locations` and `location_connections` tables exist.
- Characters and NPCs can have locations.
- There are location CRUD methods and endpoints.
- `explore_location` exists in DB, tools, and prompts.
- Browser and Discord can display some location information.

### What is missing

- Real containment hierarchy beyond a mostly unused `parent_location_id`.
- Real map model.
- Real lore model.
- Real discovery model.
- Real travel logic.
- World editor capable of hierarchy, maps, lore, discovery, and occupants.

### Current gaps and contradictions

- `parent_location_id` exists in schema but is not meaningfully exposed in tools, web forms, or runtime flows.
- `create_location()` and `update_location()` in `src/database.py` mis-map `points_of_interest` into `connected_locations` even though a `points_of_interest` column exists.
- `move_party_to_location()` in `src/tools.py` updates text game state, not actual per-character movement.
- Travel does not validate adjacency against `location_connections`.
- Campaign finalization stores preview location connection/POI data into `hidden_secrets` JSON instead of normalized structures.

### Required location model

Use one containment tree plus one traversal graph.

#### Containment tree

Represent:

- world
- plane
- continent/ocean
- nation/realm
- region/province
- settlement/site
- district/zone
- structure/interior
- room/sublocation

Add to `locations`:

- `slug`
- `root_location_id`
- `hierarchy_kind`
- `canonical_path`
- `depth`
- `sort_order`
- `tags`
- `dm_notes`
- `is_hidden`
- `discoverability`
- `map_default_id`

#### Traversal graph

Extend `location_connections` with:

- `connection_type`
- `distance_text`
- `travel_mode`
- `lock_state`
- `map_path_data`
- `discovery_rule_id`

### Required map model

Add tables:

- `maps`
- `map_location_nodes`
- optional `map_layers`

V1 note:

- `maps` and `map_location_nodes` are deferred after v1.
- v1 should reuse `locations` and `location_connections` with adjacency validation only.

Each map node must support:

- `location_id`
- coordinates
- label
- reveal state metadata
- visual style metadata

### Required lore and discovery model

Add tables:

- `lore_entries`
- `location_lore_links`
- `discovery_rules`
- `discoveries`

V1 note:

- Lore and discovery systems are deferred after v1.
- If clue-like behavior is needed in v1, it should remain lightweight and quest/objective-driven rather than implemented as the full target model.

Support reveal of:

- hidden exits
- hidden child locations
- rumors
- secrets
- hazards
- clues
- map nodes

### Web editor requirements

The world editor must support:

- tree view for hierarchy
- graph editor for connections
- map editor for node placement
- lore authoring and visibility
- discovery rule authoring
- occupant management for NPCs, items, and story events

## NPC / Monster / Boss / Faction Architecture

This section describes the target NPC/monster/faction architecture. Minimum playable v1 only requires reliable enemy stats in combat and simple NPC persistence; dynamic factions and boss phases are deferred.

### What exists

- Social NPCs are persisted in `npcs`.
- Per-character NPC reputation exists in `npc_relationships`.
- Party companion support exists as extra columns on `npcs`.
- Enemy templates exist in `data/game_data/enemies.json`.
- Combat encounter persistence exists in `combat_encounters` and `combat_participants`.
- Discord and tools support basic NPC CRUD and ad hoc enemy spawning.

### What is missing

- Monster template runtime normalization.
- Faction persistence.
- Character-to-faction reputation.
- NPC-to-faction membership.
- Boss phase state.
- Elite/minion taxonomy.
- Enemy template-driven combat spawning.

### Current gaps and contradictions

- `src/tools.py::_add_enemy()` and `src/cogs/combat.py` spawn enemies ad hoc and do not persist actual template stats.
- `src/tools.py::_roll_attack()` uses a hardcoded target AC instead of real monster stats.
- `src/tools.py::_generate_encounter()` reads `enemies.json` in the wrong shape.
- `src/tools.py::_generate_key_npcs()` expects the wrong shape from `npc_templates.json`.
- Factions generated in `web/api.py` are stored only in JSON blobs, not in relational tables.

### Required taxonomy

Add neutral runtime fields:

- `actor_kind`: `npc`, `companion`, `monster`, `boss`
- `encounter_tier`: `minion`, `standard`, `elite`, `boss`
- `combat_role`: `brute`, `skirmisher`, `artillery`, `controller`, `support`, `leader`
- `creature_family`
- `origin_type`: `persistent_npc`, `party_companion`, `monster_template`, `ad_hoc_encounter`

### Required DB additions

Add tables:

- `factions`
- `faction_memberships`
- `character_faction_reputation`
- `monster_templates`
- `boss_phases`

Extend `npcs` with:

- `actor_kind`
- `role`
- `faction_id`
- `faction_role`
- `goals`
- `secrets`
- `tags`
- `challenge_rating`
- `actions`
- `traits`

Extend `combat_participants` with:

- `template_id`
- `combat_stats`
- `resource_state`
- `phase_state`
- `is_boss`
- `encounter_tier`
- `armor_class`

V1 note:

- The only mandatory additions for v1 in this domain are the fields needed to stop ad hoc enemy combat drift, especially `armor_class` and stable combat stat snapshots or equivalent runtime fixes.
- `factions`, `faction_memberships`, `character_faction_reputation`, `monster_templates`, and `boss_phases` are deferred after v1 unless implementation chooses to land them early behind unused or lightly used surfaces.

### Boss mechanics spec

Bosses must support:

- multiple phases
- HP threshold triggers
- scripted transitions
- per-phase actions and traits
- legendary actions
- lair/environment actions
- reinforcement waves

Minimum runtime operations:

- spawn monster from template
- start boss encounter
- advance boss phase
- use legendary action
- trigger lair action
- inspect stat block

### Faction system spec

Factions must affect:

- quest availability
- merchant pricing/inventory
- travel safety/access
- NPC disposition defaults
- recruitment and betrayal pressure
- story branch outcomes

Personal NPC reputation in `npc_relationships` should remain separate from faction reputation.

## Storyline and Quest Architecture

This section describes the target narrative architecture. Minimum playable v1 should keep quests linear and objective-driven, while adopting a forward-compatible quest progress pointer.

### What exists

- `quests` and `quest_progress` provide a flat quest model.
- `story_log` records flat campaign history.
- `story_items` and `story_events` exist conceptually.
- Prompts already describe richer quest planning, branching, and failure ideas.

### What is missing

- Campaign arc/chapter/scene/beat graph.
- Branching quest structure.
- Failure-state modeling.
- Clue-to-reveal model.
- Strong normalized links between story, NPCs, locations, items, and factions.

### Current gaps and contradictions

- `get_quest_stages()` synthesizes fake stages from objective arrays, but chat/UI read a nonexistent `current_stage` field.
- `story_items` helper methods target wrong columns like `type` and `discovered` instead of real schema columns.
- `story_events` helper methods target wrong columns like `type` and `triggers` and use mismatched status logic.
- `story_log` is under-typed and cannot serve as the canonical narrative graph.

### Required narrative model

Add tables:

- `storylines`
- `storyline_nodes`
- `storyline_edges`
- `storyline_progress`
- `plot_points`
- `plot_clues`
- `quest_prerequisites`
- `quest_npcs`
- `quest_locations`
- `quest_story_items`

V1 note:

- `storylines`, `storyline_nodes`, `storyline_edges`, `storyline_progress`, `plot_points`, `plot_clues`, and the quest link tables are deferred after v1.
- v1 should instead fix quest state drift and use `quest_progress.current_node_id` as a forward-compatible field, even if the runtime still behaves like a linear staged quest system.

### Required quest model extensions

Extend `quests` with:

- `storyline_id`
- `primary_location_id`
- `start_node_id`
- `success_node_id`
- `failure_node_id`
- `quest_type`
- `availability_rules_json`
- `branching_rules_json`
- `failure_rules_json`

Extend `quest_progress` with:

- `session_id`
- `current_node_id`
- `branch_path_json`
- `variables_json`
- `failed_at`
- `failure_reason`
- `last_advanced_at`

V1 note:

- `quest_progress.current_node_id` is mandatory in v1.
- `quests.start_node_id`, `success_node_id`, `failure_node_id`, and the broader branching/failure JSON fields are optional in v1 and become required once the storyline graph is implemented.

### Clue and reveal system

Plot truths should be modeled as `plot_points`.
Discoverable evidence should be modeled as `plot_clues`.

Clues may originate from:

- NPC dialogue
- locations
- lore entries
- story items
- story events

Required behavior:

- multiple clues can point to one plot point
- reveals unlock when evidence thresholds are met
- failed checks should cost time or fidelity, not erase the storyline

## Multiplayer Campaign Flow

### Current end-to-end flow map

#### Discord path today

1. Bot starts via `run.py` and `src/bot.py`.
2. DM may create/play via `/game ...` in `src/cogs/game_master.py` or `/session ...` in `src/cogs/sessions.py`.
3. Players may join session via session/game flows.
4. Character creation may happen via `/character create` or interview/game-master flow.
5. DM begins play via `/game begin` or session/start path.
6. DM chat runs via `src/cogs/dm_chat.py` and `src/chat_handler.py`.
7. Combat may be run via slash commands in `src/cogs/combat.py` or tool-based orchestration in `src/tools.py`.
8. Save/resume may happen via `/save`, `/resume`, `/game pause`, and `/game begin`.

#### Browser path today

1. User opens dashboard.
2. Browser mints web identity via `POST /api/chat/identity`.
3. User selects session and character in browser chat.
4. Browser sends message to `POST /api/chat`.
5. API loads some persisted history and session state, then calls chat handler.
6. Browser renders DM response plus side panels.

### Primary multiplayer flow gaps

#### Session lifecycle duplication

- `/game ...` and `/session ...` both manage campaign state.
- They are not one canonical lifecycle.

#### Character creation duplication

- `/character create` and interview/game-master creation produce different initialization behavior.
- Gold, gear, and spell initialization are not consistent.

#### Combat duplication

- Slash-command combat and tool-driven combat differ in participant setup and reward handling.

#### Quest lifecycle drift

- Quest accept/progress/complete semantics are inconsistent across DB, tools, and cogs.
- Rewarding the primary visible flow is incomplete.

#### Resume continuity failure

- `/game begin` behaves like fresh start, not resume.
- `/resume` restores only partial state and does not rebind DM chat channel history.

#### Multiplayer actor-context issue

- Batched chat processing still executes tools with first-player-centric implicit context.

### Required campaign lifecycle

Canonical v1 Discord lifecycle:

1. Create campaign/session.
2. Join campaign.
3. Create/select one character per participant for that campaign.
4. Run session zero and assign starting location/content pack.
5. Begin campaign in one play channel bound to the session.
6. Run shared DM chat against canonical session state.
7. Run combat through one authoritative combat flow.
8. Advance quests/storyline through one authoritative quest flow.
9. Save/pause with full continuity.
10. Resume in the same or reassigned play channel without state reset.
11. Complete campaign through storyline/quest resolution.

## Missing Wiring and Broken Integrations

### Prompt and chat context breakages

- `src/prompts.py` contains stale wrapper methods that call missing builder functions or wrong signatures.
- Live prompt assembly is split across multiple paths with different context richness.
- Fantasy-default wording still leaks into live play and generation.
- `quest['current_stage']` is read where no such field exists.
- `game_state.current_location_id` is expected where schema only stores text `current_location`.

### DB helper/schema breakages

- `story_items` helpers target wrong column names.
- `story_events` helpers target wrong column names and wrong status assumptions.
- location POI persistence is mapped into the wrong field.
- list fetch helpers and single fetch helpers often return different shapes for JSON-ish data.

### API/DB contract breakages

- Some endpoints call missing DB methods like `get_session_characters`, `get_npcs_by_session`, `get_npcs_by_guild`.
- Some endpoints call DB methods with wrong signatures, especially location connect and event resolve paths.
- Snapshot endpoints exist without DB implementations.

### Frontend/API contract breakages

- Frontend calls endpoints that do not exist, especially bulk item/spell update paths.
- Some frontend forms reference DOM containers or modals that do not exist.
- Save Points UI is present without backend support.
- Campaign creator review/edit actions are placeholders.

### Session continuity breakages

- Channel-to-session binding is memory-only in Discord DM chat.
- Discord conversation history is not persisted to DB.
- `last_played` update semantics are inconsistent.
- Auto story logging can target the wrong active session in multi-session guilds.

### Implementation Status

- ✅ COMPLETE: `sessions.world_theme` implemented in `src/database.py`
- ✅ COMPLETE: `sessions.content_pack_id` implemented in `src/database.py`
- ✅ COMPLETE: `sessions.primary_channel_id` implemented in `src/database.py`
- ✅ COMPLETE: `sessions.last_active_channel_id` implemented in `src/database.py`
- ✅ COMPLETE: `game_state.current_location_id` implemented in `src/database.py`
- ✅ COMPLETE: `quest_progress.current_node_id` implemented in `src/database.py`
- ✅ COMPLETE: `quest_progress.session_id` and `last_advanced_at` implemented in `src/database.py`
- ✅ COMPLETE: `story_items` helper/schema drift repaired in `src/database.py`
- ✅ COMPLETE: `story_events` helper/schema drift repaired in `src/database.py`
- ✅ COMPLETE: snapshot DB methods implemented in `src/database.py`
- ✅ COMPLETE: broken API routes for session characters, NPC listing, event resolve, and location connect repaired in `web/api.py`
- ✅ COMPLETE: quest stage consumers switched off direct `quest['current_stage']` reads in `src/chat_handler.py` and `src/cogs/dm_chat.py`
- ✅ COMPLETE: additive `fantasy_core` content-pack scaffold created under `data/game_data/packs/fantasy/core`
- ✅ COMPLETE: content-pack manifest and loader added in `data/game_data/manifests/content_packs.json` and `src/content_packs.py`
- ✅ COMPLETE: pack-aware read paths added for core game data in `web/api.py` and `src/tools.py`
- ✅ COMPLETE: canonical `/session resume` command added in `src/cogs/sessions.py`
- ✅ COMPLETE: DB-backed session channel binding helpers added in `src/database.py`
- ✅ COMPLETE: `DMChat` now prefers DB-backed session-channel binding over in-memory history
- ✅ COMPLETE: campaign finalization now persists canonical `world_theme`, `content_pack_id`, starting `current_location_id`, normalized `locations.points_of_interest`, and `location_connections` in `web/api.py`
- ✅ COMPLETE: browser chat bootstrap endpoint now returns session continuity state for messages, participants, combat, and location context in `web/api.py`
- ✅ COMPLETE: browser chat frontend now hydrates from `/api/chat/bootstrap` in `web/frontend/src/main.ts`
- ✅ COMPLETE: browser chat now supports minimal fresh-session onboarding by creating and attaching a session-bound browser character in `web/api.py` and `web/frontend/src/main.ts`
- ✅ COMPLETE: `/resume` now resolves the target session and delegates through canonical `/session resume` lifecycle handling in `src/cogs/game_persistence.py`
- ✅ COMPLETE: resumed `/game begin` now preserves saved `current_scene`, `current_location`, and `current_location_id` instead of overwriting them in `src/cogs/game_master.py`
- ✅ COMPLETE: `/game begin` and `/game pause` now act as compatibility wrappers over canonical `/session start` and `/session pause` in `src/cogs/game_master.py`
- ✅ COMPLETE: API continuity regressions added for campaign finalize and browser chat bootstrap/validation in `tests/test_web_phase7.py`
- ⚠️ PARTIAL: `/game` lifecycle compatibility wrappers still exist for status/end/help surfaces, but start/pause/resume now route through canonical session lifecycle handling
- ⚠️ PARTIAL: snapshot UI/API contract is now backed by DB methods, but full snapshot restore semantics remain limited to v1 game-state restoration
- ⚠️ PARTIAL: persistent Discord channel/session rebinding is not fully implemented yet

## Missing DB Schema and Migrations

### New tables required

- `factions`
- `faction_memberships`
- `character_faction_reputation`
- `monster_templates`
- `boss_phases`
- `maps`
- `map_location_nodes`
- `lore_entries`
- `location_lore_links`
- `discovery_rules`
- `discoveries`
- `storylines`
- `storyline_nodes`
- `storyline_edges`
- `storyline_progress`
- `plot_points`
- `plot_clues`
- `quest_prerequisites`
- `quest_npcs`
- `quest_locations`
- `quest_story_items`

V1 note:

- This list is the target architecture list, not the minimum v1 schema list.
- Mandatory v1 schema additions are intentionally smaller and are defined in `## Minimum Playable v1` below.

### Column additions required

#### `sessions`

- `world_theme`
- `genre_family`
- `content_pack_id`
- `rules_profile_id`
- `theme_config`
- `primary_channel_id`
- `last_active_channel_id`

#### `game_state`

- `current_location_id`
- `active_content_pack_id`
- `theme_state`
- `allowed_content_packs`
- `current_storyline_id`
- `current_story_node_id`

#### `locations`

- `slug`
- `root_location_id`
- `hierarchy_kind`
- `canonical_path`
- `depth`
- `sort_order`
- `tags`
- `dm_notes`
- `is_hidden`
- `discoverability`
- `map_default_id`

#### `location_connections`

- `connection_type`
- `distance_text`
- `travel_mode`
- `lock_state`
- `map_path_data`
- `discovery_rule_id`

#### `npcs`

- `actor_kind`
- `role`
- `faction_id`
- `faction_role`
- `goals`
- `secrets`
- `tags`
- `challenge_rating`
- `actions`
- `traits`

#### `combat_participants`

- `template_id`
- `combat_stats`
- `resource_state`
- `phase_state`
- `is_boss`
- `encounter_tier`
- `armor_class`

#### `quests`

- `storyline_id`
- `primary_location_id`
- `start_node_id`
- `success_node_id`
- `failure_node_id`
- `quest_type`
- `availability_rules_json`
- `branching_rules_json`
- `failure_rules_json`

#### `quest_progress`

- `session_id`
- `current_node_id`
- `branch_path_json`
- `variables_json`
- `failed_at`
- `failure_reason`
- `last_advanced_at`

### Corrective migrations required

1. Fix `story_items` helper/schema drift.
2. Fix `story_events` helper/schema drift.
3. Add `game_state.current_location_id` and backfill from location names where possible.
4. Fix `locations.points_of_interest` storage/write paths.
5. Backfill `sessions.world_theme` and `content_pack_id` from `setting` and `world_state`.
6. Normalize existing generated factions from JSON blobs into faction tables where possible.

## Missing Tools / Slash Commands / UI / API Endpoints

### Missing tool schemas and handlers

#### Theme/content-pack tools

- `get_session_theme`
- `set_session_theme`
- `list_content_packs`
- `switch_content_pack`
- `get_theme_rules`
- `get_theme_content`
- `validate_theme_content`

#### World/map/discovery tools

- `get_location_tree`
- `move_location_node`
- `get_map`
- `create_map`
- `update_map_node`
- `discover_location`
- `discover_connection`
- `create_lore_entry`
- `reveal_lore_entry`

#### NPC/monster/faction tools

- `spawn_monster`
- `get_stat_block`
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

#### Storyline tools

- `create_storyline`
- `advance_storyline_node`
- `get_storyline_state`
- `create_plot_point`
- `record_clue_discovery`
- `reveal_plot_point`

### Missing slash commands

#### Canonical session/campaign

- choose one canonical namespace and deprecate the duplicate one
- add explicit `resume campaign` or equivalent canonical resume entrypoint

#### NPC/faction

- `/npc recruit`
- `/npc dismiss`
- `/npc loyalty`
- `/npc relationship`
- `/faction list`
- `/faction standing`
- `/faction modify`

#### World/story

- `/location tree`
- `/location connect`
- `/location map`
- `/lore view`
- `/storyline current`
- `/storyline advance`
- `/clue list`

#### Combat/boss

- `/combat spawn-template`
- `/combat boss-phase`
- `/combat legendary`

### Missing web endpoints

#### Theme/content

- `GET /api/themes`
- `GET /api/content-packs`
- `POST /api/sessions/{id}/theme`
- `POST /api/sessions/{id}/content-pack`

#### World/maps/lore/discovery

- `GET /api/locations/tree`
- `POST /api/locations/{id}/move`
- canonical `GET/POST/PATCH/DELETE /api/location-connections`
- `GET/POST /api/locations/{id}/lore`
- `GET/POST /api/locations/{id}/discovery-rules`
- `POST /api/locations/{id}/discover`
- `GET/POST /api/maps`
- `GET/PATCH /api/maps/{id}`
- `POST /api/maps/{id}/nodes`

#### NPC/factions/monsters

- `GET/POST/PATCH /api/factions`
- `GET/POST /api/factions/{id}/members`
- `GET/PATCH /api/characters/{id}/factions/{faction_id}`
- `GET /api/monsters`
- `GET /api/monsters/{template_id}`

#### Storyline

- `GET/POST /api/storylines`
- `GET/PATCH /api/storylines/{id}`
- `POST /api/storylines/{id}/advance`
- `GET/POST /api/plot-points`
- `POST /api/plot-clues/{id}/discover`

#### Save/snapshot continuity

- keep existing snapshot routes only after DB implementation exists
- add explicit channel/session binding endpoints if browser and Discord must share canonical continuity

### Missing or incomplete UI surfaces

- campaign creator section/item editing must become real, not placeholder
- location editor must support hierarchy, maps, lore, and discovery
- faction management page
- storyline editor page
- monster template/boss editor page
- snapshot UI must be hidden or completed until backend exists
- browser chat onboarding for fresh campaigns must create or attach valid participant characters

## Minimum Playable v1

### Scope

The minimum playable v1 should prioritize one coherent multiplayer fantasy campaign flow first, while laying only the minimum schema foundation needed to avoid rework.

Authoritative v1 boundary:

- 1 DM + 4 players
- 1 character per player, bound to one session
- 1 `fantasy` campaign using `fantasy_core`
- 3 linked but effectively linear quests
- connected-location travel using `location_connections`
- one canonical Discord play flow and browser continuation flow
- pause/resume continuity without state reset

### Required for v1

1. One canonical campaign/session lifecycle.
2. One canonical character creation flow.
3. One canonical DM chat session binding model.
4. One canonical combat flow with proper reward application.
5. One canonical quest flow with working objective/stage semantics.
6. Working save/pause/resume continuity.
7. Fixed story item and story event persistence.
8. Fixed location/travel/current-location wiring.
9. Browser chat parity for ongoing play, not necessarily full campaign administration.
10. `sessions` persists `world_theme='fantasy'` and `content_pack_id='fantasy_core'`.

Mandatory v1 schema additions:

1. `sessions.primary_channel_id`
2. `sessions.last_active_channel_id`
3. `sessions.world_theme`
4. `sessions.content_pack_id`
5. `game_state.current_location_id`
6. `quest_progress.current_node_id`

Mandatory v1 product decisions:

1. `/session` is the canonical lifecycle namespace.
2. `/game` becomes compatibility/UI sugar only and must not own different state transitions.
3. Browser support in v1 means attaching to an existing playable session, not full campaign administration.
4. Quest progression remains linear/objective-based in behavior, even if stored with a forward-compatible node pointer.

### Explicit v1 happy path

1. DM creates campaign.
2. Players join campaign.
3. Players create/select characters for that campaign.
4. Session stores canonical theme/content-pack and starting location.
5. DM starts campaign in one play channel.
6. All DM chat resolves against that session and correct acting character.
7. Party can move between connected locations.
8. Party can fight encounters with proper enemy stats and rewards.
9. Party can accept, progress, and complete quests with rewards.
10. DM can pause/save and later resume without resetting the campaign.
11. Browser chat can attach to the same session state and continue play.

### Out of scope for v1

- Full map editor polish.
- Full multi-theme runtime parity across all genres.
- Dynamic faction gameplay and faction reputation systems.
- Storyline graph execution, clue/reveal systems, and branching campaign graph runtime.
- Advanced boss/lair systems.
- Map, lore, and discovery runtime/editor systems.
- Full snapshot management UI and archive tooling unless required to satisfy pause/resume continuity.
- Fully visual storyline graph editor.

## Implementation Roadmap

### Phase 1: Stabilize broken wiring

Priority: critical

- Fix `story_items` DB helper/schema mismatch.
- Fix `story_events` DB helper/schema mismatch and status semantics.
- Fix prompt wrapper breakages in `src/prompts.py`.
- Fix `quest['current_stage']` drift by choosing a canonical quest stage representation.
- Add `game_state.current_location_id` and use it in chat/runtime.
- Fix `locations.points_of_interest` write paths.
- Fix broken API endpoints calling missing DB methods or wrong signatures.
- Hide or disable snapshot UI until DB support exists, or implement it in the same phase.

### Phase 2: Unify campaign lifecycle

Priority: critical

- Choose one canonical session/campaign command surface.
- Choose one canonical character creation flow.
- Choose one canonical combat flow.
- Separate `begin new campaign` from `resume campaign`.
- Persist Discord channel binding in DB.
- Persist Discord chat continuity or canonical rolling summaries in DB.

### Phase 3: Theme/content-pack foundation

Priority: high

- Add session/game_state theme fields.
- Introduce content-pack manifests and loader.
- Migrate current fantasy data into `fantasy/core`.
- Make character creation, tools, prompts, and game-data endpoints pack-aware.

### Phase 4: World model foundation

Priority: high

- Normalize location hierarchy.
- Normalize traversal graph.
- Add current location ID-based movement rules.
- Add discovery and lore tables.
- Add minimal map tables.

### Phase 5: NPC/monster/faction foundation

Priority: high

- Normalize monster templates.
- Make combat spawns template-driven.
- Add factions and faction reputation.
- Add NPC faction membership.
- Add foundational boss phase state.

### Phase 6: Storyline graph foundation

Priority: high

- Add storyline, node, edge, and progress tables.
- Extend quests to attach to storyline nodes.
- Add clue and reveal model.
- Connect quests to NPCs, locations, items, and factions.

### Phase 7: Web and browser parity

Priority: medium

- Bring frontend/API contracts into exact alignment.
- Complete campaign creator editing flows.
- Add world/faction/storyline admin panels.
- Make browser chat attach cleanly to playable campaigns.

### Phase 8: Test hardening

Priority: critical

Add coverage for:

- theme persistence and content-pack loading
- story item/event CRUD against real schema
- location hierarchy and connection traversal
- session/channel continuity and resume
- snapshot create/load/delete
- API contract tests for campaign finalize, browser chat, snapshots, locations, NPCs, events
- multiplayer batched tool execution with per-actor context

### Recommended implementation order inside each phase

1. DB schema and migrations
2. DB methods
3. tools and tool schemas
4. chat/prompt integration
5. Discord commands
6. API endpoints
7. frontend
8. tests
