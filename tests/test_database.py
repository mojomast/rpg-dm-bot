"""
Unit tests for src/database.py
Tests all CRUD operations for characters, inventory, quests, NPCs, combat, and sessions.
"""

import pytest
from datetime import datetime


# =============================================================================
# CHARACTER TESTS
# =============================================================================

class TestCharacters:
    """Tests for character CRUD operations"""

    async def test_create_character(self, db, sample_character_stats):
        """Test creating a new character"""
        char_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Theron",
            race="elf",
            char_class="ranger",
            stats=sample_character_stats,
            backstory="A wandering ranger"
        )
        
        assert char_id is not None
        assert char_id > 0
        
        # Verify character was created correctly
        char = await db.get_character(char_id)
        assert char is not None
        assert char['name'] == "Theron"
        assert char['race'] == "elf"
        assert char['char_class'] == "ranger"
        assert char['level'] == 1
        assert char['strength'] == 16
        assert char['is_active'] == 1

    async def test_create_character_hp_calculation(self, db):
        """Test HP is calculated correctly based on class and constitution"""
        # Warrior (12 base HP) with 15 CON (+2 mod) = 14 HP
        char_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Tank",
            race="dwarf",
            char_class="warrior",
            stats={"constitution": 15, "strength": 14, "dexterity": 10,
                   "intelligence": 8, "wisdom": 10, "charisma": 8}
        )
        
        char = await db.get_character(char_id)
        assert char['max_hp'] == 14  # 12 + 2 (con mod)
        
        # Mage (6 base HP) with 10 CON (+0 mod) = 6 HP
        mage_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Wizard",
            race="elf",
            char_class="mage",
            stats={"constitution": 10, "intelligence": 16, "wisdom": 14,
                   "strength": 8, "dexterity": 12, "charisma": 10}
        )
        
        mage = await db.get_character(mage_id)
        assert mage['max_hp'] == 6  # 6 + 0 (con mod)
        assert mage['max_mana'] > 0  # Mage should have mana

    async def test_get_active_character(self, db_with_character):
        """Test retrieving user's active character"""
        db, char_id = db_with_character
        
        char = await db.get_active_character(user_id=12345, guild_id=67890)
        assert char is not None
        assert char['id'] == char_id
        assert char['name'] == "Test Hero"

    async def test_get_active_character_no_character(self, db):
        """Test retrieving active character when none exists"""
        char = await db.get_active_character(user_id=99999, guild_id=67890)
        assert char is None

    async def test_get_user_characters(self, db, sample_character_stats):
        """Test getting all characters for a user"""
        # Create multiple characters
        for name in ["Hero1", "Hero2", "Hero3"]:
            await db.create_character(
                user_id=12345,
                guild_id=67890,
                name=name,
                race="human",
                char_class="warrior",
                stats=sample_character_stats
            )
        
        chars = await db.get_user_characters(user_id=12345, guild_id=67890)
        assert len(chars) == 3

    async def test_update_character(self, db_with_character):
        """Test updating character fields"""
        db, char_id = db_with_character
        
        await db.update_character(char_id, hp=5, gold=100)
        
        char = await db.get_character(char_id)
        assert char['hp'] == 5
        assert char['gold'] == 100

    async def test_set_active_character(self, db, sample_character_stats):
        """Test setting a character as active deactivates others"""
        # Create two characters
        char1_id = await db.create_character(
            user_id=12345, guild_id=67890, name="Hero1",
            race="human", char_class="warrior", stats=sample_character_stats
        )
        char2_id = await db.create_character(
            user_id=12345, guild_id=67890, name="Hero2",
            race="elf", char_class="mage", stats=sample_character_stats
        )
        
        # Set char2 as active
        await db.set_active_character(user_id=12345, guild_id=67890, character_id=char2_id)
        
        char1 = await db.get_character(char1_id)
        char2 = await db.get_character(char2_id)
        
        assert char1['is_active'] == 0
        assert char2['is_active'] == 1

    async def test_add_experience_no_level_up(self, db_with_character):
        """Test adding XP without level up"""
        db, char_id = db_with_character
        
        result = await db.add_experience(char_id, 100)
        
        assert result['xp_gained'] == 100
        assert result['total_xp'] == 100
        assert result['leveled_up'] is False
        assert result['new_level'] == 1

    async def test_add_experience_with_level_up(self, db_with_character):
        """Test adding enough XP to level up"""
        db, char_id = db_with_character
        
        # Level 2 requires 300 XP
        result = await db.add_experience(char_id, 350)
        
        assert result['leveled_up'] is True
        assert result['new_level'] == 2
        assert result['hp_increase'] > 0

    async def test_add_experience_character_not_found(self, db):
        """Test adding XP to non-existent character"""
        result = await db.add_experience(99999, 100)
        assert 'error' in result


# =============================================================================
# INVENTORY TESTS
# =============================================================================

class TestInventory:
    """Tests for inventory operations"""

    async def test_add_item(self, db_with_character, sample_item):
        """Test adding an item to inventory"""
        db, char_id = db_with_character
        
        inv_id = await db.add_item(
            character_id=char_id,
            item_id=sample_item['id'],
            item_name=sample_item['name'],
            item_type=sample_item['type'],
            quantity=1,
            properties=sample_item['properties']
        )
        
        assert inv_id is not None
        
        inventory = await db.get_inventory(char_id)
        assert len(inventory) == 1
        assert inventory[0]['item_name'] == "Iron Sword"

    async def test_add_stackable_items(self, db_with_character):
        """Test that consumables stack properly"""
        db, char_id = db_with_character
        
        # Add health potion
        await db.add_item(char_id, "health_potion", "Health Potion", "consumable", 2)
        # Add more health potions
        await db.add_item(char_id, "health_potion", "Health Potion", "consumable", 3)
        
        inventory = await db.get_inventory(char_id)
        assert len(inventory) == 1  # Should be stacked
        assert inventory[0]['quantity'] == 5

    async def test_equip_item(self, db_with_character, sample_item):
        """Test equipping an item"""
        db, char_id = db_with_character
        
        inv_id = await db.add_item(
            char_id, sample_item['id'], sample_item['name'],
            sample_item['type'], 1, sample_item['properties']
        )
        
        result = await db.equip_item(inv_id, "main_hand")
        
        assert result['success'] is True
        assert result['slot'] == "main_hand"
        
        equipped = await db.get_equipped_items(char_id)
        assert len(equipped) == 1
        assert equipped[0]['slot'] == "main_hand"

    async def test_equip_item_replaces_slot(self, db_with_character):
        """Test that equipping an item unequips the previous item in that slot"""
        db, char_id = db_with_character
        
        # Add and equip first sword
        inv_id1 = await db.add_item(char_id, "iron_sword", "Iron Sword", "weapon", 1)
        await db.equip_item(inv_id1, "main_hand")
        
        # Add and equip second sword
        inv_id2 = await db.add_item(char_id, "steel_sword", "Steel Sword", "weapon", 1)
        await db.equip_item(inv_id2, "main_hand")
        
        equipped = await db.get_equipped_items(char_id)
        assert len(equipped) == 1
        assert equipped[0]['item_name'] == "Steel Sword"

    async def test_unequip_item(self, db_with_character, sample_item):
        """Test unequipping an item"""
        db, char_id = db_with_character
        
        inv_id = await db.add_item(
            char_id, sample_item['id'], sample_item['name'],
            sample_item['type'], 1
        )
        await db.equip_item(inv_id, "main_hand")
        await db.unequip_item(inv_id)
        
        equipped = await db.get_equipped_items(char_id)
        assert len(equipped) == 0

    async def test_remove_item(self, db_with_character):
        """Test removing items from inventory"""
        db, char_id = db_with_character
        
        inv_id = await db.add_item(char_id, "gold_coin", "Gold Coins", "currency", 100)
        
        # Remove some
        await db.remove_item(inv_id, 30)
        inventory = await db.get_inventory(char_id)
        assert inventory[0]['quantity'] == 70
        
        # Remove all remaining
        await db.remove_item(inv_id, 100)
        inventory = await db.get_inventory(char_id)
        assert len(inventory) == 0

    async def test_update_gold(self, db_with_character):
        """Test updating character gold"""
        db, char_id = db_with_character
        
        # Add gold
        new_gold = await db.update_gold(char_id, 100)
        assert new_gold == 100
        
        # Remove gold
        new_gold = await db.update_gold(char_id, -30)
        assert new_gold == 70
        
        # Cannot go negative
        new_gold = await db.update_gold(char_id, -200)
        assert new_gold == 0


# =============================================================================
# QUEST TESTS
# =============================================================================

class TestQuests:
    """Tests for quest operations"""

    async def test_create_quest(self, db):
        """Test creating a new quest"""
        quest_id = await db.create_quest(
            guild_id=67890,
            title="Dragon's Lair",
            description="Slay the dragon terrorizing the village",
            objectives=[
                {"description": "Find the dragon's lair", "completed": False},
                {"description": "Defeat the dragon", "completed": False}
            ],
            rewards={"gold": 500, "xp": 200},
            created_by=12345,
            difficulty="hard"
        )
        
        assert quest_id is not None
        
        quest = await db.get_quest(quest_id)
        assert quest['title'] == "Dragon's Lair"
        assert quest['difficulty'] == "hard"
        assert len(quest['objectives']) == 2
        assert quest['rewards']['gold'] == 500

    async def test_get_available_quests(self, db):
        """Test getting available quests"""
        # Create multiple quests
        await db.create_quest(
            guild_id=67890, title="Quest 1", description="First quest",
            objectives=[], rewards={}, created_by=12345
        )
        await db.create_quest(
            guild_id=67890, title="Quest 2", description="Second quest",
            objectives=[], rewards={}, created_by=12345
        )
        
        quests = await db.get_available_quests(guild_id=67890)
        assert len(quests) == 2

    async def test_accept_quest(self, db_with_full_setup):
        """Test accepting a quest"""
        data = db_with_full_setup
        
        result = await data['db'].accept_quest(
            quest_id=data['quest_id'],
            character_id=data['character_id']
        )
        
        assert result['success'] is True
        
        # Verify quest is in character's quests
        quests = await data['db'].get_character_quests(data['character_id'])
        assert len(quests) == 1
        assert quests[0]['title'] == "The Missing Merchant"

    async def test_accept_quest_already_accepted(self, db_with_full_setup):
        """Test accepting a quest that's already accepted"""
        data = db_with_full_setup
        
        # Accept once
        await data['db'].accept_quest(data['quest_id'], data['character_id'])
        
        # Try to accept again
        result = await data['db'].accept_quest(data['quest_id'], data['character_id'])
        assert 'error' in result

    async def test_complete_objective(self, db_with_full_setup):
        """Test completing a quest objective"""
        data = db_with_full_setup
        
        # Accept quest first
        await data['db'].accept_quest(data['quest_id'], data['character_id'])
        
        # Complete first objective
        result = await data['db'].complete_objective(
            quest_id=data['quest_id'],
            character_id=data['character_id'],
            objective_index=0
        )
        
        assert 0 in result['completed_objectives']
        assert result['quest_complete'] is False

    async def test_complete_quest(self, db_with_full_setup):
        """Test completing a quest and receiving rewards"""
        data = db_with_full_setup
        
        # Accept and complete quest
        await data['db'].accept_quest(data['quest_id'], data['character_id'])
        
        result = await data['db'].complete_quest(
            quest_id=data['quest_id'],
            character_id=data['character_id']
        )
        
        assert result['success'] is True
        assert 'rewards' in result
        assert result['rewards']['gold'] == 100
        assert result['rewards']['xp'] == 50
        
        # Verify character received rewards
        char = await data['db'].get_character(data['character_id'])
        assert char['gold'] == 100
        assert char['experience'] == 50


# =============================================================================
# NPC TESTS
# =============================================================================

class TestNPCs:
    """Tests for NPC operations"""

    async def test_create_npc(self, db):
        """Test creating an NPC"""
        npc_id = await db.create_npc(
            guild_id=67890,
            name="Bartender Bob",
            description="A grizzled veteran who runs the local tavern",
            personality="Gruff but kind-hearted",
            created_by=12345,
            npc_type="friendly",
            location="The Golden Goblet"
        )
        
        assert npc_id is not None
        
        npc = await db.get_npc(npc_id)
        assert npc['name'] == "Bartender Bob"
        assert npc['npc_type'] == "friendly"
        assert npc['is_alive'] == 1

    async def test_create_merchant_npc(self, db):
        """Test creating a merchant NPC"""
        npc_id = await db.create_npc(
            guild_id=67890,
            name="Shopkeeper Steve",
            description="A shrewd merchant",
            personality="Business-minded",
            created_by=12345,
            is_merchant=True,
            merchant_inventory=[
                {"item_id": "health_potion", "name": "Health Potion", "price": 50, "quantity": 10}
            ]
        )
        
        npc = await db.get_npc(npc_id)
        assert npc['is_merchant'] == 1
        assert len(npc['merchant_inventory']) == 1

    async def test_get_npcs_by_location(self, db):
        """Test getting NPCs at a specific location"""
        await db.create_npc(
            guild_id=67890, name="Guard 1", description="A guard",
            personality="Stoic", created_by=12345, location="Castle Gate"
        )
        await db.create_npc(
            guild_id=67890, name="Guard 2", description="Another guard",
            personality="Alert", created_by=12345, location="Castle Gate"
        )
        await db.create_npc(
            guild_id=67890, name="Merchant", description="A merchant",
            personality="Friendly", created_by=12345, location="Market Square"
        )
        
        guards = await db.get_npcs_by_location(67890, "Castle Gate")
        assert len(guards) == 2
        
        merchants = await db.get_npcs_by_location(67890, "Market Square")
        assert len(merchants) == 1

    async def test_update_npc_relationship(self, db_with_full_setup):
        """Test updating NPC-character relationship"""
        data = db_with_full_setup
        
        # Initial reputation
        rep = await data['db'].update_npc_relationship(
            npc_id=data['npc_id'],
            character_id=data['character_id'],
            reputation_change=10,
            notes="Helped with a delivery"
        )
        assert rep == 10
        
        # Increase reputation
        rep = await data['db'].update_npc_relationship(
            npc_id=data['npc_id'],
            character_id=data['character_id'],
            reputation_change=15
        )
        assert rep == 25

    async def test_npc_relationship_capped(self, db_with_full_setup):
        """Test that NPC relationship is capped at -100 to 100"""
        data = db_with_full_setup
        
        # Try to go above 100
        await data['db'].update_npc_relationship(
            data['npc_id'], data['character_id'], 150
        )
        
        relationship = await data['db'].get_npc_relationship(
            data['npc_id'], data['character_id']
        )
        assert relationship['reputation'] <= 100


# =============================================================================
# COMBAT TESTS
# =============================================================================

class TestCombat:
    """Tests for combat operations"""

    async def test_create_combat(self, db):
        """Test creating a combat encounter"""
        combat_id = await db.create_combat(
            guild_id=67890,
            channel_id=11111
        )
        
        assert combat_id is not None
        
        combat = await db.get_active_combat(channel_id=11111)
        assert combat is not None
        assert combat['status'] == 'active'
        assert combat['round_number'] == 1

    async def test_add_combatant(self, db):
        """Test adding combatants to combat"""
        combat_id = await db.create_combat(67890, 11111)
        
        # Add player
        player_id = await db.add_combatant(
            encounter_id=combat_id,
            participant_type="player",
            participant_id=12345,
            name="Test Hero",
            hp=20,
            max_hp=20,
            initiative=15,
            is_player=True
        )
        
        # Add enemy
        enemy_id = await db.add_combatant(
            encounter_id=combat_id,
            participant_type="enemy",
            participant_id=1,
            name="Goblin",
            hp=7,
            max_hp=7,
            initiative=12,
            is_player=False
        )
        
        combatants = await db.get_combatants(combat_id)
        assert len(combatants) == 2
        # Should be ordered by initiative (descending)
        assert combatants[0]['name'] == "Test Hero"
        assert combatants[1]['name'] == "Goblin"

    async def test_update_combatant_hp(self, db):
        """Test updating combatant HP (damage/healing)"""
        combat_id = await db.create_combat(67890, 11111)
        participant_id = await db.add_combatant(
            combat_id, "player", 12345, "Test Hero", 20, 20, 15
        )
        
        # Deal damage
        result = await db.update_combatant_hp(participant_id, -8)
        assert result['old_hp'] == 20
        assert result['new_hp'] == 12
        assert result['is_dead'] is False
        
        # Heal
        result = await db.update_combatant_hp(participant_id, 5)
        assert result['new_hp'] == 17
        
        # Deal lethal damage
        result = await db.update_combatant_hp(participant_id, -20)
        assert result['new_hp'] == 0
        assert result['is_dead'] is True

    async def test_add_status_effect(self, db):
        """Test adding status effects to combatants"""
        combat_id = await db.create_combat(67890, 11111)
        participant_id = await db.add_combatant(
            combat_id, "player", 12345, "Test Hero", 20, 20, 15
        )
        
        await db.add_status_effect(participant_id, "poisoned", duration=3)
        
        combatants = await db.get_combatants(combat_id)
        effects = combatants[0]['status_effects']
        assert len(effects) == 1
        assert effects[0]['effect'] == "poisoned"
        assert effects[0]['duration'] == 3

    async def test_advance_combat_turn(self, db):
        """Test advancing turns in combat"""
        combat_id = await db.create_combat(67890, 11111)
        
        await db.add_combatant(combat_id, "player", 1, "Hero1", 20, 20, 15)
        await db.add_combatant(combat_id, "player", 2, "Hero2", 20, 20, 10)
        
        # First turn should be Hero1 (higher initiative)
        combat = await db.get_active_combat(channel_id=11111)
        assert combat['current_turn'] == 0
        
        # Advance to next turn
        result = await db.advance_combat_turn(combat_id)
        assert result['round'] == 1
        assert result['current_combatant']['name'] == "Hero2"
        
        # Advance again - should start new round
        result = await db.advance_combat_turn(combat_id)
        assert result['round'] == 2
        assert result['current_combatant']['name'] == "Hero1"

    async def test_end_combat(self, db):
        """Test ending combat"""
        combat_id = await db.create_combat(67890, 11111)
        
        await db.end_combat(combat_id)
        
        # Should no longer be active
        combat = await db.get_active_combat(channel_id=11111)
        assert combat is None

    async def test_combat_log(self, db):
        """Test adding entries to combat log"""
        combat_id = await db.create_combat(67890, 11111)
        
        await db.add_combat_log(combat_id, "Combat started!")
        await db.add_combat_log(combat_id, "Hero attacks Goblin for 5 damage")
        
        combat = await db.get_active_combat(channel_id=11111)
        assert len(combat['combat_log']) == 2


# =============================================================================
# SESSION TESTS
# =============================================================================

class TestSessions:
    """Tests for session/campaign operations"""

    async def test_create_session(self, db):
        """Test creating a new session"""
        session_id = await db.create_session(
            guild_id=67890,
            name="The Lost Mines",
            dm_user_id=12345,
            description="An adventure in the mines",
            setting="Fantasy",
            max_players=4
        )
        
        assert session_id is not None
        
        session = await db.get_session(session_id)
        assert session['name'] == "The Lost Mines"
        assert session['max_players'] == 4
        assert session['status'] == 'inactive'

    async def test_start_and_end_session(self, db):
        """Test starting and ending a session"""
        session_id = await db.create_session(
            guild_id=67890, name="Test Session",
            dm_user_id=12345
        )
        
        # Start session
        await db.start_session(session_id)
        session = await db.get_session(session_id)
        assert session['status'] == 'active'
        
        # End session
        await db.end_session(session_id)
        session = await db.get_session(session_id)
        assert session['status'] == 'inactive'

    async def test_get_active_session(self, db):
        """Test getting active session for a guild"""
        session_id = await db.create_session(
            guild_id=67890, name="Active Session",
            dm_user_id=12345
        )
        await db.start_session(session_id)
        
        active = await db.get_active_session(67890)
        assert active is not None
        assert active['id'] == session_id

    async def test_join_session(self, db):
        """Test player joining a session"""
        session_id = await db.create_session(
            guild_id=67890, name="Test Session",
            dm_user_id=12345
        )
        
        # Player joins
        result = await db.join_session(session_id, user_id=99999)
        assert result is True
        
        participants = await db.get_session_participants(session_id)
        assert len(participants) == 1
        assert participants[0]['user_id'] == 99999

    async def test_join_session_with_character(self, db_with_character):
        """Test player joining session with a character"""
        db, char_id = db_with_character
        
        session_id = await db.create_session(
            guild_id=67890, name="Test Session",
            dm_user_id=12345
        )
        
        await db.join_session(session_id, user_id=12345, character_id=char_id)
        
        participants = await db.get_session_participants(session_id)
        assert participants[0]['character_id'] == char_id
        assert participants[0]['character_name'] == "Test Hero"

    async def test_update_world_state(self, db):
        """Test updating session world state"""
        session_id = await db.create_session(
            guild_id=67890, name="Test Session",
            dm_user_id=12345
        )
        
        await db.update_world_state(session_id, {
            "time_of_day": "night",
            "weather": "stormy",
            "location": "Dark Forest"
        })
        
        session = await db.get_session(session_id)
        assert session['world_state']['time_of_day'] == "night"
        assert session['world_state']['weather'] == "stormy"


# =============================================================================
# MEMORY & CONVERSATION TESTS
# =============================================================================

class TestMemoryAndConversation:
    """Tests for memory and conversation history"""

    async def test_save_and_get_memory(self, db):
        """Test saving and retrieving memories"""
        await db.save_memory(
            user_id=12345,
            guild_id=67890,
            key="favorite_weapon",
            value="longsword",
            context="Player expressed preference during combat"
        )
        
        memories = await db.get_all_memories(12345, 67890)
        assert "favorite_weapon" in memories
        assert memories["favorite_weapon"]["value"] == "longsword"

    async def test_update_memory(self, db):
        """Test updating an existing memory"""
        await db.save_memory(12345, 67890, "pet_name", "Fluffy")
        await db.save_memory(12345, 67890, "pet_name", "Max")
        
        memories = await db.get_all_memories(12345, 67890)
        assert memories["pet_name"]["value"] == "Max"

    async def test_delete_memory(self, db):
        """Test deleting a memory"""
        await db.save_memory(12345, 67890, "temp_data", "to_delete")
        await db.delete_memory(12345, 67890, "temp_data")
        
        memories = await db.get_all_memories(12345, 67890)
        assert "temp_data" not in memories

    async def test_conversation_history(self, db):
        """Test saving and retrieving conversation history"""
        await db.save_message(12345, 67890, 11111, "user", "Hello DM!")
        await db.save_message(12345, 67890, 11111, "assistant", "Greetings, adventurer!")
        await db.save_message(12345, 67890, 11111, "user", "What should I do?")
        
        messages = await db.get_recent_messages(12345, 67890, 11111, limit=10)
        assert len(messages) == 3
        assert messages[0]['role'] == "user"
        assert messages[1]['role'] == "assistant"

    async def test_story_log(self, db_with_session):
        """Test adding and retrieving story log entries"""
        db, session_id = db_with_session
        
        await db.add_story_entry(
            session_id=session_id,
            entry_type="narrative",
            content="The party arrived at the ancient ruins...",
            participants=[12345, 67890]
        )
        
        await db.add_story_entry(
            session_id=session_id,
            entry_type="combat",
            content="Battle with goblins began!"
        )
        
        log = await db.get_story_log(session_id)
        assert len(log) == 2
        assert log[0]['entry_type'] == "narrative"


# =============================================================================
# DICE ROLL TESTS
# =============================================================================

class TestDiceRolls:
    """Tests for dice roll history"""

    async def test_log_dice_roll(self, db):
        """Test logging a dice roll"""
        roll_id = await db.log_dice_roll(
            user_id=12345,
            guild_id=67890,
            roll_type="attack",
            dice_expression="1d20+5",
            individual_rolls=[15],
            modifier=5,
            total=20,
            purpose="Attack roll against goblin"
        )
        
        assert roll_id is not None

    async def test_get_roll_history(self, db):
        """Test retrieving roll history"""
        for i in range(5):
            await db.log_dice_roll(
                12345, 67890, "attack", "1d20", [10+i], 0, 10+i
            )
        
        history = await db.get_roll_history(12345, 67890, limit=3)
        assert len(history) == 3
        # Should be in reverse chronological order
        assert history[0]['total'] == 14
