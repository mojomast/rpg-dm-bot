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
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
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
                    npc_type TEXT DEFAULT 'neutral',
                    is_merchant INTEGER DEFAULT 0,
                    merchant_inventory TEXT DEFAULT '[]',
                    dialogue_context TEXT,
                    stats TEXT DEFAULT '{}',
                    is_alive INTEGER DEFAULT 1,
                    created_by INTEGER NOT NULL,
                    created_at TEXT NOT NULL
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
                    character_id INTEGER,
                    roll_type TEXT NOT NULL,
                    dice_expression TEXT NOT NULL,
                    individual_rolls TEXT NOT NULL,
                    modifier INTEGER DEFAULT 0,
                    total INTEGER NOT NULL,
                    purpose TEXT,
                    created_at TEXT NOT NULL
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
            
            await db.commit()
    
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
                await db.execute("""
                    INSERT INTO npc_relationships (npc_id, character_id, reputation, 
                        relationship_notes, last_interaction)
                    VALUES (?, ?, ?, ?, ?)
                """, (npc_id, character_id, reputation_change, notes, now))
                await db.commit()
                return reputation_change
    
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
        """Get the active session that a user is participating in for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Find active sessions where this user is a participant
            cursor = await db.execute("""
                SELECT s.* FROM sessions s
                INNER JOIN session_participants sp ON s.id = sp.session_id
                WHERE s.guild_id = ? AND sp.user_id = ? AND s.status = 'active'
                ORDER BY s.last_played DESC NULLS LAST
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
    
    async def update_gold(self, character_id: int, amount: int) -> bool:
        """Add or subtract gold from a character"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE characters SET gold = gold + ?, updated_at = ?
                WHERE id = ?
            """, (amount, datetime.utcnow().isoformat(), character_id))
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
