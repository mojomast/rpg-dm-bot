"""
RPG DM Bot - Database Models
SQLite database with aiosqlite for async operations
Handles characters, inventory, quests, NPCs, combat, and sessions
"""

import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, db_path: str = "data/rpg.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
    async def init(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # ================================================================
            # CHARACTERS TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    session_id INTEGER,
                    name TEXT NOT NULL,
                    race TEXT NOT NULL,
                    class TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    experience INTEGER DEFAULT 0,
                    hp INTEGER NOT NULL,
                    max_hp INTEGER NOT NULL,
                    mana INTEGER DEFAULT 0,
                    max_mana INTEGER DEFAULT 0,
                    strength INTEGER DEFAULT 10,
                    dexterity INTEGER DEFAULT 10,
                    constitution INTEGER DEFAULT 10,
                    intelligence INTEGER DEFAULT 10,
                    wisdom INTEGER DEFAULT 10,
                    charisma INTEGER DEFAULT 10,
                    gold INTEGER DEFAULT 0,
                    backstory TEXT,
                    current_location_id INTEGER,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (current_location_id) REFERENCES locations(id)
                )
            """)
            
            # ================================================================
            # INVENTORY TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    is_equipped INTEGER DEFAULT 0,
                    slot TEXT,
                    properties TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (character_id) REFERENCES characters(id)
                )
            """)
            
            # ================================================================
            # QUESTS TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    session_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    objectives TEXT DEFAULT '[]',
                    rewards TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'available',
                    difficulty TEXT DEFAULT 'medium',
                    quest_giver_npc_id INTEGER,
                    dm_notes TEXT,
                    dm_plan TEXT,
                    created_by INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            
            # ================================================================
            # QUEST PROGRESS TABLE (per character)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quest_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quest_id INTEGER NOT NULL,
                    character_id INTEGER NOT NULL,
                    objectives_completed TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'active',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (quest_id) REFERENCES quests(id),
                    FOREIGN KEY (character_id) REFERENCES characters(id),
                    UNIQUE(quest_id, character_id)
                )
            """)
            
            # ================================================================
            # NPCS TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS npcs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    session_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    personality TEXT,
                    location TEXT,
                    location_id INTEGER,
                    npc_type TEXT DEFAULT 'neutral',
                    is_merchant INTEGER DEFAULT 0,
                    merchant_inventory TEXT DEFAULT '[]',
                    dialogue_context TEXT,
                    stats TEXT DEFAULT '{}',
                    is_alive INTEGER DEFAULT 1,
                    created_by INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id)
                )
            """)
            
            # ================================================================
            # NPC RELATIONSHIPS TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS npc_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    npc_id INTEGER NOT NULL,
                    character_id INTEGER NOT NULL,
                    reputation INTEGER DEFAULT 0,
                    relationship_notes TEXT,
                    last_interaction TEXT,
                    FOREIGN KEY (npc_id) REFERENCES npcs(id),
                    FOREIGN KEY (character_id) REFERENCES characters(id),
                    UNIQUE(npc_id, character_id)
                )
            """)
            
            # ================================================================
            # COMBAT ENCOUNTERS TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS combat_encounters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    session_id INTEGER,
                    status TEXT DEFAULT 'active',
                    current_turn INTEGER DEFAULT 0,
                    initiative_order TEXT DEFAULT '[]',
                    combatants TEXT DEFAULT '[]',
                    combat_log TEXT DEFAULT '[]',
                    round_number INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    ended_at TEXT
                )
            """)
            
            # ================================================================
            # COMBAT PARTICIPANTS TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS combat_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    encounter_id INTEGER NOT NULL,
                    participant_type TEXT NOT NULL,
                    participant_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    current_hp INTEGER NOT NULL,
                    max_hp INTEGER NOT NULL,
                    initiative INTEGER DEFAULT 0,
                    is_player INTEGER DEFAULT 1,
                    status_effects TEXT DEFAULT '[]',
                    turn_order INTEGER DEFAULT 0,
                    FOREIGN KEY (encounter_id) REFERENCES combat_encounters(id)
                )
            """)
            
            # ================================================================
            # SESSIONS/CAMPAIGNS TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    dm_user_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'inactive',
                    max_players INTEGER DEFAULT 6,
                    current_quest_id INTEGER,
                    setting TEXT,
                    world_state TEXT DEFAULT '{}',
                    session_notes TEXT,
                    created_at TEXT NOT NULL,
                    last_played TEXT
                )
            """)
            
            # ================================================================
            # SESSION PARTICIPANTS TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS session_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    character_id INTEGER,
                    joined_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id),
                    FOREIGN KEY (character_id) REFERENCES characters(id),
                    UNIQUE(session_id, user_id)
                )
            """)
            
            # ================================================================
            # DICE ROLL HISTORY TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dice_rolls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    session_id INTEGER,
                    character_id INTEGER,
                    roll_type TEXT NOT NULL,
                    dice_expression TEXT NOT NULL,
                    individual_rolls TEXT NOT NULL,
                    modifier INTEGER DEFAULT 0,
                    total INTEGER NOT NULL,
                    purpose TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id),
                    FOREIGN KEY (character_id) REFERENCES characters(id)
                )
            """)
            
            # ================================================================
            # USER MEMORIES TABLE (for AI context)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    memory_key TEXT NOT NULL,
                    memory_value TEXT NOT NULL,
                    context TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, guild_id, memory_key)
                )
            """)
            
            # ================================================================
            # CONVERSATION HISTORY TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # ================================================================
            # STORY LOG TABLE (campaign history)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS story_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    entry_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    participants TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            
            # ================================================================
            # CHARACTER INTERVIEW PROGRESS TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS character_interviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    dm_channel_id INTEGER,
                    current_field TEXT,
                    responses TEXT DEFAULT '{}',
                    stage TEXT DEFAULT 'greeting',
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed INTEGER DEFAULT 0,
                    UNIQUE(user_id, guild_id)
                )
            """)
            
            # ================================================================
            # GAME STATE TABLE (for tracking active game progress)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS game_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL UNIQUE,
                    current_scene TEXT,
                    current_location TEXT,
                    dm_notes TEXT,
                    last_activity TEXT,
                    turn_count INTEGER DEFAULT 0,
                    game_data TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            
            # ================================================================
            # CHARACTER SPELLS TABLE (known/prepared spells)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS character_spells (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    spell_id TEXT NOT NULL,
                    spell_name TEXT NOT NULL,
                    spell_level INTEGER NOT NULL,
                    is_prepared INTEGER DEFAULT 1,
                    is_cantrip INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'class',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (character_id) REFERENCES characters(id),
                    UNIQUE(character_id, spell_id)
                )
            """)
            
            # ================================================================
            # CHARACTER ABILITIES TABLE (class features, racial traits)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS character_abilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    ability_id TEXT NOT NULL,
                    ability_name TEXT NOT NULL,
                    ability_type TEXT DEFAULT 'class',
                    uses_remaining INTEGER,
                    max_uses INTEGER,
                    recharge TEXT DEFAULT 'long_rest',
                    properties TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (character_id) REFERENCES characters(id),
                    UNIQUE(character_id, ability_id)
                )
            """)
            
            # ================================================================
            # SPELL SLOTS TABLE (track available spell slots per character)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS spell_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    slot_level INTEGER NOT NULL,
                    total INTEGER NOT NULL,
                    remaining INTEGER NOT NULL,
                    FOREIGN KEY (character_id) REFERENCES characters(id),
                    UNIQUE(character_id, slot_level)
                )
            """)
            
            # ================================================================
            # CHARACTER SKILLS TABLE (learned skills from skill trees)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS character_skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    skill_id TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    skill_branch TEXT NOT NULL,
                    skill_tier INTEGER NOT NULL,
                    is_passive INTEGER DEFAULT 0,
                    cooldown_remaining INTEGER DEFAULT 0,
                    uses_remaining INTEGER,
                    max_uses INTEGER,
                    recharge TEXT DEFAULT 'long_rest',
                    unlocked_at TEXT NOT NULL,
                    FOREIGN KEY (character_id) REFERENCES characters(id),
                    UNIQUE(character_id, skill_id)
                )
            """)
            
            # ================================================================
            # CHARACTER STATUS EFFECTS TABLE (buffs/debuffs)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS character_status_effects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    effect_id TEXT NOT NULL,
                    effect_name TEXT NOT NULL,
                    effect_type TEXT NOT NULL,
                    source TEXT,
                    duration_remaining INTEGER,
                    is_permanent INTEGER DEFAULT 0,
                    stacks INTEGER DEFAULT 1,
                    properties TEXT DEFAULT '{}',
                    applied_at TEXT NOT NULL,
                    FOREIGN KEY (character_id) REFERENCES characters(id)
                )
            """)
            
            # ================================================================
            # SKILL POINTS TABLE (track available skill points per character)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS character_skill_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL,
                    total_points INTEGER DEFAULT 0,
                    spent_points INTEGER DEFAULT 0,
                    FOREIGN KEY (character_id) REFERENCES characters(id),
                    UNIQUE(character_id)
                )
            """)
            
            # ================================================================
            # LOCATIONS TABLE
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    guild_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    location_type TEXT DEFAULT 'area',
                    parent_location_id INTEGER,
                    danger_level INTEGER DEFAULT 0,
                    current_weather TEXT,
                    hidden_secrets TEXT,
                    connected_locations TEXT DEFAULT '[]',
                    npcs_present TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id),
                    FOREIGN KEY (parent_location_id) REFERENCES locations(id)
                )
            """)
            
            # ================================================================
            # LOCATION CONNECTIONS TABLE (travel between locations)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS location_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_location_id INTEGER NOT NULL,
                    to_location_id INTEGER NOT NULL,
                    direction TEXT,
                    travel_time INTEGER DEFAULT 1,
                    requirements TEXT,
                    hidden INTEGER DEFAULT 0,
                    bidirectional INTEGER DEFAULT 1,
                    FOREIGN KEY (from_location_id) REFERENCES locations(id),
                    FOREIGN KEY (to_location_id) REFERENCES locations(id),
                    UNIQUE(from_location_id, to_location_id, direction)
                )
            """)
            
            # ================================================================
            # STORY ITEMS TABLE (key items, artifacts, plot items)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS story_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    guild_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    item_type TEXT DEFAULT 'key_item',
                    lore TEXT,
                    discovery_conditions TEXT,
                    is_discovered INTEGER DEFAULT 0,
                    discovered_by INTEGER,
                    discovered_at TEXT,
                    current_holder_id INTEGER,
                    location_id INTEGER,
                    dm_notes TEXT,
                    properties TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id),
                    FOREIGN KEY (discovered_by) REFERENCES characters(id),
                    FOREIGN KEY (current_holder_id) REFERENCES characters(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id)
                )
            """)
            
            # ================================================================
            # STORY EVENTS TABLE (plot events, triggers, encounters)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS story_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    guild_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    event_type TEXT DEFAULT 'story',
                    trigger_conditions TEXT,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    location_id INTEGER,
                    involved_npcs TEXT DEFAULT '[]',
                    involved_items TEXT DEFAULT '[]',
                    involved_characters TEXT DEFAULT '[]',
                    outcomes TEXT DEFAULT '{}',
                    dm_notes TEXT,
                    triggered_at TEXT,
                    resolved_at TEXT,
                    resolution_outcome TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id)
                )
            """)
            
            # ================================================================
            # SESSION SNAPSHOTS TABLE (save/load game state)
            # ================================================================
            await db.execute("""
                CREATE TABLE IF NOT EXISTS session_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    snapshot_data TEXT NOT NULL,
                    created_by INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            
            await db.commit()
            
            # Run migrations for existing databases
            await self._run_migrations(db)
    
    async def _run_migrations(self, db):
        """Run database migrations for schema changes"""
        # Migration 1: Add priority column to story_events if it doesn't exist
        try:
            cursor = await db.execute("PRAGMA table_info(story_events)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            if 'priority' not in columns:
                await db.execute("ALTER TABLE story_events ADD COLUMN priority INTEGER DEFAULT 0")
                await db.commit()
            
            # Migration 1b: Add triggered_at column to story_events if it doesn't exist
            if 'triggered_at' not in columns:
                await db.execute("ALTER TABLE story_events ADD COLUMN triggered_at TEXT")
                await db.commit()
            
            # Migration 1c: Add resolved_at column to story_events if it doesn't exist
            if 'resolved_at' not in columns:
                await db.execute("ALTER TABLE story_events ADD COLUMN resolved_at TEXT")
                await db.commit()
            
            # Migration 1d: Add resolution_outcome column to story_events if it doesn't exist
            if 'resolution_outcome' not in columns:
                await db.execute("ALTER TABLE story_events ADD COLUMN resolution_outcome TEXT")
                await db.commit()
        except Exception:
            pass  # Table might not exist yet, that's fine
        
        # Migration 2: Add points_of_interest to locations if it doesn't exist
        try:
            cursor = await db.execute("PRAGMA table_info(locations)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            if 'points_of_interest' not in columns:
                await db.execute("ALTER TABLE locations ADD COLUMN points_of_interest TEXT DEFAULT '[]'")
                await db.commit()
        except Exception:
            pass
        
        # Migration 3: Add NPC party member columns to npcs table if they don't exist
        try:
            cursor = await db.execute("PRAGMA table_info(npcs)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            if 'is_party_member' not in columns:
                await db.execute("ALTER TABLE npcs ADD COLUMN is_party_member INTEGER DEFAULT 0")
                await db.commit()
            
            if 'party_role' not in columns:
                await db.execute("ALTER TABLE npcs ADD COLUMN party_role TEXT")
                await db.commit()
            
            if 'loyalty' not in columns:
                await db.execute("ALTER TABLE npcs ADD COLUMN loyalty INTEGER DEFAULT 50")
                await db.commit()
            
            if 'combat_stats' not in columns:
                await db.execute("ALTER TABLE npcs ADD COLUMN combat_stats TEXT DEFAULT '{}'")
                await db.commit()
        except Exception:
            pass
    
    # ========================================================================
    # CHARACTER METHODS
    # ========================================================================
    
    async def create_character(self, user_id: int, guild_id: int, name: str, race: str,
                               char_class: str, stats: Dict[str, int], backstory: str = None,
                               session_id: int = None) -> int:
        """Create a new character and return its ID"""
        now = datetime.utcnow().isoformat()
        
        # Calculate HP based on class and constitution
        base_hp = {"warrior": 12, "mage": 6, "rogue": 8, "cleric": 10, "ranger": 10, "bard": 8}.get(char_class.lower(), 10)
        con_mod = (stats.get('constitution', 10) - 10) // 2
        max_hp = base_hp + con_mod
        
        # Calculate mana for casters
        max_mana = 0
        if char_class.lower() in ['mage', 'cleric', 'bard']:
            int_mod = (stats.get('intelligence', 10) - 10) // 2
            wis_mod = (stats.get('wisdom', 10) - 10) // 2
            max_mana = 10 + max(int_mod, wis_mod) * 2
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO characters (user_id, guild_id, session_id, name, race, class,
                    hp, max_hp, mana, max_mana, strength, dexterity, constitution,
                    intelligence, wisdom, charisma, backstory, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, guild_id, session_id, name, race, char_class,
                max_hp, max_hp, max_mana, max_mana,
                stats.get('strength', 10), stats.get('dexterity', 10), stats.get('constitution', 10),
                stats.get('intelligence', 10), stats.get('wisdom', 10), stats.get('charisma', 10),
                backstory, now, now
            ))
            await db.commit()
            return cursor.lastrowid
    
    def _normalize_character(self, char_dict: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Normalize character dict to use 'char_class' instead of 'class' for consistency"""
        if char_dict is None:
            return None
        # Copy the dict and rename 'class' to 'char_class' if present
        result = dict(char_dict)
        if 'class' in result:
            result['char_class'] = result.pop('class')
        return result
    
    async def get_character(self, character_id: int) -> Optional[Dict[str, Any]]:
        """Get character by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
            row = await cursor.fetchone()
            return self._normalize_character(dict(row)) if row else None
    
    async def get_active_character(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get user's active character in a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM characters 
                WHERE user_id = ? AND guild_id = ? AND is_active = 1
                ORDER BY updated_at DESC LIMIT 1
            """, (user_id, guild_id))
            row = await cursor.fetchone()
            return self._normalize_character(dict(row)) if row else None
    
    async def get_user_characters(self, user_id: int, guild_id: int) -> List[Dict[str, Any]]:
        """Get all characters for a user in a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM characters WHERE user_id = ? AND guild_id = ?
                ORDER BY is_active DESC, updated_at DESC
            """, (user_id, guild_id))
            rows = await cursor.fetchall()
            return [self._normalize_character(dict(row)) for row in rows]
    
    async def update_character(self, character_id: int, **kwargs) -> bool:
        """Update character fields"""
        if not kwargs:
            return False
        
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [character_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE characters SET {fields} WHERE id = ?", values)
            await db.commit()
            return True
    
    async def set_active_character(self, user_id: int, guild_id: int, character_id: int) -> bool:
        """Set a character as active (deactivate others)"""
        async with aiosqlite.connect(self.db_path) as db:
            # Deactivate all characters for this user in this guild
            await db.execute("""
                UPDATE characters SET is_active = 0 
                WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id))
            # Activate the selected character
            await db.execute("""
                UPDATE characters SET is_active = 1, updated_at = ?
                WHERE id = ? AND user_id = ? AND guild_id = ?
            """, (datetime.utcnow().isoformat(), character_id, user_id, guild_id))
            await db.commit()
            return True
    
    async def add_experience(self, character_id: int, xp: int) -> Dict[str, Any]:
        """Add experience and handle level ups"""
        char = await self.get_character(character_id)
        if not char:
            return {"error": "Character not found"}
        
        new_xp = char['experience'] + xp
        new_level = char['level']
        leveled_up = False
        
        # XP thresholds per level (simplified D&D-style)
        xp_thresholds = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000]
        
        while new_level < len(xp_thresholds) and new_xp >= xp_thresholds[new_level]:
            new_level += 1
            leveled_up = True
        
        updates = {'experience': new_xp, 'level': new_level}
        
        # On level up, increase max HP
        if leveled_up:
            con_mod = (char['constitution'] - 10) // 2
            hp_increase = max(1, 5 + con_mod)  # Average roll + con mod
            updates['max_hp'] = char['max_hp'] + hp_increase
            updates['hp'] = char['hp'] + hp_increase  # Heal on level up
        
        await self.update_character(character_id, **updates)
        
        return {
            "xp_gained": xp,
            "total_xp": new_xp,
            "new_level": new_level,
            "leveled_up": leveled_up,
            "hp_increase": updates.get('max_hp', char['max_hp']) - char['max_hp']
        }
    
    # ========================================================================
    # INVENTORY METHODS
    # ========================================================================
    
    async def add_item(self, character_id: int, item_id: str, item_name: str, 
                       item_type: str, quantity: int = 1, properties: Dict = None,
                       is_equipped: bool = False, slot: str = None) -> int:
        """Add an item to character's inventory, optionally equipped"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Check if item already exists (stackable) - only stack if not equipping
            if not is_equipped:
                cursor = await db.execute("""
                    SELECT id, quantity FROM inventory 
                    WHERE character_id = ? AND item_id = ? AND is_equipped = 0
                """, (character_id, item_id))
                existing = await cursor.fetchone()
                
                if existing and item_type in ['consumable', 'material', 'currency']:
                    # Stack the items
                    await db.execute("""
                        UPDATE inventory SET quantity = quantity + ? WHERE id = ?
                    """, (quantity, existing[0]))
                    await db.commit()
                    return existing[0]
            
            # Determine slot if equipping
            if is_equipped and not slot:
                slot = self._get_default_slot(item_type)
            
            # Add new item
            cursor = await db.execute("""
                INSERT INTO inventory (character_id, item_id, item_name, item_type, 
                    quantity, is_equipped, slot, properties, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (character_id, item_id, item_name, item_type, quantity,
                  1 if is_equipped else 0, slot, json.dumps(properties or {}), now))
            await db.commit()
            return cursor.lastrowid
    
    def _get_default_slot(self, item_type: str) -> str:
        """Get default equipment slot for an item type"""
        slot_map = {
            'weapon': 'main_hand',
            'armor': 'body',
            'shield': 'off_hand',
            'helmet': 'head',
            'boots': 'feet',
            'gloves': 'hands',
            'ring': 'ring',
            'amulet': 'neck',
            'cloak': 'back'
        }
        return slot_map.get(item_type, 'misc')
    
    async def get_inventory(self, character_id: int) -> List[Dict[str, Any]]:
        """Get all items in character's inventory"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM inventory WHERE character_id = ?
                ORDER BY is_equipped DESC, item_type, item_name
            """, (character_id,))
            rows = await cursor.fetchall()
            items = []
            for row in rows:
                item = dict(row)
                item['properties'] = json.loads(item['properties'])
                items.append(item)
            return items
    
    async def get_equipped_items(self, character_id: int) -> List[Dict[str, Any]]:
        """Get equipped items for a character"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM inventory WHERE character_id = ? AND is_equipped = 1
            """, (character_id,))
            rows = await cursor.fetchall()
            items = []
            for row in rows:
                item = dict(row)
                item['properties'] = json.loads(item['properties'])
                items.append(item)
            return items
    
    async def equip_item(self, inventory_id: int, slot: str) -> Dict[str, Any]:
        """Equip an item to a slot"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get the item
            cursor = await db.execute("SELECT * FROM inventory WHERE id = ?", (inventory_id,))
            item = await cursor.fetchone()
            if not item:
                return {"error": "Item not found"}
            
            item = dict(item)
            
            # Unequip any item in the same slot
            await db.execute("""
                UPDATE inventory SET is_equipped = 0, slot = NULL
                WHERE character_id = ? AND slot = ?
            """, (item['character_id'], slot))
            
            # Equip the new item
            await db.execute("""
                UPDATE inventory SET is_equipped = 1, slot = ? WHERE id = ?
            """, (slot, inventory_id))
            await db.commit()
            
            return {"success": True, "item_name": item['item_name'], "slot": slot}
    
    async def unequip_item(self, inventory_id: int) -> bool:
        """Unequip an item"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE inventory SET is_equipped = 0, slot = NULL WHERE id = ?
            """, (inventory_id,))
            await db.commit()
            return True
    
    async def remove_item(self, inventory_id: int, quantity: int = 1) -> bool:
        """Remove item(s) from inventory"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT quantity FROM inventory WHERE id = ?", (inventory_id,))
            row = await cursor.fetchone()
            if not row:
                return False
            
            if row[0] <= quantity:
                await db.execute("DELETE FROM inventory WHERE id = ?", (inventory_id,))
            else:
                await db.execute(
                    "UPDATE inventory SET quantity = quantity - ? WHERE id = ?",
                    (quantity, inventory_id))
            await db.commit()
            return True
    
    async def update_gold(self, character_id: int, amount: int) -> int:
        """Add or remove gold (can be negative)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE characters SET gold = MAX(0, gold + ?), updated_at = ?
                WHERE id = ?
            """, (amount, datetime.utcnow().isoformat(), character_id))
            await db.commit()
            
            cursor = await db.execute(
                "SELECT gold FROM characters WHERE id = ?", (character_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    # ========================================================================
    # SPELL & ABILITY METHODS
    # ========================================================================
    
    async def learn_spell(self, character_id: int, spell_id: str, spell_name: str,
                         spell_level: int, is_cantrip: bool = False, 
                         source: str = 'class') -> int:
        """Add a spell to character's known spells"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute("""
                    INSERT INTO character_spells (character_id, spell_id, spell_name, 
                        spell_level, is_cantrip, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (character_id, spell_id, spell_name, spell_level, 
                      1 if is_cantrip else 0, source, now))
                await db.commit()
                return cursor.lastrowid
            except Exception:
                # Spell already known
                return -1
    
    async def forget_spell(self, character_id: int, spell_id: str) -> bool:
        """Remove a spell from character's known spells"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM character_spells 
                WHERE character_id = ? AND spell_id = ?
            """, (character_id, spell_id))
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_character_spells(self, character_id: int, 
                                   prepared_only: bool = False) -> List[Dict[str, Any]]:
        """Get all spells known by a character"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = "SELECT * FROM character_spells WHERE character_id = ?"
            params = [character_id]
            
            if prepared_only:
                query += " AND is_prepared = 1"
            
            query += " ORDER BY is_cantrip DESC, spell_level, spell_name"
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def prepare_spell(self, character_id: int, spell_id: str, 
                           prepare: bool = True) -> bool:
        """Prepare or unprepare a spell"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE character_spells SET is_prepared = ?
                WHERE character_id = ? AND spell_id = ? AND is_cantrip = 0
            """, (1 if prepare else 0, character_id, spell_id))
            await db.commit()
            return cursor.rowcount > 0
    
    async def set_spell_prepared(self, character_id: int, spell_id: str,
                                  prepared: bool = True) -> bool:
        """Alias for prepare_spell - set spell preparation status"""
        return await self.prepare_spell(character_id, spell_id, prepared)
    
    async def get_spell_slots(self, character_id: int) -> Dict[int, Dict[str, int]]:
        """Get spell slots for a character"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM spell_slots WHERE character_id = ?
                ORDER BY slot_level
            """, (character_id,))
            rows = await cursor.fetchall()
            
            slots = {}
            for row in rows:
                slots[row['slot_level']] = {
                    'total': row['total'],
                    'remaining': row['remaining']
                }
            return slots
    
    async def set_spell_slots(self, character_id: int, 
                             slots: Dict[int, int]) -> None:
        """Set spell slot totals for a character (usually on level up)"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            for level, total in slots.items():
                await db.execute("""
                    INSERT INTO spell_slots (character_id, slot_level, total, remaining)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(character_id, slot_level) 
                    DO UPDATE SET total = ?, remaining = ?
                """, (character_id, level, total, total, total, total))
            await db.commit()
    
    async def use_spell_slot(self, character_id: int, slot_level: int) -> bool:
        """Use a spell slot. Returns False if no slots available."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT remaining FROM spell_slots 
                WHERE character_id = ? AND slot_level = ?
            """, (character_id, slot_level))
            row = await cursor.fetchone()
            
            if not row or row[0] <= 0:
                return False
            
            await db.execute("""
                UPDATE spell_slots SET remaining = remaining - 1
                WHERE character_id = ? AND slot_level = ?
            """, (character_id, slot_level))
            await db.commit()
            return True
    
    async def restore_spell_slots(self, character_id: int, 
                                  levels: List[int] = None) -> None:
        """Restore spell slots (on rest). If levels is None, restore all."""
        async with aiosqlite.connect(self.db_path) as db:
            if levels:
                for level in levels:
                    await db.execute("""
                        UPDATE spell_slots SET remaining = total
                        WHERE character_id = ? AND slot_level = ?
                    """, (character_id, level))
            else:
                await db.execute("""
                    UPDATE spell_slots SET remaining = total
                    WHERE character_id = ?
                """, (character_id,))
            await db.commit()
    
    async def add_ability(self, character_id: int, ability_id: str, ability_name: str,
                         ability_type: str = 'class', max_uses: int = None,
                         recharge: str = 'long_rest', properties: Dict = None) -> int:
        """Add an ability/feature to a character"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute("""
                    INSERT INTO character_abilities (character_id, ability_id, ability_name,
                        ability_type, uses_remaining, max_uses, recharge, properties, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (character_id, ability_id, ability_name, ability_type, 
                      max_uses, max_uses, recharge, json.dumps(properties or {}), now))
                await db.commit()
                return cursor.lastrowid
            except Exception:
                return -1
    
    async def get_character_abilities(self, character_id: int) -> List[Dict[str, Any]]:
        """Get all abilities for a character"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM character_abilities WHERE character_id = ?
                ORDER BY ability_type, ability_name
            """, (character_id,))
            rows = await cursor.fetchall()
            
            abilities = []
            for row in rows:
                ability = dict(row)
                ability['properties'] = json.loads(ability['properties'])
                abilities.append(ability)
            return abilities
    
    async def use_ability(self, character_id: int, ability_id: str) -> bool:
        """Use an ability. Returns False if no uses remaining."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT uses_remaining, max_uses FROM character_abilities 
                WHERE character_id = ? AND ability_id = ?
            """, (character_id, ability_id))
            row = await cursor.fetchone()
            
            if not row:
                return False
            
            # Unlimited use ability
            if row[1] is None:
                return True
            
            # Check remaining uses
            if row[0] is not None and row[0] <= 0:
                return False
            
            await db.execute("""
                UPDATE character_abilities SET uses_remaining = uses_remaining - 1
                WHERE character_id = ? AND ability_id = ?
            """, (character_id, ability_id))
            await db.commit()
            return True
    
    async def restore_abilities(self, character_id: int, 
                               recharge_type: str = 'long_rest') -> None:
        """Restore ability uses based on recharge type"""
        async with aiosqlite.connect(self.db_path) as db:
            if recharge_type == 'long_rest':
                # Restore long rest and short rest abilities
                await db.execute("""
                    UPDATE character_abilities SET uses_remaining = max_uses
                    WHERE character_id = ? AND max_uses IS NOT NULL
                """, (character_id,))
            else:
                # Short rest - only restore short_rest abilities
                await db.execute("""
                    UPDATE character_abilities SET uses_remaining = max_uses
                    WHERE character_id = ? AND recharge = 'short_rest' AND max_uses IS NOT NULL
                """, (character_id,))
            await db.commit()
    
    # ========================================================================
    # SKILL METHODS
    # ========================================================================
    
    async def learn_skill(self, character_id: int, skill_id: str, skill_name: str,
                         skill_branch: str, skill_tier: int, is_passive: bool = False,
                         max_uses: int = None, recharge: str = 'long_rest') -> int:
        """Learn a new skill from the skill tree"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute("""
                    INSERT INTO character_skills (character_id, skill_id, skill_name,
                        skill_branch, skill_tier, is_passive, uses_remaining, max_uses,
                        recharge, unlocked_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (character_id, skill_id, skill_name, skill_branch, skill_tier,
                      1 if is_passive else 0, max_uses, max_uses, recharge, now))
                await db.commit()
                return cursor.lastrowid
            except Exception:
                return -1
    
    async def get_character_skills(self, character_id: int) -> List[Dict[str, Any]]:
        """Get all learned skills for a character"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM character_skills WHERE character_id = ?
                ORDER BY skill_branch, skill_tier, skill_name
            """, (character_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_character_skills_by_branch(self, character_id: int, 
                                              branch: str) -> List[Dict[str, Any]]:
        """Get all skills for a character in a specific branch"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM character_skills 
                WHERE character_id = ? AND skill_branch = ?
                ORDER BY skill_tier, skill_name
            """, (character_id, branch))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def has_skill(self, character_id: int, skill_id: str) -> bool:
        """Check if character has learned a specific skill"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 1 FROM character_skills WHERE character_id = ? AND skill_id = ?
            """, (character_id, skill_id))
            return await cursor.fetchone() is not None
    
    async def use_skill(self, character_id: int, skill_id: str) -> bool:
        """Use a skill. Returns False if no uses remaining or on cooldown."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT uses_remaining, max_uses, cooldown_remaining, is_passive 
                FROM character_skills 
                WHERE character_id = ? AND skill_id = ?
            """, (character_id, skill_id))
            row = await cursor.fetchone()
            
            if not row:
                return False
            
            uses_remaining, max_uses, cooldown_remaining, is_passive = row
            
            # Passive skills can't be "used"
            if is_passive:
                return False
            
            # Check cooldown
            if cooldown_remaining and cooldown_remaining > 0:
                return False
            
            # Unlimited use skill
            if max_uses is None:
                return True
            
            # Check remaining uses
            if uses_remaining is not None and uses_remaining <= 0:
                return False
            
            await db.execute("""
                UPDATE character_skills SET uses_remaining = uses_remaining - 1
                WHERE character_id = ? AND skill_id = ?
            """, (character_id, skill_id))
            await db.commit()
            return True
    
    async def set_skill_cooldown(self, character_id: int, skill_id: str, 
                                  cooldown: int) -> None:
        """Set cooldown for a skill (in rounds/turns)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE character_skills SET cooldown_remaining = ?
                WHERE character_id = ? AND skill_id = ?
            """, (cooldown, character_id, skill_id))
            await db.commit()
    
    async def reduce_cooldowns(self, character_id: int, amount: int = 1) -> None:
        """Reduce all cooldowns by amount (usually called each turn)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE character_skills 
                SET cooldown_remaining = MAX(0, cooldown_remaining - ?)
                WHERE character_id = ? AND cooldown_remaining > 0
            """, (amount, character_id))
            await db.commit()
    
    async def restore_skills(self, character_id: int, 
                            recharge_type: str = 'long_rest') -> None:
        """Restore skill uses based on recharge type"""
        async with aiosqlite.connect(self.db_path) as db:
            if recharge_type == 'long_rest':
                # Restore all skills and reset cooldowns
                await db.execute("""
                    UPDATE character_skills SET uses_remaining = max_uses, cooldown_remaining = 0
                    WHERE character_id = ? AND max_uses IS NOT NULL
                """, (character_id,))
            else:
                # Short rest - only restore short_rest skills
                await db.execute("""
                    UPDATE character_skills SET uses_remaining = max_uses, cooldown_remaining = 0
                    WHERE character_id = ? AND recharge = 'short_rest' AND max_uses IS NOT NULL
                """, (character_id,))
            await db.commit()
    
    async def unlearn_skill(self, character_id: int, skill_id: str) -> bool:
        """Remove a skill from a character (e.g., for respec)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM character_skills WHERE character_id = ? AND skill_id = ?
            """, (character_id, skill_id))
            await db.commit()
            return cursor.rowcount > 0
    
    # ========================================================================
    # SKILL POINTS METHODS
    # ========================================================================
    
    async def get_skill_points(self, character_id: int) -> Dict[str, int]:
        """Get skill points for a character"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT total_points, spent_points FROM character_skill_points
                WHERE character_id = ?
            """, (character_id,))
            row = await cursor.fetchone()
            
            if row:
                return {"total": row[0], "spent": row[1], "available": row[0] - row[1]}
            return {"total": 0, "spent": 0, "available": 0}
    
    async def add_skill_points(self, character_id: int, points: int) -> None:
        """Add skill points to a character"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO character_skill_points (character_id, total_points, spent_points)
                VALUES (?, ?, 0)
                ON CONFLICT(character_id) DO UPDATE SET total_points = total_points + ?
            """, (character_id, points, points))
            await db.commit()
    
    async def spend_skill_points(self, character_id: int, points: int) -> bool:
        """Spend skill points. Returns False if not enough points."""
        skill_points = await self.get_skill_points(character_id)
        
        if skill_points["available"] < points:
            return False
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE character_skill_points SET spent_points = spent_points + ?
                WHERE character_id = ?
            """, (points, character_id))
            await db.commit()
        return True
    
    async def refund_skill_points(self, character_id: int, points: int) -> None:
        """Refund skill points (for respec)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE character_skill_points 
                SET spent_points = MAX(0, spent_points - ?)
                WHERE character_id = ?
            """, (points, character_id))
            await db.commit()
    
    # ========================================================================
    # STATUS EFFECTS METHODS
    # ========================================================================
    
    async def apply_status_effect(self, character_id: int, effect_id: str, effect_name: str,
                                   effect_type: str, duration: int = None, 
                                   source: str = None, stacks: int = 1,
                                   is_permanent: bool = False, 
                                   properties: Dict = None) -> int:
        """Apply a status effect (buff/debuff) to a character"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Check if effect already exists and can stack
            cursor = await db.execute("""
                SELECT id, stacks FROM character_status_effects
                WHERE character_id = ? AND effect_id = ?
            """, (character_id, effect_id))
            existing = await cursor.fetchone()
            
            if existing:
                # Update stacks and refresh duration
                await db.execute("""
                    UPDATE character_status_effects 
                    SET stacks = stacks + ?, duration_remaining = ?
                    WHERE id = ?
                """, (stacks, duration, existing[0]))
                await db.commit()
                return existing[0]
            else:
                cursor = await db.execute("""
                    INSERT INTO character_status_effects (character_id, effect_id, effect_name,
                        effect_type, source, duration_remaining, is_permanent, stacks, 
                        properties, applied_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (character_id, effect_id, effect_name, effect_type, source, duration,
                      1 if is_permanent else 0, stacks, json.dumps(properties or {}), now))
                await db.commit()
                return cursor.lastrowid
    
    async def get_status_effects(self, character_id: int, 
                                  effect_type: str = None) -> List[Dict[str, Any]]:
        """Get all status effects on a character, optionally filtered by type"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if effect_type:
                cursor = await db.execute("""
                    SELECT * FROM character_status_effects 
                    WHERE character_id = ? AND effect_type = ?
                    ORDER BY applied_at
                """, (character_id, effect_type))
            else:
                cursor = await db.execute("""
                    SELECT * FROM character_status_effects WHERE character_id = ?
                    ORDER BY effect_type, applied_at
                """, (character_id,))
            
            rows = await cursor.fetchall()
            effects = []
            for row in rows:
                effect = dict(row)
                effect['properties'] = json.loads(effect['properties'])
                effects.append(effect)
            return effects
    
    async def has_status_effect(self, character_id: int, effect_id: str) -> bool:
        """Check if character has a specific status effect"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 1 FROM character_status_effects 
                WHERE character_id = ? AND effect_id = ?
            """, (character_id, effect_id))
            return await cursor.fetchone() is not None
    
    async def remove_status_effect(self, character_id: int, effect_id: str) -> bool:
        """Remove a specific status effect"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM character_status_effects 
                WHERE character_id = ? AND effect_id = ?
            """, (character_id, effect_id))
            await db.commit()
            return cursor.rowcount > 0
    
    async def tick_status_effects(self, character_id: int) -> List[str]:
        """Reduce duration of all effects by 1 and remove expired ones.
        Returns list of removed effect IDs."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get effects that will expire
            cursor = await db.execute("""
                SELECT effect_id FROM character_status_effects
                WHERE character_id = ? AND duration_remaining = 1 AND is_permanent = 0
            """, (character_id,))
            expired = [row[0] for row in await cursor.fetchall()]
            
            # Remove expired effects
            await db.execute("""
                DELETE FROM character_status_effects
                WHERE character_id = ? AND duration_remaining <= 1 AND is_permanent = 0
            """, (character_id,))
            
            # Reduce duration of remaining effects
            await db.execute("""
                UPDATE character_status_effects
                SET duration_remaining = duration_remaining - 1
                WHERE character_id = ? AND duration_remaining > 1 AND is_permanent = 0
            """, (character_id,))
            
            await db.commit()
            return expired
    
    async def clear_status_effects(self, character_id: int, 
                                    effect_type: str = None) -> int:
        """Clear all status effects (or just a specific type) from a character"""
        async with aiosqlite.connect(self.db_path) as db:
            if effect_type:
                cursor = await db.execute("""
                    DELETE FROM character_status_effects 
                    WHERE character_id = ? AND effect_type = ?
                """, (character_id, effect_type))
            else:
                cursor = await db.execute("""
                    DELETE FROM character_status_effects WHERE character_id = ?
                """, (character_id,))
            await db.commit()
            return cursor.rowcount
    
    # ========================================================================
    # QUEST METHODS
    # ========================================================================
    
    async def create_quest(self, guild_id: int, title: str, description: str,
                          objectives: List[Dict], rewards: Dict, created_by: int,
                          session_id: int = None, difficulty: str = "medium",
                          quest_giver_npc_id: int = None, dm_notes: str = None,
                          dm_plan: str = None) -> int:
        """Create a new quest"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO quests (guild_id, session_id, title, description, objectives,
                    rewards, difficulty, quest_giver_npc_id, dm_notes, dm_plan, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, session_id, title, description, json.dumps(objectives),
                  json.dumps(rewards), difficulty, quest_giver_npc_id, dm_notes, dm_plan,
                  created_by, now))
            await db.commit()
            return cursor.lastrowid
    
    async def get_quest(self, quest_id: int) -> Optional[Dict[str, Any]]:
        """Get quest by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM quests WHERE id = ?", (quest_id,))
            row = await cursor.fetchone()
            if row:
                quest = dict(row)
                quest['objectives'] = json.loads(quest['objectives'])
                quest['rewards'] = json.loads(quest['rewards'])
                return quest
            return None
    
    async def get_available_quests(self, guild_id: int, session_id: int = None) -> List[Dict[str, Any]]:
        """Get available quests for a guild/session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if session_id:
                cursor = await db.execute("""
                    SELECT * FROM quests WHERE guild_id = ? AND session_id = ? AND status = 'available'
                    ORDER BY created_at DESC
                """, (guild_id, session_id))
            else:
                cursor = await db.execute("""
                    SELECT * FROM quests WHERE guild_id = ? AND status = 'available'
                    ORDER BY created_at DESC
                """, (guild_id,))
            rows = await cursor.fetchall()
            quests = []
            for row in rows:
                quest = dict(row)
                quest['objectives'] = json.loads(quest['objectives'])
                quest['rewards'] = json.loads(quest['rewards'])
                quests.append(quest)
            return quests
    
    async def accept_quest(self, quest_id: int, character_id: int) -> Dict[str, Any]:
        """Accept a quest for a character"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO quest_progress (quest_id, character_id, started_at)
                    VALUES (?, ?, ?)
                """, (quest_id, character_id, now))
                await db.commit()
                return {"success": True}
            except aiosqlite.IntegrityError:
                return {"error": "Quest already accepted"}
    
    async def get_character_quests(self, character_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get quests for a character"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                cursor = await db.execute("""
                    SELECT q.*, qp.objectives_completed, qp.status as progress_status, qp.started_at
                    FROM quests q
                    JOIN quest_progress qp ON q.id = qp.quest_id
                    WHERE qp.character_id = ? AND qp.status = ?
                    ORDER BY qp.started_at DESC
                """, (character_id, status))
            else:
                cursor = await db.execute("""
                    SELECT q.*, qp.objectives_completed, qp.status as progress_status, qp.started_at
                    FROM quests q
                    JOIN quest_progress qp ON q.id = qp.quest_id
                    WHERE qp.character_id = ?
                    ORDER BY qp.started_at DESC
                """, (character_id,))
            rows = await cursor.fetchall()
            quests = []
            for row in rows:
                quest = dict(row)
                quest['objectives'] = json.loads(quest['objectives'])
                quest['rewards'] = json.loads(quest['rewards'])
                quest['objectives_completed'] = json.loads(quest['objectives_completed'])
                quests.append(quest)
            return quests
    
    async def complete_objective(self, quest_id: int, character_id: int, 
                                objective_index: int) -> Dict[str, Any]:
        """Mark a quest objective as complete"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get current progress
            cursor = await db.execute("""
                SELECT objectives_completed FROM quest_progress
                WHERE quest_id = ? AND character_id = ?
            """, (quest_id, character_id))
            row = await cursor.fetchone()
            if not row:
                return {"error": "Quest not accepted"}
            
            completed = json.loads(row['objectives_completed'])
            if objective_index not in completed:
                completed.append(objective_index)
            
            await db.execute("""
                UPDATE quest_progress SET objectives_completed = ?
                WHERE quest_id = ? AND character_id = ?
            """, (json.dumps(completed), quest_id, character_id))
            await db.commit()
            
            # Check if all objectives complete
            quest = await self.get_quest(quest_id)
            all_complete = len(completed) >= len(quest['objectives'])
            
            return {"completed_objectives": completed, "quest_complete": all_complete}
    
    async def complete_quest(self, quest_id: int, character_id: int) -> Dict[str, Any]:
        """Mark a quest as complete and give rewards"""
        now = datetime.utcnow().isoformat()
        
        quest = await self.get_quest(quest_id)
        if not quest:
            return {"error": "Quest not found"}
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE quest_progress SET status = 'completed', completed_at = ?
                WHERE quest_id = ? AND character_id = ?
            """, (now, quest_id, character_id))
            await db.commit()
        
        # Distribute rewards
        rewards_given = {}
        if 'gold' in quest['rewards']:
            new_gold = await self.update_gold(character_id, quest['rewards']['gold'])
            rewards_given['gold'] = quest['rewards']['gold']
        
        if 'xp' in quest['rewards']:
            xp_result = await self.add_experience(character_id, quest['rewards']['xp'])
            rewards_given['xp'] = quest['rewards']['xp']
            rewards_given['level_up'] = xp_result.get('leveled_up', False)
        
        if 'items' in quest['rewards']:
            for item in quest['rewards']['items']:
                await self.add_item(character_id, item['id'], item['name'], 
                                   item.get('type', 'misc'), item.get('quantity', 1))
            rewards_given['items'] = quest['rewards']['items']
        
        return {"success": True, "rewards": rewards_given}
    
    async def update_quest(self, quest_id: int, **kwargs) -> bool:
        """Update quest fields"""
        if not kwargs:
            return False
        
        # Handle JSON fields
        if 'objectives' in kwargs:
            kwargs['objectives'] = json.dumps(kwargs['objectives'])
        if 'rewards' in kwargs:
            kwargs['rewards'] = json.dumps(kwargs['rewards'])
        
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [quest_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE quests SET {fields} WHERE id = ?", values)
            await db.commit()
            return True
    
    # ========================================================================
    # NPC METHODS
    # ========================================================================
    
    async def create_npc(self, guild_id: int, name: str, description: str,
                        personality: str, created_by: int, npc_type: str = "neutral",
                        location: str = None, is_merchant: bool = False,
                        merchant_inventory: List[Dict] = None, stats: Dict = None,
                        session_id: int = None) -> int:
        """Create a new NPC"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO npcs (guild_id, session_id, name, description, personality,
                    location, npc_type, is_merchant, merchant_inventory, stats, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, session_id, name, description, personality, location, npc_type,
                  1 if is_merchant else 0, json.dumps(merchant_inventory or []),
                  json.dumps(stats or {}), created_by, now))
            await db.commit()
            return cursor.lastrowid
    
    async def get_npc(self, npc_id: int) -> Optional[Dict[str, Any]]:
        """Get NPC by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM npcs WHERE id = ?", (npc_id,))
            row = await cursor.fetchone()
            if row:
                npc = dict(row)
                npc['merchant_inventory'] = json.loads(npc['merchant_inventory'])
                npc['stats'] = json.loads(npc['stats'])
                return npc
            return None
    
    async def get_npcs_by_location(self, guild_id: int, location: str) -> List[Dict[str, Any]]:
        """Get NPCs at a location"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM npcs WHERE guild_id = ? AND location = ? AND is_alive = 1
            """, (guild_id, location))
            rows = await cursor.fetchall()
            npcs = []
            for row in rows:
                npc = dict(row)
                npc['merchant_inventory'] = json.loads(npc['merchant_inventory'])
                npc['stats'] = json.loads(npc['stats'])
                npcs.append(npc)
            return npcs
    
    async def get_guild_npcs(self, guild_id: int, session_id: int = None) -> List[Dict[str, Any]]:
        """Get all NPCs in a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if session_id:
                cursor = await db.execute("""
                    SELECT * FROM npcs WHERE guild_id = ? AND session_id = ? AND is_alive = 1
                    ORDER BY name
                """, (guild_id, session_id))
            else:
                cursor = await db.execute("""
                    SELECT * FROM npcs WHERE guild_id = ? AND is_alive = 1 ORDER BY name
                """, (guild_id,))
            rows = await cursor.fetchall()
            npcs = []
            for row in rows:
                npc = dict(row)
                npc['merchant_inventory'] = json.loads(npc['merchant_inventory'])
                npc['stats'] = json.loads(npc['stats'])
                npcs.append(npc)
            return npcs
    
    async def update_npc_relationship(self, npc_id: int, character_id: int, 
                                      reputation_change: int = 0, notes: str = None) -> int:
        """Update or create NPC-character relationship"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Check if relationship exists
            cursor = await db.execute("""
                SELECT id, reputation FROM npc_relationships
                WHERE npc_id = ? AND character_id = ?
            """, (npc_id, character_id))
            existing = await cursor.fetchone()
            
            if existing:
                new_rep = max(-100, min(100, existing[1] + reputation_change))
                update_fields = ["reputation = ?", "last_interaction = ?"]
                update_values = [new_rep, now]
                if notes:
                    update_fields.append("relationship_notes = ?")
                    update_values.append(notes)
                update_values.extend([npc_id, character_id])
                
                await db.execute(f"""
                    UPDATE npc_relationships SET {', '.join(update_fields)}
                    WHERE npc_id = ? AND character_id = ?
                """, update_values)
                await db.commit()
                return new_rep
            else:
                # Cap initial reputation between -100 and 100
                initial_rep = max(-100, min(100, reputation_change))
                await db.execute("""
                    INSERT INTO npc_relationships (npc_id, character_id, reputation, 
                        relationship_notes, last_interaction)
                    VALUES (?, ?, ?, ?, ?)
                """, (npc_id, character_id, initial_rep, notes, now))
                await db.commit()
                return initial_rep
    
    async def get_npc_relationship(self, npc_id: int, character_id: int) -> Dict[str, Any]:
        """Get relationship between NPC and character"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM npc_relationships
                WHERE npc_id = ? AND character_id = ?
            """, (npc_id, character_id))
            row = await cursor.fetchone()
            return dict(row) if row else {"reputation": 0, "relationship_notes": None}
    
    # ========================================================================
    # NPC PARTY MEMBER METHODS
    # ========================================================================
    
    async def add_npc_to_party(self, npc_id: int, party_role: str = None, 
                               combat_stats: Dict = None) -> bool:
        """Add an NPC as a party member/companion"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Parse combat_stats if it's a string
                if isinstance(combat_stats, str):
                    combat_stats = json.loads(combat_stats)
                
                await db.execute("""
                    UPDATE npcs SET 
                        is_party_member = 1,
                        party_role = ?,
                        loyalty = COALESCE(loyalty, 50),
                        combat_stats = ?
                    WHERE id = ?
                """, (party_role, json.dumps(combat_stats or {}), npc_id))
                await db.commit()
                return True
            except Exception:
                return False
    
    async def remove_npc_from_party(self, npc_id: int) -> bool:
        """Remove an NPC from the party"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    UPDATE npcs SET 
                        is_party_member = 0,
                        party_role = NULL
                    WHERE id = ?
                """, (npc_id,))
                await db.commit()
                return True
            except Exception:
                return False
    
    async def get_party_npcs(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all NPC party members for a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            try:
                cursor = await db.execute("""
                    SELECT * FROM npcs 
                    WHERE session_id = ? AND is_party_member = 1 AND is_alive = 1
                    ORDER BY name
                """, (session_id,))
                rows = await cursor.fetchall()
                npcs = []
                for row in rows:
                    npc = dict(row)
                    npc['merchant_inventory'] = json.loads(npc.get('merchant_inventory', '[]') or '[]')
                    npc['stats'] = json.loads(npc.get('stats', '{}') or '{}')
                    npc['combat_stats'] = json.loads(npc.get('combat_stats', '{}') or '{}')
                    npcs.append(npc)
                return npcs
            except Exception:
                # Handle case where new columns don't exist yet
                cursor = await db.execute("""
                    SELECT * FROM npcs 
                    WHERE session_id = ? AND is_alive = 1
                    ORDER BY name
                """, (session_id,))
                rows = await cursor.fetchall()
                # Return empty for party NPCs if columns don't exist
                return []
    
    async def update_npc_loyalty(self, npc_id: int, loyalty_change: int) -> int:
        """Update an NPC party member's loyalty (0-100 scale)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT loyalty FROM npcs WHERE id = ?", (npc_id,))
            row = await cursor.fetchone()
            if row:
                current = row[0] or 50
                new_loyalty = max(0, min(100, current + loyalty_change))
                await db.execute("UPDATE npcs SET loyalty = ? WHERE id = ?", (new_loyalty, npc_id))
                await db.commit()
                return new_loyalty
            return 50
    
    async def get_npc_loyalty(self, npc_id: int) -> int:
        """Get an NPC's current loyalty level"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute("SELECT loyalty FROM npcs WHERE id = ?", (npc_id,))
                row = await cursor.fetchone()
                return row[0] if row and row[0] is not None else 50
            except Exception:
                return 50
    
    # ========================================================================
    # COMBAT METHODS
    # ========================================================================
    
    async def create_combat(self, guild_id: int, channel_id: int, 
                           session_id: int = None) -> int:
        """Create a new combat encounter"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO combat_encounters (guild_id, channel_id, session_id, created_at)
                VALUES (?, ?, ?, ?)
            """, (guild_id, channel_id, session_id, now))
            await db.commit()
            return cursor.lastrowid
    
    async def get_active_combat(self, guild_id: int = None, channel_id: int = None) -> Optional[Dict[str, Any]]:
        """Get active combat in a channel or guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if channel_id:
                cursor = await db.execute("""
                    SELECT * FROM combat_encounters 
                    WHERE channel_id = ? AND status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                """, (channel_id,))
            elif guild_id:
                cursor = await db.execute("""
                    SELECT * FROM combat_encounters 
                    WHERE guild_id = ? AND status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                """, (guild_id,))
            else:
                return None
            row = await cursor.fetchone()
            if row:
                combat = dict(row)
                combat['initiative_order'] = json.loads(combat['initiative_order'])
                combat['combatants'] = json.loads(combat['combatants'])
                combat['combat_log'] = json.loads(combat['combat_log'])
                return combat
            return None
    
    async def add_combatant(self, encounter_id: int, participant_type: str,
                           participant_id: int, name: str, hp: int, max_hp: int,
                           initiative: int, is_player: bool = True) -> int:
        """Add a combatant to an encounter"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO combat_participants (encounter_id, participant_type, participant_id,
                    name, current_hp, max_hp, initiative, is_player)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (encounter_id, participant_type, participant_id, name, hp, max_hp,
                  initiative, 1 if is_player else 0))
            await db.commit()
            return cursor.lastrowid
    
    async def get_combatants(self, encounter_id: int) -> List[Dict[str, Any]]:
        """Get all combatants in an encounter"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM combat_participants WHERE encounter_id = ?
                ORDER BY initiative DESC, id ASC
            """, (encounter_id,))
            rows = await cursor.fetchall()
            combatants = []
            for row in rows:
                c = dict(row)
                c['status_effects'] = json.loads(c['status_effects'])
                combatants.append(c)
            return combatants
    
    async def update_combatant_hp(self, participant_id: int, hp_change: int) -> Dict[str, Any]:
        """Update combatant HP"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM combat_participants WHERE id = ?", (participant_id,))
            row = await cursor.fetchone()
            if not row:
                return {"error": "Combatant not found"}
            
            combatant = dict(row)
            new_hp = max(0, min(combatant['max_hp'], combatant['current_hp'] + hp_change))
            
            await db.execute(
                "UPDATE combat_participants SET current_hp = ? WHERE id = ?",
                (new_hp, participant_id))
            await db.commit()
            
            return {
                "name": combatant['name'],
                "old_hp": combatant['current_hp'],
                "new_hp": new_hp,
                "max_hp": combatant['max_hp'],
                "is_dead": new_hp <= 0
            }
    
    async def update_combatant_initiative(self, participant_id: int, initiative: int) -> bool:
        """Update a combatant's initiative value"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE combat_participants SET initiative = ? WHERE id = ?",
                (initiative, participant_id))
            await db.commit()
            return True
    
    async def add_status_effect(self, participant_id: int, effect: str, 
                               duration: int = -1) -> bool:
        """Add a status effect to a combatant"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT status_effects FROM combat_participants WHERE id = ?",
                (participant_id,))
            row = await cursor.fetchone()
            if not row:
                return False
            
            effects = json.loads(row[0])
            effects.append({"effect": effect, "duration": duration})
            
            await db.execute(
                "UPDATE combat_participants SET status_effects = ? WHERE id = ?",
                (json.dumps(effects), participant_id))
            await db.commit()
            return True
    
    async def advance_combat_turn(self, encounter_id: int) -> Dict[str, Any]:
        """Advance to the next turn in combat"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get combat state
            cursor = await db.execute(
                "SELECT * FROM combat_encounters WHERE id = ?", (encounter_id,))
            combat = await cursor.fetchone()
            if not combat:
                return {"error": "Combat not found"}
            
            combat = dict(combat)
            combatants = await self.get_combatants(encounter_id)
            alive_combatants = [c for c in combatants if c['current_hp'] > 0]
            
            if not alive_combatants:
                return {"error": "No alive combatants"}
            
            current_turn = combat['current_turn']
            new_turn = (current_turn + 1) % len(alive_combatants)
            new_round = combat['round_number']
            
            if new_turn == 0:
                new_round += 1
            
            await db.execute("""
                UPDATE combat_encounters SET current_turn = ?, round_number = ?
                WHERE id = ?
            """, (new_turn, new_round, encounter_id))
            await db.commit()
            
            return {
                "round": new_round,
                "current_combatant": alive_combatants[new_turn],
                "turn_index": new_turn
            }
    
    async def end_combat(self, encounter_id: int) -> bool:
        """End a combat encounter"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE combat_encounters SET status = 'ended', ended_at = ?
                WHERE id = ?
            """, (now, encounter_id))
            await db.commit()
            return True
    
    async def add_combat_log(self, encounter_id: int, entry: str) -> bool:
        """Add an entry to the combat log"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT combat_log FROM combat_encounters WHERE id = ?", (encounter_id,))
            row = await cursor.fetchone()
            if not row:
                return False
            
            log = json.loads(row[0])
            log.append({"entry": entry, "time": datetime.utcnow().isoformat()})
            
            await db.execute(
                "UPDATE combat_encounters SET combat_log = ? WHERE id = ?",
                (json.dumps(log), encounter_id))
            await db.commit()
            return True
    
    # ========================================================================
    # SESSION METHODS
    # ========================================================================
    
    async def create_session(self, guild_id: int, name: str, dm_user_id: int,
                            description: str = None, setting: str = None,
                            max_players: int = 6) -> int:
        """Create a new campaign session"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO sessions (guild_id, name, description, dm_user_id, setting, max_players, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, name, description, dm_user_id, setting, max_players, now))
            await db.commit()
            return cursor.lastrowid
    
    async def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = await cursor.fetchone()
            if row:
                session = dict(row)
                session['world_state'] = json.loads(session['world_state'])
                return session
            return None
    
    async def get_full_session_state(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get full session state including participants, characters, locations, etc."""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get participants with character info
            cursor = await db.execute("""
                SELECT sp.*, c.name as character_name, c.class as character_class, 
                       c.race as character_race, c.level as character_level
                FROM session_participants sp
                LEFT JOIN characters c ON sp.character_id = c.id
                WHERE sp.session_id = ?
            """, (session_id,))
            participants = [dict(row) for row in await cursor.fetchall()]
            
            # Get session locations
            cursor = await db.execute("""
                SELECT * FROM locations WHERE session_id = ?
            """, (session_id,))
            locations = [dict(row) for row in await cursor.fetchall()]
            
            # Get session NPCs
            cursor = await db.execute("""
                SELECT * FROM npcs WHERE session_id = ?
            """, (session_id,))
            npcs = [dict(row) for row in await cursor.fetchall()]
            
            # Get session quests
            cursor = await db.execute("""
                SELECT * FROM quests WHERE session_id = ?
            """, (session_id,))
            quests = []
            for row in await cursor.fetchall():
                quest = dict(row)
                if quest.get('objectives'):
                    quest['objectives'] = json.loads(quest['objectives'])
                if quest.get('rewards'):
                    quest['rewards'] = json.loads(quest['rewards'])
                quests.append(quest)
        
        return {
            **session,
            "participants": participants,
            "locations": locations,
            "npcs": npcs,
            "quests": quests
        }
    
    async def get_guild_sessions(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM sessions WHERE guild_id = ? ORDER BY last_played DESC NULLS LAST
            """, (guild_id,))
            rows = await cursor.fetchall()
            sessions = []
            for row in rows:
                session = dict(row)
                session['world_state'] = json.loads(session['world_state'])
                sessions.append(session)
            return sessions
    
    async def get_active_session(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get the active session for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM sessions WHERE guild_id = ? AND status = 'active'
                ORDER BY last_played DESC LIMIT 1
            """, (guild_id,))
            row = await cursor.fetchone()
            if row:
                session = dict(row)
                session['world_state'] = json.loads(session['world_state'])
                return session
            return None
    
    async def start_session(self, session_id: int) -> bool:
        """Start a session (set to active)"""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions SET status = 'active', last_played = ? WHERE id = ?
            """, (now, session_id))
            await db.commit()
            return True
    
    async def end_session(self, session_id: int) -> bool:
        """End a session (set to inactive)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions SET status = 'inactive' WHERE id = ?
            """, (session_id,))
            await db.commit()
            return True
    
    async def join_session(self, session_id: int, user_id: int, 
                          character_id: int = None) -> bool:
        """Add a player to a session"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO session_participants (session_id, user_id, character_id, joined_at)
                    VALUES (?, ?, ?, ?)
                """, (session_id, user_id, character_id, now))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                # Already joined, update character if provided
                if character_id:
                    await db.execute("""
                        UPDATE session_participants SET character_id = ?
                        WHERE session_id = ? AND user_id = ?
                    """, (character_id, session_id, user_id))
                    await db.commit()
                return True
    
    async def get_session_participants(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all participants in a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT sp.*, c.name as character_name, c.class as character_class, c.level
                FROM session_participants sp
                LEFT JOIN characters c ON sp.character_id = c.id
                WHERE sp.session_id = ?
            """, (session_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def update_world_state(self, session_id: int, updates: Dict[str, Any]) -> bool:
        """Update the world state for a session"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        world_state = session['world_state']
        world_state.update(updates)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions SET world_state = ? WHERE id = ?
            """, (json.dumps(world_state), session_id))
            await db.commit()
            return True
    
    # ========================================================================
    # DICE ROLL METHODS
    # ========================================================================
    
    async def log_dice_roll(self, user_id: int, guild_id: int, roll_type: str,
                           dice_expression: str, individual_rolls: List[int],
                           modifier: int, total: int, character_id: int = None,
                           purpose: str = None) -> int:
        """Log a dice roll"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO dice_rolls (user_id, guild_id, character_id, roll_type,
                    dice_expression, individual_rolls, modifier, total, purpose, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, guild_id, character_id, roll_type, dice_expression,
                  json.dumps(individual_rolls), modifier, total, purpose, now))
            await db.commit()
            return cursor.lastrowid
    
    async def get_roll_history(self, user_id: int, guild_id: int, 
                              limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent roll history for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM dice_rolls WHERE user_id = ? AND guild_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, guild_id, limit))
            rows = await cursor.fetchall()
            rolls = []
            for row in rows:
                roll = dict(row)
                roll['individual_rolls'] = json.loads(roll['individual_rolls'])
                rolls.append(roll)
            return rolls
    
    # ========================================================================
    # MEMORY METHODS (for AI context)
    # ========================================================================
    
    async def save_memory(self, user_id: int, guild_id: int, key: str, 
                         value: str, context: str = None) -> bool:
        """Save or update a memory about a user"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_memories (user_id, guild_id, memory_key, memory_value, context, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id, memory_key) DO UPDATE SET
                    memory_value = excluded.memory_value,
                    context = excluded.context,
                    updated_at = excluded.updated_at
            """, (user_id, guild_id, key, value, context, now, now))
            await db.commit()
            return True
    
    async def get_all_memories(self, user_id: int, guild_id: int) -> Dict[str, Any]:
        """Get all memories for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM user_memories WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id))
            rows = await cursor.fetchall()
            return {row['memory_key']: {"value": row['memory_value'], "context": row['context']} 
                    for row in rows}
    
    async def delete_memory(self, user_id: int, guild_id: int, key: str) -> bool:
        """Delete a specific memory"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM user_memories WHERE user_id = ? AND guild_id = ? AND memory_key = ?
            """, (user_id, guild_id, key))
            await db.commit()
            return True
    
    # ========================================================================
    # CONVERSATION HISTORY METHODS
    # ========================================================================
    
    async def save_message(self, user_id: int, guild_id: int, channel_id: int,
                          role: str, content: str) -> int:
        """Save a message to conversation history"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO conversation_history (user_id, guild_id, channel_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, guild_id, channel_id, role, content, now))
            await db.commit()
            return cursor.lastrowid
    
    async def get_recent_messages(self, user_id: int, guild_id: int, channel_id: int,
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from conversation history"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM conversation_history 
                WHERE user_id = ? AND guild_id = ? AND channel_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, guild_id, channel_id, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in reversed(rows)]
    
    # ========================================================================
    # STORY LOG METHODS
    # ========================================================================
    
    async def add_story_entry(self, session_id: int, entry_type: str, content: str,
                             participants: List[int] = None) -> int:
        """Add an entry to the story log"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO story_log (session_id, entry_type, content, participants, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, entry_type, content, json.dumps(participants or []), now))
            await db.commit()
            return cursor.lastrowid
    
    async def get_story_log(self, session_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get story log entries for a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM story_log WHERE session_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (session_id, limit))
            rows = await cursor.fetchall()
            entries = []
            for row in reversed(rows):
                entry = dict(row)
                entry['participants'] = json.loads(entry['participants'])
                entries.append(entry)
            return entries
    
    # ========================================================================
    # ADDITIONAL HELPER METHODS (for cogs)
    # ========================================================================
    
    async def get_sessions(self, guild_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get sessions for a guild, optionally filtered by status"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                cursor = await db.execute("""
                    SELECT * FROM sessions WHERE guild_id = ? AND status = ?
                    ORDER BY last_played DESC NULLS LAST
                """, (guild_id, status))
            else:
                cursor = await db.execute("""
                    SELECT * FROM sessions WHERE guild_id = ?
                    ORDER BY last_played DESC NULLS LAST
                """, (guild_id,))
            rows = await cursor.fetchall()
            sessions = []
            for row in rows:
                session = dict(row)
                session['world_state'] = json.loads(session['world_state']) if session.get('world_state') else {}
                sessions.append(session)
            return sessions
    
    async def update_session(self, session_id: int, **kwargs) -> bool:
        """Update session fields"""
        if not kwargs:
            return False
        
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [session_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE sessions SET {fields} WHERE id = ?", values)
            await db.commit()
            return True
    
    async def delete_session(self, session_id: int) -> bool:
        """Delete a session and its participants"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM session_participants WHERE session_id = ?", (session_id,))
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()
            return True
    
    async def add_session_player(self, session_id: int, character_id: int) -> bool:
        """Add a player (via character) to a session"""
        char = await self.get_character(character_id)
        if not char:
            return False
        
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO session_participants (session_id, user_id, character_id, joined_at)
                    VALUES (?, ?, ?, ?)
                """, (session_id, char['user_id'], character_id, now))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False
    
    async def remove_session_player(self, session_id: int, character_id: int) -> bool:
        """Remove a player from a session"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM session_participants 
                WHERE session_id = ? AND character_id = ?
            """, (session_id, character_id))
            await db.commit()
            return True
    
    async def get_session_players(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all players in a session"""
        return await self.get_session_participants(session_id)
    
    async def get_user_active_session(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get the active session that a user is participating in for a guild.
        
        Returns the most recently CREATED session, not the most recently played one,
        to ensure new games take precedence over old ones.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Find active sessions where this user is a participant
            # Order by session ID descending (newest created first) to prioritize new games
            cursor = await db.execute("""
                SELECT s.* FROM sessions s
                INNER JOIN session_participants sp ON s.id = sp.session_id
                WHERE s.guild_id = ? AND sp.user_id = ? AND s.status = 'active'
                ORDER BY s.id DESC
                LIMIT 1
            """, (guild_id, user_id))
            row = await cursor.fetchone()
            if row:
                session = dict(row)
                session['world_state'] = json.loads(session['world_state']) if session.get('world_state') else {}
                return session
            return None
    
    async def get_npcs(self, guild_id: int, location: str = None) -> List[Dict[str, Any]]:
        """Get NPCs for a guild, optionally filtered by location"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if location:
                cursor = await db.execute("""
                    SELECT * FROM npcs WHERE guild_id = ? AND location LIKE ? AND is_alive = 1
                    ORDER BY name
                """, (guild_id, f"%{location}%"))
            else:
                cursor = await db.execute("""
                    SELECT * FROM npcs WHERE guild_id = ? AND is_alive = 1
                    ORDER BY name
                """, (guild_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def update_npc(self, npc_id: int, **kwargs) -> bool:
        """Update NPC fields"""
        if not kwargs:
            return False
        
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [npc_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE npcs SET {fields} WHERE id = ?", values)
            await db.commit()
            return True
    
    async def delete_npc(self, npc_id: int) -> bool:
        """Delete an NPC"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM npc_relationships WHERE npc_id = ?", (npc_id,))
            await db.execute("DELETE FROM npcs WHERE id = ?", (npc_id,))
            await db.commit()
            return True
    
    async def get_quests(self, guild_id: int = None, session_id: int = None, status: str = None) -> List[Dict[str, Any]]:
        """Get quests for a guild or session, optionally filtered by status"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Build query based on parameters
            conditions = []
            params = []
            
            if guild_id:
                conditions.append("guild_id = ?")
                params.append(guild_id)
            
            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor = await db.execute(f"""
                SELECT * FROM quests WHERE {where_clause}
                ORDER BY created_at DESC
            """, params)
            
            rows = await cursor.fetchall()
            quests = []
            for row in rows:
                quest = dict(row)
                quest['objectives'] = json.loads(quest['objectives']) if quest.get('objectives') else []
                quest['rewards'] = json.loads(quest['rewards']) if quest.get('rewards') else {}
                quests.append(quest)
            return quests
            return quests
    
    async def get_quest(self, quest_id: int) -> Optional[Dict[str, Any]]:
        """Get a quest by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM quests WHERE id = ?", (quest_id,))
            row = await cursor.fetchone()
            if row:
                quest = dict(row)
                quest['objectives'] = json.loads(quest['objectives']) if quest.get('objectives') else []
                quest['rewards'] = json.loads(quest['rewards']) if quest.get('rewards') else {}
                return quest
            return None
    
    async def update_quest(self, quest_id: int, **kwargs) -> bool:
        """Update quest fields"""
        if not kwargs:
            return False
        
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [quest_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE quests SET {fields} WHERE id = ?", values)
            await db.commit()
            return True
    
    async def delete_quest(self, quest_id: int) -> bool:
        """Delete a quest"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM quest_progress WHERE quest_id = ?", (quest_id,))
            await db.execute("DELETE FROM quests WHERE id = ?", (quest_id,))
            await db.commit()
            return True
    
    async def equip_item(self, item_id: int, slot: str) -> Dict[str, Any]:
        """Equip an item to a slot"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Get the item
            cursor = await db.execute("SELECT * FROM inventory WHERE id = ?", (item_id,))
            item = await cursor.fetchone()
            if not item:
                return {"error": "Item not found"}
            
            item = dict(item)
            
            # Unequip any item in that slot
            await db.execute("""
                UPDATE inventory SET is_equipped = 0, slot = NULL
                WHERE character_id = ? AND slot = ?
            """, (item['character_id'], slot))
            
            # Equip the new item
            await db.execute("""
                UPDATE inventory SET is_equipped = 1, slot = ?
                WHERE id = ?
            """, (slot, item_id))
            
            await db.commit()
            return {"success": True, "item": item['item_name'], "slot": slot}
    
    async def unequip_item(self, item_id: int) -> bool:
        """Unequip an item"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE inventory SET is_equipped = 0, slot = NULL
                WHERE id = ?
            """, (item_id,))
            await db.commit()
            return True
    
    async def remove_item(self, item_id: int, quantity: int = 1) -> bool:
        """Remove quantity of an item (delete if quantity reaches 0)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT quantity FROM inventory WHERE id = ?", (item_id,))
            row = await cursor.fetchone()
            if not row:
                return False
            
            new_qty = row['quantity'] - quantity
            if new_qty <= 0:
                await db.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
            else:
                await db.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_qty, item_id))
            
            await db.commit()
            return True
    
    async def get_combat_participants(self, encounter_id: int) -> List[Dict[str, Any]]:
        """Get all participants in a combat encounter"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM combat_participants 
                WHERE encounter_id = ?
                ORDER BY turn_order
            """, (encounter_id,))
            rows = await cursor.fetchall()
            participants = []
            for row in rows:
                p = dict(row)
                p['status_effects'] = json.loads(p['status_effects']) if p.get('status_effects') else []
                participants.append(p)
            return participants

    # ========================================================================
    # GAME STATE METHODS
    # ========================================================================
    
    async def get_game_state(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get the current game state for a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM game_state WHERE session_id = ?", 
                (session_id,)
            )
            row = await cursor.fetchone()
            if row:
                state = dict(row)
                state['game_data'] = json.loads(state['game_data']) if state.get('game_data') else {}
                return state
            return None
    
    async def create_game_state(self, session_id: int, **kwargs) -> int:
        """Create a new game state for a session"""
        now = datetime.utcnow().isoformat()
        
        game_data = kwargs.pop('game_data', {})
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO game_state (session_id, last_activity, game_data, 
                    current_scene, current_location, dm_notes, turn_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, 
                now, 
                json.dumps(game_data),
                kwargs.get('current_scene'),
                kwargs.get('current_location'),
                kwargs.get('dm_notes'),
                kwargs.get('turn_count', 0)
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def update_game_state(self, session_id: int, **kwargs) -> bool:
        """Update the game state for a session"""
        if not kwargs:
            return False
        
        now = datetime.utcnow().isoformat()
        kwargs['last_activity'] = now
        
        # Handle game_data specially
        if 'game_data' in kwargs:
            kwargs['game_data'] = json.dumps(kwargs['game_data'])
        
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [session_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE game_state SET {fields} WHERE session_id = ?", values)
            await db.commit()
            return True
    
    async def increment_turn_count(self, session_id: int) -> int:
        """Increment the turn count for a session and return new value"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE game_state SET turn_count = turn_count + 1, last_activity = ?
                WHERE session_id = ?
            """, (datetime.utcnow().isoformat(), session_id))
            await db.commit()
            
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT turn_count FROM game_state WHERE session_id = ?",
                (session_id,)
            )
            row = await cursor.fetchone()
            return row['turn_count'] if row else 0
    
    async def save_game_state(self, session_id: int, **kwargs) -> bool:
        """Save game state - creates if doesn't exist, updates if it does"""
        existing = await self.get_game_state(session_id)
        if existing:
            return await self.update_game_state(session_id, **kwargs)
        else:
            await self.create_game_state(session_id, **kwargs)
            return True
    
    # ========================================================================
    # CHARACTER INTERVIEW METHODS
    # ========================================================================
    
    async def get_character_interview(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get an active character interview"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM character_interviews 
                WHERE user_id = ? AND guild_id = ? AND completed = 0
            """, (user_id, guild_id))
            row = await cursor.fetchone()
            if row:
                interview = dict(row)
                interview['responses'] = json.loads(interview['responses']) if interview.get('responses') else {}
                return interview
            return None
    
    async def create_character_interview(
        self, 
        user_id: int, 
        guild_id: int, 
        dm_channel_id: int = None
    ) -> int:
        """Create a new character interview"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Remove any existing incomplete interview
            await db.execute("""
                DELETE FROM character_interviews 
                WHERE user_id = ? AND guild_id = ? AND completed = 0
            """, (user_id, guild_id))
            
            cursor = await db.execute("""
                INSERT INTO character_interviews 
                (user_id, guild_id, dm_channel_id, stage, responses, started_at, updated_at)
                VALUES (?, ?, ?, 'greeting', '{}', ?, ?)
            """, (user_id, guild_id, dm_channel_id, now, now))
            await db.commit()
            return cursor.lastrowid
    
    async def update_character_interview(
        self, 
        user_id: int, 
        guild_id: int, 
        **kwargs
    ) -> bool:
        """Update a character interview"""
        if not kwargs:
            return False
        
        now = datetime.utcnow().isoformat()
        kwargs['updated_at'] = now
        
        # Handle responses specially
        if 'responses' in kwargs:
            kwargs['responses'] = json.dumps(kwargs['responses'])
        
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [user_id, guild_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"""
                UPDATE character_interviews SET {fields} 
                WHERE user_id = ? AND guild_id = ? AND completed = 0
            """, values)
            await db.commit()
            return True
    
    async def complete_character_interview(self, user_id: int, guild_id: int) -> bool:
        """Mark a character interview as completed"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE character_interviews SET completed = 1, updated_at = ?
                WHERE user_id = ? AND guild_id = ?
            """, (datetime.utcnow().isoformat(), user_id, guild_id))
            await db.commit()
            return True

    # ==================== LOCATION METHODS ====================
    
    async def get_locations(self, session_id: int = None, guild_id: int = None) -> List[Dict]:
        """Get all locations, optionally filtered by session or guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if session_id:
                cursor = await db.execute("""
                    SELECT * FROM locations WHERE session_id = ? ORDER BY name
                """, (session_id,))
            elif guild_id:
                cursor = await db.execute("""
                    SELECT * FROM locations WHERE guild_id = ? ORDER BY name
                """, (guild_id,))
            else:
                cursor = await db.execute("""
                    SELECT * FROM locations ORDER BY name
                """)
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_location(self, location_id: int) -> Optional[Dict]:
        """Get a specific location by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM locations WHERE id = ?
            """, (location_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def create_location(
        self,
        guild_id: int,
        name: str,
        created_by: int,
        session_id: int = None,
        description: str = "",
        location_type: str = "generic",
        points_of_interest: List = None,
        current_weather: str = None,
        danger_level: int = 0,
        hidden_secrets: str = None
    ) -> int:
        """Create a new location"""
        now = datetime.utcnow().isoformat()
        
        # Serialize points_of_interest to JSON
        poi_json = json.dumps(points_of_interest) if points_of_interest else "[]"
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO locations 
                (session_id, guild_id, name, description, type, coordinates, 
                 danger_level, weather, secrets, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, guild_id, name, description, location_type,
                  poi_json, danger_level, current_weather, hidden_secrets, now))
            await db.commit()
            return cursor.lastrowid
            await db.commit()
            return cursor.lastrowid
    
    async def update_location(self, location_id: int, **kwargs) -> bool:
        """Update a location"""
        if not kwargs:
            return False
        
        # Map API field names to DB column names
        if 'location_type' in kwargs:
            kwargs['type'] = kwargs.pop('location_type')
        if 'current_weather' in kwargs:
            kwargs['weather'] = kwargs.pop('current_weather')
        if 'hidden_secrets' in kwargs:
            kwargs['secrets'] = kwargs.pop('hidden_secrets')
        
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [location_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"""
                UPDATE locations SET {fields} WHERE id = ?
            """, values)
            await db.commit()
            return True
    
    async def delete_location(self, location_id: int) -> bool:
        """Delete a location"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM location_connections WHERE from_location_id = ? OR to_location_id = ?", 
                           (location_id, location_id))
            await db.execute("DELETE FROM locations WHERE id = ?", (location_id,))
            await db.commit()
            return True
    
    async def connect_locations(
        self,
        from_location_id: int,
        to_location_id: int,
        direction: str,
        travel_time: int = 1,
        requirements: str = None,
        hidden: bool = False
    ) -> int:
        """Create a connection between two locations"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO location_connections 
                (from_location_id, to_location_id, direction, travel_time, requirements, hidden)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (from_location_id, to_location_id, direction, travel_time, requirements, int(hidden)))
            await db.commit()
            return cursor.lastrowid
    
    async def get_location_connections(self, location_id: int) -> List[Dict]:
        """Get all connections from a location"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT lc.*, l.name as destination_name 
                FROM location_connections lc
                JOIN locations l ON lc.to_location_id = l.id
                WHERE lc.from_location_id = ?
            """, (location_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ==================== STORY ITEMS METHODS ====================
    
    async def get_story_items(self, session_id: int = None, guild_id: int = None) -> List[Dict]:
        """Get all story items, optionally filtered"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if session_id:
                cursor = await db.execute("""
                    SELECT * FROM story_items WHERE session_id = ? ORDER BY name
                """, (session_id,))
            elif guild_id:
                cursor = await db.execute("""
                    SELECT si.* FROM story_items si
                    JOIN sessions s ON si.session_id = s.id
                    WHERE s.guild_id = ? ORDER BY si.name
                """, (guild_id,))
            else:
                cursor = await db.execute("""
                    SELECT * FROM story_items ORDER BY name
                """)
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_story_item(self, item_id: int) -> Optional[Dict]:
        """Get a specific story item by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM story_items WHERE id = ?
            """, (item_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def create_story_item(
        self,
        guild_id: int,
        name: str,
        created_by: int,
        session_id: int = None,
        description: str = "",
        item_type: str = "misc",
        lore: str = None,
        discovery_conditions: str = None,
        dm_notes: str = None
    ) -> int:
        """Create a new story item"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO story_items 
                (session_id, name, description, type, lore, rarity, discovered, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, name, description, item_type, lore, discovery_conditions or "common", 0, now))
            await db.commit()
            return cursor.lastrowid
    
    async def update_story_item(self, item_id: int, **kwargs) -> bool:
        """Update a story item"""
        if not kwargs:
            return False
        
        # Map API field names to DB column names
        if 'is_discovered' in kwargs:
            kwargs['discovered'] = int(kwargs.pop('is_discovered'))
        elif 'discovered' in kwargs:
            kwargs['discovered'] = int(kwargs['discovered'])
        
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [item_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"""
                UPDATE story_items SET {fields} WHERE id = ?
            """, values)
            await db.commit()
            return True
    
    async def delete_story_item(self, item_id: int) -> bool:
        """Delete a story item"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM story_items WHERE id = ?", (item_id,))
            await db.commit()
            return True
    
    async def reveal_story_item(self, item_id: int) -> bool:
        """Mark a story item as discovered"""
        return await self.update_story_item(item_id, discovered=True)

    async def get_story_items_at_location(self, location_id: int) -> List[Dict]:
        """Get all story items at a specific location"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM story_items 
                WHERE location_id = ? AND current_holder_id IS NULL
                ORDER BY name
            """, (location_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ==================== STORY EVENTS METHODS ====================
    
    async def get_story_events(self, session_id: int = None, guild_id: int = None, status: str = None) -> List[Dict]:
        """Get all story events, optionally filtered"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            conditions = []
            params = []
            
            if session_id:
                conditions.append("se.session_id = ?")
                params.append(session_id)
            if guild_id:
                conditions.append("s.guild_id = ?")
                params.append(guild_id)
            if status:
                conditions.append("se.status = ?")
                params.append(status)
            
            if guild_id and not session_id:
                # Need to join with sessions
                query = "SELECT se.* FROM story_events se JOIN sessions s ON se.session_id = s.id"
            else:
                query = "SELECT * FROM story_events se"
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY se.created_at DESC"
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_story_event(self, event_id: int) -> Optional[Dict]:
        """Get a specific story event by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM story_events WHERE id = ?
            """, (event_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def create_story_event(
        self,
        guild_id: int,
        name: str,
        created_by: int,
        session_id: int = None,
        description: str = "",
        event_type: str = "side_event",
        trigger_conditions: str = None,
        dm_notes: str = None
    ) -> int:
        """Create a new story event"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO story_events 
                (session_id, name, description, type, triggers, status, outcomes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, name, description, event_type, trigger_conditions, "pending", dm_notes, now))
            await db.commit()
            return cursor.lastrowid
    
    async def update_story_event(self, event_id: int, **kwargs) -> bool:
        """Update a story event"""
        if not kwargs:
            return False
        
        # Map API field names to DB column names
        if 'trigger_conditions' in kwargs:
            kwargs['triggers'] = kwargs.pop('trigger_conditions')
        
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [event_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"""
                UPDATE story_events SET {fields} WHERE id = ?
            """, values)
            await db.commit()
            return True
    
    async def delete_story_event(self, event_id: int) -> bool:
        """Delete a story event"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM story_events WHERE id = ?", (event_id,))
            await db.commit()
            return True
    
    async def trigger_event(self, event_id: int) -> bool:
        """Mark a story event as triggered"""
        now = datetime.utcnow().isoformat()
        return await self.update_story_event(event_id, status="triggered", triggered_at=now)
    
    async def resolve_event(self, event_id: int, outcome: str = None) -> bool:
        """Mark a story event as resolved"""
        now = datetime.utcnow().isoformat()
        kwargs = {"status": "resolved", "resolved_at": now}
        if outcome:
            kwargs["outcomes"] = outcome
        return await self.update_story_event(event_id, **kwargs)

    # ========================================================================
    # CROSS-SYSTEM WIRING METHODS
    # ========================================================================

    # ==================== CHARACTER LOCATION TRACKING ====================
    
    async def move_character_to_location(self, character_id: int, location_id: int) -> Dict[str, Any]:
        """Move a character to a new location and update related systems"""
        now = datetime.utcnow().isoformat()
        
        # Get current location for story logging
        character = await self.get_character(character_id)
        if not character:
            return {"success": False, "error": "Character not found"}
        
        old_location_id = character.get('current_location_id')
        
        # Get new location details
        new_location = await self.get_location(location_id)
        if not new_location:
            return {"success": False, "error": "Location not found"}
        
        async with aiosqlite.connect(self.db_path) as db:
            # Update character location
            await db.execute("""
                UPDATE characters SET current_location_id = ?, updated_at = ?
                WHERE id = ?
            """, (location_id, now, character_id))
            await db.commit()
        
        # Log the movement if character has a session
        if character.get('session_id'):
            await self.add_story_entry(
                character['session_id'],
                'movement',
                f"{character['name']} traveled to {new_location['name']}",
                participants=[character_id]
            )
        
        return {
            "success": True,
            "character_id": character_id,
            "old_location_id": old_location_id,
            "new_location_id": location_id,
            "location_name": new_location['name']
        }
    
    async def get_characters_at_location(self, location_id: int) -> List[Dict[str, Any]]:
        """Get all characters currently at a location"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM characters 
                WHERE current_location_id = ? AND is_active = 1
            """, (location_id,))
            rows = await cursor.fetchall()
            return [self._normalize_character(dict(row)) for row in rows]

    # ==================== NPC LOCATION WIRING ====================
    
    async def move_npc_to_location(self, npc_id: int, location_id: int) -> bool:
        """Move an NPC to a location (updates both location_id and location text)"""
        location = await self.get_location(location_id)
        if not location:
            return False
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE npcs SET location_id = ?, location = ?
                WHERE id = ?
            """, (location_id, location['name'], npc_id))
            await db.commit()
            return True
    
    async def get_npcs_at_location(self, location_id: int) -> List[Dict[str, Any]]:
        """Get all NPCs at a specific location"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM npcs 
                WHERE location_id = ? AND is_alive = 1
            """, (location_id,))
            rows = await cursor.fetchall()
            npcs = []
            for row in rows:
                npc = dict(row)
                if npc.get('stats'):
                    npc['stats'] = json.loads(npc['stats'])
                if npc.get('merchant_inventory'):
                    npc['merchant_inventory'] = json.loads(npc['merchant_inventory'])
                npcs.append(npc)
            return npcs

    # ==================== COMBAT-CHARACTER SYNC ====================
    
    async def sync_combat_damage_to_character(self, participant_id: int) -> Dict[str, Any]:
        """Sync combat participant HP back to the character table"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get combat participant
            cursor = await db.execute("""
                SELECT * FROM combat_participants WHERE id = ?
            """, (participant_id,))
            participant = await cursor.fetchone()
            
            if not participant or not participant['is_player']:
                return {"success": False, "error": "Participant not found or not a player"}
            
            participant = dict(participant)
            
            # Update the character's HP
            await db.execute("""
                UPDATE characters SET hp = ?, updated_at = ?
                WHERE id = ?
            """, (participant['current_hp'], datetime.utcnow().isoformat(), participant['participant_id']))
            await db.commit()
            
            return {
                "success": True,
                "character_id": participant['participant_id'],
                "new_hp": participant['current_hp'],
                "max_hp": participant['max_hp']
            }
    
    async def sync_all_combat_to_characters(self, encounter_id: int) -> List[Dict[str, Any]]:
        """Sync all player participant HP back to character tables after combat"""
        combatants = await self.get_combatants(encounter_id)
        results = []
        
        for combatant in combatants:
            if combatant['is_player']:
                result = await self.sync_combat_damage_to_character(combatant['id'])
                results.append(result)
        
        return results
    
    async def award_combat_experience(self, encounter_id: int, xp_per_character: int) -> List[Dict[str, Any]]:
        """Award XP to all surviving player characters after combat"""
        combatants = await self.get_combatants(encounter_id)
        results = []
        
        for combatant in combatants:
            if combatant['is_player'] and combatant['current_hp'] > 0:
                result = await self.add_experience(combatant['participant_id'], xp_per_character)
                results.append({
                    "character_id": combatant['participant_id'],
                    "name": combatant['name'],
                    "xp_gained": xp_per_character,
                    **result
                })
        
        return results
    
    async def end_combat_with_rewards(self, encounter_id: int, xp_per_character: int = 0, 
                                       gold_per_character: int = 0, loot_items: List[Dict] = None) -> Dict[str, Any]:
        """End combat, sync HP, and distribute rewards"""
        # Sync all HP
        hp_results = await self.sync_all_combat_to_characters(encounter_id)
        
        # Award XP
        xp_results = []
        if xp_per_character > 0:
            xp_results = await self.award_combat_experience(encounter_id, xp_per_character)
        
        # Award gold
        gold_results = []
        if gold_per_character > 0:
            combatants = await self.get_combatants(encounter_id)
            for combatant in combatants:
                if combatant['is_player'] and combatant['current_hp'] > 0:
                    new_gold = await self.update_gold(combatant['participant_id'], gold_per_character)
                    gold_results.append({
                        "character_id": combatant['participant_id'],
                        "name": combatant['name'],
                        "gold_gained": gold_per_character,
                        "new_total": new_gold
                    })
        
        # Distribute loot (to first surviving player for simplicity)
        loot_results = []
        if loot_items:
            combatants = await self.get_combatants(encounter_id)
            survivors = [c for c in combatants if c['is_player'] and c['current_hp'] > 0]
            if survivors:
                for item in loot_items:
                    item_id = await self.add_item(
                        survivors[0]['participant_id'],
                        item.get('item_id', ''),
                        item.get('name', 'Unknown Item'),
                        item.get('type', 'misc'),
                        quantity=item.get('quantity', 1),
                        properties=item.get('properties', {})
                    )
                    loot_results.append({
                        "item_name": item.get('name'),
                        "given_to": survivors[0]['name'],
                        "inventory_id": item_id
                    })
        
        # End the combat
        await self.end_combat(encounter_id)
        
        # Get combat info for story logging
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT session_id FROM combat_encounters WHERE id = ?", (encounter_id,))
            combat = await cursor.fetchone()
            
            if combat and combat['session_id']:
                await self.add_story_entry(
                    combat['session_id'],
                    'combat_end',
                    f"Combat ended. XP: {xp_per_character}, Gold: {gold_per_character}",
                    participants=[c['participant_id'] for c in combatants if c['is_player']]
                )
        
        return {
            "success": True,
            "hp_synced": hp_results,
            "xp_awarded": xp_results,
            "gold_awarded": gold_results,
            "loot_distributed": loot_results
        }

    # ==================== QUEST REWARD WIRING ====================
    
    async def complete_quest_with_rewards(self, quest_id: int, character_id: int) -> Dict[str, Any]:
        """Complete a quest and automatically grant rewards to the character"""
        quest = await self.get_quest(quest_id)
        if not quest:
            return {"success": False, "error": "Quest not found"}
        
        character = await self.get_character(character_id)
        if not character:
            return {"success": False, "error": "Character not found"}
        
        # Parse rewards
        rewards = quest.get('rewards', {})
        if isinstance(rewards, str):
            rewards = json.loads(rewards)
        
        results = {
            "quest_title": quest['title'],
            "character_name": character['name'],
            "xp_gained": 0,
            "gold_gained": 0,
            "items_gained": [],
            "leveled_up": False,
            "new_level": character['level']
        }
        
        # Award XP
        if rewards.get('experience') or rewards.get('xp'):
            xp = rewards.get('experience') or rewards.get('xp')
            xp_result = await self.add_experience(character_id, xp)
            results['xp_gained'] = xp
            results['leveled_up'] = xp_result.get('leveled_up', False)
            results['new_level'] = xp_result.get('new_level', character['level'])
        
        # Award gold
        if rewards.get('gold'):
            new_gold = await self.update_gold(character_id, rewards['gold'])
            results['gold_gained'] = rewards['gold']
            results['new_gold_total'] = new_gold
        
        # Award items
        if rewards.get('items'):
            for item in rewards['items']:
                item_id = await self.add_item(
                    character_id,
                    item.get('item_id', ''),
                    item.get('name', item.get('item_name', 'Unknown')),
                    item.get('type', item.get('item_type', 'misc')),
                    quantity=item.get('quantity', 1),
                    properties=item.get('properties', {})
                )
                results['items_gained'].append({
                    "name": item.get('name', item.get('item_name')),
                    "inventory_id": item_id
                })
        
        # Mark quest as completed
        await self.complete_quest(quest_id, character_id)
        
        # Log to story
        if character.get('session_id'):
            await self.add_story_entry(
                character['session_id'],
                'quest_complete',
                f"{character['name']} completed quest: {quest['title']}. Rewards: {results['xp_gained']} XP, {results['gold_gained']} gold",
                participants=[character_id]
            )
        
        results['success'] = True
        return results

    # ==================== STORY ITEM TO INVENTORY WIRING ====================
    
    async def pickup_story_item(self, story_item_id: int, character_id: int) -> Dict[str, Any]:
        """Have a character pick up a story item (marks discovered, sets holder, adds to inventory)"""
        now = datetime.utcnow().isoformat()
        
        story_item = await self.get_story_item(story_item_id)
        if not story_item:
            return {"success": False, "error": "Story item not found"}
        
        character = await self.get_character(character_id)
        if not character:
            return {"success": False, "error": "Character not found"}
        
        # Update story item
        await self.update_story_item(story_item_id, 
                                      is_discovered=1,
                                      discovered_by=character_id,
                                      discovered_at=now,
                                      current_holder_id=character_id,
                                      location_id=None)  # No longer at a location
        
        # Add to character inventory
        properties = story_item.get('properties', {})
        if isinstance(properties, str):
            properties = json.loads(properties)
        properties['is_story_item'] = True
        properties['story_item_id'] = story_item_id
        properties['lore'] = story_item.get('lore', '')
        
        inventory_id = await self.add_item(
            character_id,
            f"story_item_{story_item_id}",
            story_item['name'],
            story_item.get('item_type', 'key_item'),
            quantity=1,
            properties=properties
        )
        
        # Log to story
        if character.get('session_id'):
            await self.add_story_entry(
                character['session_id'],
                'item_discovery',
                f"{character['name']} discovered: {story_item['name']}",
                participants=[character_id]
            )
        
        return {
            "success": True,
            "story_item": story_item['name'],
            "character": character['name'],
            "inventory_id": inventory_id
        }
    
    async def drop_story_item(self, story_item_id: int, location_id: int = None) -> Dict[str, Any]:
        """Drop a story item (removes from holder, optionally places at location)"""
        story_item = await self.get_story_item(story_item_id)
        if not story_item:
            return {"success": False, "error": "Story item not found"}
        
        holder_id = story_item.get('current_holder_id')
        
        # Remove from inventory if currently held
        if holder_id:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM inventory 
                    WHERE character_id = ? AND item_id = ?
                """, (holder_id, f"story_item_{story_item_id}"))
                await db.commit()
        
        # Update story item
        await self.update_story_item(story_item_id,
                                      current_holder_id=None,
                                      location_id=location_id)
        
        return {
            "success": True,
            "story_item": story_item['name'],
            "new_location_id": location_id
        }

    # ==================== SESSION INITIALIZATION ====================
    
    async def initialize_session(self, session_id: int) -> Dict[str, Any]:
        """Ensure a session has all required related records (game_state, etc.)"""
        session = await self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        results = {"session_id": session_id, "initialized": []}
        
        # Ensure game_state exists
        game_state = await self.get_game_state(session_id)
        if not game_state:
            await self.create_game_state(session_id, 
                                         current_scene="Session beginning",
                                         current_location="Unknown")
            results['initialized'].append('game_state')
        
        results['success'] = True
        return results
    
    async def start_session_with_init(self, session_id: int) -> Dict[str, Any]:
        """Start a session and ensure it's fully initialized"""
        # Initialize
        init_result = await self.initialize_session(session_id)
        if not init_result.get('success'):
            return init_result
        
        # Start the session
        await self.start_session(session_id)
        
        # Log story entry
        await self.add_story_entry(session_id, 'session_start', 'The adventure begins!')
        
        return {
            "success": True,
            "session_id": session_id,
            "initialized": init_result.get('initialized', [])
        }

    # ==================== STORY EVENT CHARACTER WIRING ====================
    
    async def add_character_to_event(self, event_id: int, character_id: int) -> bool:
        """Add a character to a story event's involved_characters"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT involved_characters FROM story_events WHERE id = ?
            """, (event_id,))
            row = await cursor.fetchone()
            
            if not row:
                return False
            
            involved = json.loads(row['involved_characters']) if row['involved_characters'] else []
            if character_id not in involved:
                involved.append(character_id)
                await db.execute("""
                    UPDATE story_events SET involved_characters = ?
                    WHERE id = ?
                """, (json.dumps(involved), event_id))
                await db.commit()
            
            return True
    
    async def get_events_for_character(self, character_id: int) -> List[Dict]:
        """Get all story events involving a character"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM story_events 
                WHERE involved_characters LIKE ?
            """, (f'%{character_id}%',))
            rows = await cursor.fetchall()
            
            # Filter to ensure exact match (not partial ID matches)
            events = []
            for row in rows:
                event = dict(row)
                involved = json.loads(event['involved_characters']) if event.get('involved_characters') else []
                if character_id in involved:
                    events.append(event)
            
            return events

    # ==================== DICE ROLL SESSION WIRING ====================
    
    async def log_dice_roll_with_session(self, user_id: int, guild_id: int, roll_type: str,
                                          dice_expression: str, individual_rolls: List[int],
                                          modifier: int, total: int, purpose: str = None,
                                          character_id: int = None, session_id: int = None) -> int:
        """Log a dice roll with session tracking"""
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO dice_rolls (user_id, guild_id, session_id, character_id, roll_type,
                    dice_expression, individual_rolls, modifier, total, purpose, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, guild_id, session_id, character_id, roll_type,
                  dice_expression, json.dumps(individual_rolls), modifier, total, purpose, now))
            await db.commit()
            return cursor.lastrowid
    
    async def get_session_roll_history(self, session_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get dice roll history for a specific session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT dr.*, c.name as character_name
                FROM dice_rolls dr
                LEFT JOIN characters c ON dr.character_id = c.id
                WHERE dr.session_id = ?
                ORDER BY dr.created_at DESC
                LIMIT ?
            """, (session_id, limit))
            rows = await cursor.fetchall()
            
            rolls = []
            for row in rows:
                roll = dict(row)
                roll['individual_rolls'] = json.loads(roll['individual_rolls'])
                rolls.append(roll)
            return rolls

    # ==================== LOCATION EXPLORATION HELPERS ====================
    
    async def explore_location(self, character_id: int, location_id: int) -> Dict[str, Any]:
        """Have a character explore a location - reveals NPCs, items, connections"""
        character = await self.get_character(character_id)
        if not character:
            return {"success": False, "error": "Character not found"}
        
        location = await self.get_location(location_id)
        if not location:
            return {"success": False, "error": "Location not found"}
        
        # Move character to location
        await self.move_character_to_location(character_id, location_id)
        
        # Get NPCs at location
        npcs = await self.get_npcs_at_location(location_id)
        
        # Get other characters at location
        other_characters = await self.get_characters_at_location(location_id)
        other_characters = [c for c in other_characters if c['id'] != character_id]
        
        # Get connected locations
        connections = await self.get_location_connections(location_id)
        
        # Get story items at location
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM story_items 
                WHERE location_id = ? AND is_discovered = 0
            """, (location_id,))
            hidden_items = [dict(row) for row in await cursor.fetchall()]
            
            cursor = await db.execute("""
                SELECT * FROM story_items 
                WHERE location_id = ? AND is_discovered = 1
            """, (location_id,))
            visible_items = [dict(row) for row in await cursor.fetchall()]
        
        # Log exploration
        if character.get('session_id'):
            await self.add_story_entry(
                character['session_id'],
                'exploration',
                f"{character['name']} explored {location['name']}",
                participants=[character_id]
            )
        
        return {
            "success": True,
            "location": location,
            "npcs": npcs,
            "other_characters": other_characters,
            "connections": connections,
            "visible_items": visible_items,
            "hidden_items_count": len(hidden_items),
            "danger_level": location.get('danger_level', 0),
            "weather": location.get('current_weather'),
            "secrets": location.get('hidden_secrets')
        }

    # ==================== REST/RECOVERY WIRING ====================
    
    async def long_rest(self, character_id: int) -> Dict[str, Any]:
        """Perform a long rest - restore HP, spell slots, abilities, skills"""
        character = await self.get_character(character_id)
        if not character:
            return {"success": False, "error": "Character not found"}
        
        results = {"character_name": character['name'], "restored": []}
        
        # Restore HP to max
        if character['hp'] < character['max_hp']:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE characters SET hp = max_hp, updated_at = ?
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), character_id))
                await db.commit()
            results['restored'].append(f"HP restored to {character['max_hp']}")
        
        # Restore spell slots
        await self.restore_spell_slots(character_id, full=True)
        results['restored'].append("All spell slots restored")
        
        # Restore abilities
        await self.restore_abilities(character_id, recharge_type='long_rest')
        results['restored'].append("Long rest abilities restored")
        
        # Restore skills
        await self.restore_skills(character_id, recharge_type='long_rest')
        results['restored'].append("Long rest skills restored")
        
        # Clear temporary status effects
        cleared = await self.clear_status_effects(character_id, effect_type='debuff')
        if cleared:
            results['restored'].append("Temporary debuffs cleared")
        
        # Log to story
        if character.get('session_id'):
            await self.add_story_entry(
                character['session_id'],
                'rest',
                f"{character['name']} completed a long rest",
                participants=[character_id]
            )
        
        results['success'] = True
        return results
    
    async def short_rest(self, character_id: int) -> Dict[str, Any]:
        """Perform a short rest - partial recovery"""
        character = await self.get_character(character_id)
        if not character:
            return {"success": False, "error": "Character not found"}
        
        results = {"character_name": character['name'], "restored": []}
        
        # Restore some HP (e.g., 25% of max)
        hp_restore = character['max_hp'] // 4
        if character['hp'] < character['max_hp']:
            new_hp = min(character['hp'] + hp_restore, character['max_hp'])
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE characters SET hp = ?, updated_at = ?
                    WHERE id = ?
                """, (new_hp, datetime.utcnow().isoformat(), character_id))
                await db.commit()
            results['restored'].append(f"HP restored by {hp_restore} (now {new_hp})")
        
        # Restore short rest abilities
        await self.restore_abilities(character_id, recharge_type='short_rest')
        results['restored'].append("Short rest abilities restored")
        
        # Restore short rest skills
        await self.restore_skills(character_id, recharge_type='short_rest')
        results['restored'].append("Short rest skills restored")
        
        # Reduce all cooldowns by 1
        await self.reduce_cooldowns(character_id, amount=1)
        results['restored'].append("Cooldowns reduced")
        
        results['success'] = True
        return results

    # ==================== FULL SESSION STATE ====================
    
    async def get_comprehensive_session_state(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get absolutely everything about a session for save/load or AI context"""
        session = await self.get_full_session_state(session_id)
        if not session:
            return None
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get game state
            game_state = await self.get_game_state(session_id)
            
            # Get all story events
            cursor = await db.execute("""
                SELECT * FROM story_events WHERE session_id = ?
            """, (session_id,))
            story_events = [dict(row) for row in await cursor.fetchall()]
            
            # Get all story items
            cursor = await db.execute("""
                SELECT * FROM story_items WHERE session_id = ?
            """, (session_id,))
            story_items = [dict(row) for row in await cursor.fetchall()]
            
            # Get story log
            story_log = await self.get_story_log(session_id)
            
            # Get active combat if any
            cursor = await db.execute("""
                SELECT * FROM combat_encounters 
                WHERE session_id = ? AND status = 'active'
            """, (session_id,))
            active_combat = await cursor.fetchone()
            if active_combat:
                active_combat = dict(active_combat)
                active_combat['combatants'] = await self.get_combatants(active_combat['id'])
            
            # Get character details including inventory, spells, skills
            characters_full = []
            for participant in session.get('participants', []):
                if participant.get('character_id'):
                    char = await self.get_character(participant['character_id'])
                    if char:
                        char['inventory'] = await self.get_inventory(char['id'])
                        char['spells'] = await self.get_character_spells(char['id'])
                        char['abilities'] = await self.get_character_abilities(char['id'])
                        char['skills'] = await self.get_character_skills(char['id'])
                        char['status_effects'] = await self.get_status_effects(char['id'])
                        char['spell_slots'] = await self.get_spell_slots(char['id'])
                        characters_full.append(char)
        
        return {
            **session,
            'game_state': game_state,
            'story_events': story_events,
            'story_items': story_items,
            'story_log': story_log,
            'active_combat': active_combat,
            'characters_full': characters_full
        }

    # ==================== MISSING WIRING METHODS ====================
    
    async def get_nearby_locations(self, location_id: int) -> List[Dict]:
        """Get all connected locations (bidirectional) from a location"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Get both outgoing and incoming connections
            cursor = await db.execute("""
                SELECT lc.*, l.name as to_name, l.location_type, l.danger_level, l.description
                FROM location_connections lc
                JOIN locations l ON lc.to_location_id = l.id
                WHERE lc.from_location_id = ? AND lc.hidden = 0
                UNION
                SELECT lc.id, lc.to_location_id as from_location_id, lc.from_location_id as to_location_id,
                       CASE lc.direction 
                           WHEN 'north' THEN 'south'
                           WHEN 'south' THEN 'north'
                           WHEN 'east' THEN 'west'
                           WHEN 'west' THEN 'east'
                           WHEN 'up' THEN 'down'
                           WHEN 'down' THEN 'up'
                           ELSE lc.direction
                       END as direction,
                       lc.travel_time, lc.requirements, lc.hidden,
                       l.name as to_name, l.location_type, l.danger_level, l.description
                FROM location_connections lc
                JOIN locations l ON lc.from_location_id = l.id
                WHERE lc.to_location_id = ? AND lc.bidirectional = 1 AND lc.hidden = 0
            """, (location_id, location_id))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_active_events(self, session_id: int) -> List[Dict]:
        """Get all active (triggered but not resolved) story events for a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            try:
                cursor = await db.execute("""
                    SELECT * FROM story_events 
                    WHERE session_id = ? AND status = 'active'
                    ORDER BY COALESCE(priority, 0) DESC, COALESCE(triggered_at, created_at) DESC
                """, (session_id,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception:
                # Fallback without priority/triggered_at ordering if columns don't exist
                try:
                    cursor = await db.execute("""
                        SELECT * FROM story_events 
                        WHERE session_id = ? AND status = 'active'
                        ORDER BY created_at DESC
                    """, (session_id,))
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                except Exception:
                    return []  # Table might not exist
    
    async def get_pending_events(self, session_id: int) -> List[Dict]:
        """Get all pending (not yet triggered) story events for a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            try:
                cursor = await db.execute("""
                    SELECT * FROM story_events 
                    WHERE session_id = ? AND status = 'pending'
                    ORDER BY COALESCE(priority, 0) DESC, created_at DESC
                """, (session_id,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception:
                # Fallback without priority ordering
                try:
                    cursor = await db.execute("""
                        SELECT * FROM story_events 
                        WHERE session_id = ? AND status = 'pending'
                        ORDER BY created_at DESC
                    """, (session_id,))
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                except Exception:
                    return []  # Table might not exist
    
    async def get_combat_for_channel(self, session_id: int, channel_id: int) -> Optional[Dict]:
        """Get active combat for a specific channel in a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM combat_encounters 
                WHERE session_id = ? AND channel_id = ? AND status = 'active'
                ORDER BY created_at DESC LIMIT 1
            """, (session_id, channel_id))
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def transfer_story_item(self, item_id: int, new_holder_id: int = None, holder_type: str = 'none') -> bool:
        """Transfer a story item to a new holder (character, npc, location, or none)"""
        async with aiosqlite.connect(self.db_path) as db:
            if holder_type == 'none' or new_holder_id is None:
                await db.execute("""
                    UPDATE story_items 
                    SET current_holder_id = NULL, location_id = NULL
                    WHERE id = ?
                """, (item_id,))
            elif holder_type == 'character':
                await db.execute("""
                    UPDATE story_items 
                    SET current_holder_id = ?, location_id = NULL
                    WHERE id = ?
                """, (new_holder_id, item_id))
            elif holder_type == 'location':
                await db.execute("""
                    UPDATE story_items 
                    SET current_holder_id = NULL, location_id = ?
                    WHERE id = ?
                """, (new_holder_id, item_id))
            await db.commit()
            return True
    
    async def add_story_log_entry(self, session_id: int, entry_type: str, content: str, 
                                   participants: List[int] = None) -> int:
        """Add an entry to the story log (alias for add_story_entry for consistency)"""
        return await self.add_story_entry(session_id, entry_type, content, participants)
