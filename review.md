# rpg-dm-bot — Full Code Review & Agent Fix Plan

> **Repo:** https://github.com/mojomast/rpg-dm-bot  
> **Context:** Single-prompt Claude Opus 4.5 generation from ussybot → RPG DM bot.  
> **Purpose of this doc:** Feed this entire file to a coding agent with the instruction:  
> *"Clone https://github.com/mojomast/rpg-dm-bot, read this entire document top to bottom, then execute every fix in order. Do not skip sections. Commit after each Phase."*

> **Status note (April 17, 2026):** This is a historical review document captured before the latest hardening and worldbuilding implementation passes. Several issues described below have since been fixed, so treat this file as archived analysis rather than the current source of truth.

***

## TL;DR — What State Is This Bot In?

The bot is **~60% wired**. The architecture is sound and well-thought-out. The database schema is massive and largely correct. The LLM tool-loop is real and functional. However, a significant number of methods are either **stubs** (defined but do nothing), **broken** (wrong signatures, wrong DB calls, wrong return shapes), **unwired** (defined but never called or registered), or **spaghetti** (logic duplicated in 3 places with slightly different behavior each time).

It will **not start cleanly** today. It will crash on boot due to missing env vars, a missing `web/` dependency, and several import-time errors. Once those are fixed, it will partially work but combat, the web dashboard, proactive DM nudges, and several tool handlers will silently fail or error.

The good news: the bones are excellent. This needs a focused hardening pass, not a rewrite.

***

## Part 1 — Structural Map (What Exists)

```
rpg-dm-bot/
├── run.py                    ✅ thin entrypoint, fine
├── requirements.txt          ⚠️  missing several deps (see below)
├── src/
│   ├── bot.py                ⚠️  boot errors, missing wiring
│   ├── database.py           ⚠️  181KB — many stub methods, wrong signatures
│   ├── llm.py                ✅  mostly solid, minor issues
│   ├── tools.py              🔴  130KB — many stubs/broken handlers
│   ├── tool_schemas.py       ✅  schemas exist but some don't match tools.py
│   ├── prompts.py            ✅  good, overly large but functional
│   ├── mechanics_tracker.py  ✅  works fine as a module
│   └── cogs/
│       ├── dm_chat.py        ⚠️  core loop works, several broken paths
│       ├── combat.py         ⚠️  UI stubs, DB calls use wrong signatures
│       ├── character.py      ⚠️  partially wired
│       ├── game_master.py    ⚠️  many stubs
│       └── (others?)
├── web/                      🔴  referenced in bot.py but likely incomplete
├── data/                     ✅  SQLite file lives here
├── tests/                    ⚠️  exists but sparse
└── HANDOFF.md                ✅  Claude left good notes here — read it
```

***

## Part 2 — Broken Things (Will Crash or Error)

### 2A — Boot Crashes

**Problem 1: Missing environment variables crash on import**  
`src/bot.py` reads `os.environ` at module level with no fallback. If `.env` is missing, it raises `KeyError` before Discord even connects.

**Fix:** Wrap all `os.environ` reads in `os.getenv()` with sensible defaults and add a startup validation function that prints a clear error and exits if required vars are absent.

Required `.env` vars that MUST exist:
```
DISCORD_TOKEN=
OPENAI_API_KEY=          # or ANTHROPIC_API_KEY
DATABASE_URL=            # defaults to data/rpg.db if absent
LLM_PROVIDER=openai      # or anthropic
LLM_MODEL=gpt-4o
```

Add to `src/bot.py`:
```python
def validate_env():
    required = ["DISCORD_TOKEN"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"[FATAL] Missing required env vars: {', '.join(missing)}")
        sys.exit(1)
```
Call `validate_env()` at the top of `run.py` before anything else.

***

**Problem 2: `web/` import fails**  
`bot.py` tries to import a web dashboard module. If `web/` is incomplete (likely), this crashes on boot.

**Fix:** Wrap the web import in a try/except and make the web dashboard optional:
```python
try:
    from web.dashboard import start_dashboard
    WEB_ENABLED = True
except ImportError:
    WEB_ENABLED = False
    logger.warning("Web dashboard not available — skipping")
```

***

**Problem 3: `get_active_combat` called with wrong signature**  
In `combat.py`, `get_active_combat(interaction.channel.id)` passes only `channel_id`. But in `database.py`, the method signature is `get_active_combat(guild_id, channel_id)` — two args. This will raise `TypeError` on every combat command.

**Fix everywhere this is called:**
```python
# WRONG:
combat = await self.db.get_active_combat(interaction.channel.id)

# RIGHT:
combat = await self.db.get_active_combat(interaction.guild.id, interaction.channel.id)
```

Search the codebase: `grep -n "get_active_combat(" src/cogs/combat.py src/cogs/dm_chat.py`  
Fix every occurrence.

***

**Problem 4: `get_active_session` vs `get_user_active_session` mismatch**  
`combat.py` calls `self.db.get_active_session(guild_id)` (no user_id). This method either doesn't exist or has a different signature than what `dm_chat.py` uses (`get_user_active_session(guild_id, user_id)`).

**Fix:** Standardize. Add a `get_active_session(guild_id)` alias in `database.py` that returns the first active session for a guild (same as the fallback logic already in `dm_chat.py`).

***

### 2B — Silent Failures (Won't Crash But Won't Work)

**Problem 5: `defend_button` and `item_button` in `combat.py` are UI stubs**  
The Defend button just sends a message but never applies +2 AC anywhere. The Item button says "coming soon." These are dead UI.

**Fix (Defend):** When defend is clicked, call a new DB method `apply_status_effect(combatant_id, 'defending', duration=1)` and check for it during the next attack calculation.

**Fix (Item):** Query `db.get_inventory(char_id)` and show a `discord.ui.Select` with usable items. On selection, call `tools.use_item()`.

***

**Problem 6: Initiative order is displayed but never persisted**  
`/combat initiative` rolls and shows the order, but never saves it to the database. The next `/combat attack` has no idea whose turn it is.

**Fix:** After sorting `results`, call:
```python
await self.db.set_initiative_order(combat['id'], [r['id'] for r in results])
await self.db.set_current_turn(combat['id'], results[0]['id'])
```
Add these methods to `database.py` (update the `combat_encounters` table with a JSON `initiative_order` column and `current_combatant_id`).

***

**Problem 7: `FakeMessage` in `PlayerActionButton.callback` is spaghetti**  
In `dm_chat.py`, button callbacks construct a `FakeMessage` object to pass to `process_dm_message()`. This is a duck-typing hack that will break if `process_dm_message` ever accesses any attribute not defined on `FakeMessage`.

**Fix:** Refactor `process_dm_message` to accept explicit primitives:
```python
async def process_dm_message(self, channel, guild, author, content) -> tuple:
```
Update all call sites. Eliminates `FakeMessage` entirely.

***

**Problem 8: `PlayerActionButton` uses hardcoded action strings that don't match what the DM actually said**  
Options are always "Option 1 / Option 2 / Option 3" with canned prompts like `"{char['name']} chooses option 1."` — these don't reflect the actual narrative options the DM presented.

**Fix:** When the DM response is generated, parse it for numbered options (regex: `r'^\s*[1-3][.)]\s*(.+)'` multiline) and pass the actual option text into `GameActionsView(cog, options=[...])`. The button labels and prompts should use the real option text.

***

**Problem 9: `clear_all_guild_histories` doesn't actually filter by guild**  
The method has a comment admitting it can't filter: `# Note: We can't easily filter by guild without channel info`. So calling it with a `guild_id` does nothing — it either clears everything or nothing.

**Fix:** Change `self.histories` key structure to `(guild_id, channel_id)` tuples instead of just `channel_id`. This also fixes a potential cross-guild history leak.

```python
# Change all dict keys from:
self.histories[channel_id]
# To:
self.histories[(guild_id, channel_id)]
```

***

## Part 3 — Stubs (Defined But Empty/Placeholder)

These are methods that exist, have docstrings, but either `pass`, `return {}`, `return None`, or `raise NotImplementedError`.

### In `database.py`:

Run this to find them all:
```bash
grep -n "pass$\|return {}\|return \[\]\|raise NotImplementedError\|TODO\|FIXME\|stub" src/database.py
```

**Known critical stubs:**

| Method | Status | Fix Needed |
|--------|--------|-----------|
| `get_story_items_at_location(location_id)` | Likely stub | Query `story_items` table WHERE `location_id = ?` |
| `get_party_npcs(session_id)` | Likely stub | Query `npcs` JOIN `session_npcs` WHERE `session_id = ?` AND `in_party = 1` |
| `get_nearby_locations(location_id)` | Likely stub | Query `location_connections` WHERE `from_location_id = ?` |
| `apply_status_effect(...)` | Missing entirely | Add method + table migration |
| `set_initiative_order(...)` | Missing entirely | Add method |
| `update_combatant_hp(target_id, delta)` | Check return shape | Must return `{'new_hp': int, 'max_hp': int, 'is_dead': bool, 'name': str}` |

**For every stub method in `database.py`:** Write the SQL. The schema is already defined in the `init_db()` method — read it carefully and write SELECT/INSERT/UPDATE statements that match the actual table/column names. Do NOT invent new tables; work with what's there.

***

### In `tools.py`:

Run:
```bash
grep -n "TODO\|pass$\|not implemented\|return {\"success\": False" src/tools.py | head -60
```

**Known critical stubs or broken tool handlers:**

| Tool Name | Issue |
|-----------|-------|
| `cast_spell` | Likely stub — no spell table exists |
| `trigger_random_encounter` | Likely calls a missing DB method |
| `generate_npc_dialogue` | Probably just returns placeholder text |
| `update_weather` | DB method may not exist |
| `award_experience` | Check if it actually calls `level_up` logic when XP threshold crossed |
| `create_quest` | Verify it populates `quest_stages` too, not just `quests` |

**For each:** Trace the tool call → DB method → SQL path. If any link is broken, fix it.

***

### In `cogs/game_master.py`:

This cog likely has the most stubs. Common pattern from AI-generated code:
- Commands are defined with `@app_commands.command`
- Body is `await interaction.response.send_message("Coming soon!")`
- Or body calls a DB method that doesn't exist yet

**Fix:** For each command, implement it properly or remove it and re-add it later. Dead slash commands that error confuse users.

***

## Part 4 — Unwired Things (Exist But Never Connected)

### 4A — Proactive DM Nudges

`dm_chat.py` tracks `self.last_activity[channel_id]` and imports `PROACTIVE_DM_GUIDELINES` from `prompts.py`. But there is **no background task** that actually checks inactivity and sends a DM nudge.

**Fix:** Add a `tasks.loop` background task to `DMChat`:
```python
from discord.ext import tasks

@tasks.loop(minutes=5)
async def proactive_dm_check(self):
    now = datetime.utcnow()
    for channel_id, last_time in list(self.last_activity.items()):
        elapsed = (now - last_time).total_seconds()
        if 1800 < elapsed < 7200:  # between 30min and 2hr inactive
            channel = self.bot.get_channel(channel_id)
            if channel:
                nudge = await self._generate_proactive_nudge(channel)
                if nudge:
                    await channel.send(nudge)
                    self.last_activity[channel_id] = now
```
Start it in `cog_load` or `__init__` after the bot is ready.

***

### 4B — Web Dashboard

A `web/` directory exists. It is referenced in `bot.py`. Based on the repo structure it appears to contain a Flask or FastAPI dashboard for viewing game state. It is **not started anywhere** and likely has its own missing deps.

**Fix (short term):** Comment out the web import in `bot.py` until the dashboard is ready. Add a `WEB_ENABLED` flag.

**Fix (long term):** Wire it as an async background task using `asyncio.create_task(start_dashboard(bot))` in `bot.on_ready`.

***

### 4C — `mechanics_tracker.py` is a global singleton — dangerous

`mechanics_tracker.py` uses a module-level global tracker instance, reset with `new_tracker()` at the start of each message. But since Discord bot handlers are async and can interleave, two simultaneous requests can stomp each other's tracker state.

**Fix:** Replace the global singleton with a per-call instance. Pass the tracker object explicitly:
```python
# In dm_chat.py process_dm_message:
tracker = MechanicsTracker()  # local instance
# ... pass to tools context if needed
mechanics_text = tracker.format_all() if tracker.has_mechanics() else ""
```

***

### 4D — `tool_schemas.py` schemas not validated against `tools.py` handlers

Several tool schemas defined in `tool_schemas.py` may not have corresponding handler functions in `tools.py`, or the parameter names differ. The LLM will call a tool, `tools.execute_tool()` will dispatch by name, find no handler, and silently return an error dict.

**Fix:** Add a startup validation:
```python
# In bot.py on_ready or tools __init__:
schemas = tool_schemas.get_all_schemas()
for schema in schemas:
    name = schema['function']['name']
    if not hasattr(tools_instance, f'_{name}') and name not in tools_instance.handlers:
        logger.error(f"Tool schema '{name}' has no handler in tools.py!")
```
Fix every mismatch found.

***

## Part 5 — Spaghetti Code

### 5A — Session lookup logic duplicated in 3 places

The "find the active session" logic appears in:
1. `dm_chat.py` → `get_active_session_id()` (most complete version)
2. `dm_chat.py` → `get_game_context()` (inline version, slightly different)
3. `combat.py` → inline `get_active_session(guild_id)` call

**Fix:** Make `get_active_session_id(guild_id, user_id=None, channel_id=None)` the single source of truth in `DMChat` cog or move it to `database.py`. Delete all inline duplicates.

***

### 5B — Message chunking duplicated

The "split response into 2000-char chunks and send" logic appears in at least 3 places (`PlayerActionButton.callback`, `process_dm_message`, possibly `game_master.py`).

**Fix:** Extract to a utility function:
```python
# src/utils.py
async def send_chunked(target, content: str, view=None, max_len=2000):
    chunks = [content[i:i+max_len] for i in range(0, len(content), max_len)]
    for i, chunk in enumerate(chunks):
        kw = {'view': view} if (view and i == len(chunks) - 1) else {}
        await target.send(chunk, **kw)
```

***

### 5C — Attack logic duplicated in `combat.py` (slash command AND button)

`/combat attack` slash command and the `TargetSelectView` button both have full attack resolution logic (roll, hit check, damage, DB update). They're nearly identical but differ slightly (button uses `target_ac = 10` hardcoded; slash also uses `target_ac = 10` hardcoded).

**Fix:** Extract to a shared `resolve_attack(attacker_char, target_combatant)` async function at module level in `combat.py`. Both call sites use it.

***

### 5D — `database.py` is 181KB — needs splitting

One file with every single database method is a maintenance nightmare. Claude generated it all in one go.

**Fix (recommended structure):**
```
src/db/
├── __init__.py       # exports Database class
├── base.py           # connection, init_db, migrations
├── characters.py     # character CRUD
├── sessions.py       # session/game state
├── combat.py         # combat encounters
├── quests.py         # quests and stages
├── world.py          # locations, NPCs, items
└── inventory.py      # character inventory
```
Use a mixin pattern or composition to reassemble into one `Database` class.

***

## Part 6 — What Is Missing Entirely

These features are referenced in prompts, README, or HANDOFF but have **zero implementation**:

| Missing Feature | Where Referenced | What To Build |
|----------------|-----------------|---------------|
| Spell system | `cast_spell` tool schema | `spells` table, spell resolution logic, mana cost deduction |
| Level-up flow | `award_experience` tool | XP threshold check → stat bump prompt → announce in channel |
| Merchant/shop | NPC `is_merchant` flag | `/shop` command or DM-triggered shop UI with buy/sell |
| Save/load game | README implies it | Export session state to JSON; restore from JSON |
| Multi-server isolation | Partial | Verify ALL DB queries are scoped by `guild_id` — audit every SELECT |
| Dice expression parser | `/roll` referenced | Parse `2d6+3`, `1d20 adv`, etc. → `mechanics_tracker` output |
| Character import | README mentions it | Accept D&D Beyond JSON or simple stat block text |
| Webhook/embed image | README mentions | Location/scene image generation via DALL-E or stable diffusion |

***

## Part 7 — Requirements.txt Issues

Current `requirements.txt` is missing several packages that are imported in the code:

```
# Add these:
python-dotenv>=1.0.0     # for .env loading (used but not listed)
aiohttp>=3.9.0           # used in llm.py for HTTP calls
aiosqlite>=0.20.0        # async sqlite (verify this is what database.py uses)
flask>=3.0.0             # if web dashboard is kept
pydantic>=2.0.0          # if used in data validation
```

Also verify the Discord.py version — the code uses `app_commands` and `ui.View`, which requires `discord.py>=2.3.0`. Pin it explicitly.

***

## Part 8 — Phased Fix Plan for the Coding Agent

Execute in this exact order. Commit after each phase.

### Phase 1 — Make It Boot (30 min)
1. Add `python-dotenv` loading to `run.py` → `load_dotenv()` before anything
2. Add `validate_env()` check in `run.py`
3. Wrap web import in try/except in `bot.py`
4. Fix all `get_active_combat(channel_id)` → `get_active_combat(guild_id, channel_id)` calls
5. Fix `get_active_session` signature mismatch in `combat.py`
6. Run `python run.py` — it should connect to Discord without crashing

### Phase 2 — Fix Core DB Methods (1-2 hrs)
1. Audit every method called from `tools.py` and `cogs/` against what exists in `database.py`
2. Implement any stub or missing DB methods (write real SQL)
3. Ensure `update_combatant_hp` returns the correct shape
4. Add `set_initiative_order` and `apply_status_effect` methods
5. Add `get_active_session(guild_id)` alias

### Phase 3 — Fix Tool Handlers (1-2 hrs)
1. Run the tool schema validation check (from Part 4D above)
2. For every mismatched or stubbed tool handler in `tools.py`, implement it
3. Focus on: `award_experience`, `create_quest`, `update_weather`, `generate_npc_dialogue`
4. Verify `cast_spell` either works or returns a clear "not yet implemented" message to the LLM

### Phase 4 — Fix Spaghetti (1 hr)
1. Create `src/utils.py` with `send_chunked()`
2. Replace all inline chunking with `send_chunked()`
3. Extract `resolve_attack()` in `combat.py`
4. Centralize session lookup — delete inline duplicates
5. Fix `FakeMessage` → refactor `process_dm_message` signature

### Phase 5 — Wire Unwired Features (1-2 hrs)
1. Add proactive DM background task
2. Fix `mechanics_tracker.py` global singleton → per-call instance
3. Parse DM response for actual option text → wire into `GameActionsView`
4. Fix `clear_all_guild_histories` to use `(guild_id, channel_id)` tuple keys
5. Add startup tool schema validation logging

### Phase 6 — Combat Polish (1 hr)
1. Implement Defend button → apply status effect → check in attack resolution
2. Implement Item button → inventory select UI
3. Persist initiative order to DB after rolling
4. Use persisted initiative in attack/end-turn flow
5. Add `/combat next` command to advance turn

### Phase 7 — Missing Features (prioritize by value)
1. **Level-up flow** — highest user-facing value
2. **Dice expression parser** — needed for `/roll` to feel real
3. **Merchant shop UI** — common RPG flow
4. **Multi-server audit** — security/correctness

***

## Part 9 — Agent Prompt (Copy-Paste This)

```
You are a senior Python developer doing a hardening pass on a Discord RPG DM bot.

Clone the repository: https://github.com/mojomast/rpg-dm-bot

Read HANDOFF.md in the root first — it contains Claude's own notes about the codebase.

Then execute every fix described in this review document in Phase order (Phase 1 through Phase 7). Do not skip phases. Commit after each phase with a message like "Phase 1: boot fixes" etc.

Ground rules:
- Do NOT rewrite working code. Only fix what is broken, stubbed, or unwired.
- Do NOT change the database schema unless strictly necessary. Work with what exists.
- Keep all existing functionality. Remove nothing unless explicitly told to.
- When implementing stub DB methods, read the init_db() schema carefully and write SQL that matches the ACTUAL column names in the existing tables.
- When in doubt about behavior, add a log statement and a safe fallback rather than crashing.
- After Phase 1, run the bot and confirm it connects. After Phase 6, run a test game end-to-end: create a character, start a session, say something in the DM channel, trigger combat, end combat.
- Write tests in tests/ for any new DB methods you add.

The goal is for the bot to run a complete RPG session from character creation through combat and quest completion without any crashes, stubs, or silent failures.
```

***

## Appendix — Quick Reference: Known DB Method Signature Fixes

| Called As | Should Be |
|-----------|-----------|
| `get_active_combat(channel_id)` | `get_active_combat(guild_id, channel_id)` |
| `get_active_session(guild_id)` | `get_user_active_session(guild_id, user_id)` or new alias |
| `get_combatants(combat_id)` | Verify — check if it's `get_combat_participants(combat_id)` |
| `update_combatant_hp(id, delta)` | Verify return shape includes `name`, `new_hp`, `max_hp`, `is_dead` |
| `add_combatant(encounter_id, type, ref_id, name, hp, max_hp, init, is_player)` | Verify all positional args match DB method signature |

***

*Generated by code review of mojomast/rpg-dm-bot @ 8d4d16d — April 2026*
