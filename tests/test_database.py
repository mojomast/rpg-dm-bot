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

    async def test_update_character_hp_clamps_and_returns_state(self, db_with_character):
        """Test updating character HP returns the expected state."""
        db, char_id = db_with_character

        result = await db.update_character_hp(char_id, -999)

        assert result['name'] == "Test Hero"
        assert result['new_hp'] == 0
        assert result['max_hp'] > 0
        assert result['is_dead'] is True

        char = await db.get_character(char_id)
        assert char['hp'] == 0


class TestSessionChannelBinding:
    async def test_bind_session_channel_sets_last_active_and_primary(self, db):
        session_id = await db.create_session(
            guild_id=67890,
            name="Bound Session",
            dm_user_id=12345,
        )

        ok = await db.bind_session_channel(session_id, 555, set_primary=True)
        assert ok is True

        session = await db.get_session(session_id)
        assert session['last_active_channel_id'] == 555
        assert session['primary_channel_id'] == 555

    async def test_get_session_by_channel_prefers_bound_session(self, db):
        session_id = await db.create_session(
            guild_id=67890,
            name="Lookup Session",
            dm_user_id=12345,
        )
        await db.update_session(session_id, status='active')
        await db.bind_session_channel(session_id, 777, set_primary=True)

        session = await db.get_session_by_channel(67890, 777, statuses=['active'])
        assert session is not None
        assert session['id'] == session_id


class TestSnapshots:
    async def test_load_session_snapshot_restores_runtime_state(self, db, sample_character_stats):
        session_id = await db.create_session(
            guild_id=67890,
            name="Snapshot Session",
            dm_user_id=12345,
            description="Snapshot restore test",
        )
        await db.update_session(session_id, status='active', world_theme='fantasy', content_pack_id='fantasy_core')

        town_id = await db.create_location(
            guild_id=67890,
            session_id=session_id,
            created_by=12345,
            name="Oakheart",
            description="Town square",
            location_type="town",
            points_of_interest=["Square"],
        )
        forest_id = await db.create_location(
            guild_id=67890,
            session_id=session_id,
            created_by=12345,
            name="Whisperwood",
            description="Ancient forest",
            location_type="wilderness",
        )
        await db.connect_locations(town_id, forest_id, direction='north', travel_time=2)

        char_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Aria",
            race="human",
            char_class="warrior",
            stats=sample_character_stats,
            session_id=session_id,
        )
        await db.join_session(session_id, user_id=12345, character_id=char_id)
        await db.add_item(char_id, 'rope', 'Rope', 'gear', 1)

        quest_id = await db.create_quest(
            guild_id=67890,
            title="Lost Relic",
            description="Recover the relic.",
            objectives=[{"description": "Find the shrine", "completed": False}],
            rewards={"gold": 100},
            created_by=12345,
            session_id=session_id,
        )
        await db.accept_quest(quest_id, char_id)

        npc_id = await db.create_npc(
            guild_id=67890,
            name="Wren",
            description="A worried scout.",
            personality="Alert",
            created_by=12345,
            session_id=session_id,
            location="Oakheart",
        )
        await db.update_npc(npc_id, location_id=town_id, loyalty=75, party_role='guide')

        await db.save_game_state(
            session_id,
            current_scene='At the gates',
            current_location='Oakheart',
            current_location_id=town_id,
            dm_notes='Original state',
            turn_count=3,
            game_data={'active_content_pack_id': 'fantasy_core'},
        )
        await db.save_message(12345, 67890, 555, 'assistant', 'Original message', session_id=session_id)

        snapshot_id = await db.save_session_snapshot(
            session_id=session_id,
            name='Before divergence',
            created_by=12345,
            description='Reference restore point',
        )

        await db.update_session(session_id, name='Mutated Session', current_quest_id=None)
        await db.save_game_state(
            session_id,
            current_scene='Changed scene',
            current_location='Nowhere',
            current_location_id=None,
            dm_notes='Mutated',
            turn_count=0,
            game_data={},
        )
        await db.delete_npc(npc_id)
        await db.delete_quest(quest_id)

        mutated_char = await db.get_character(char_id)
        await db.update_character(mutated_char['id'], name='Mutated Hero', current_location_id=None)
        inventory = await db.get_inventory(mutated_char['id'])
        if inventory:
            await db.remove_item(inventory[0]['id'])

        await db.load_session_snapshot(snapshot_id)

        restored_session = await db.get_session(session_id)
        assert restored_session['name'] == 'Snapshot Session'
        assert restored_session['content_pack_id'] == 'fantasy_core'

        restored_state = await db.get_game_state(session_id)
        assert restored_state['current_scene'] == 'At the gates'
        assert restored_state['current_location'] == 'Oakheart'
        assert restored_state['turn_count'] == 3

        restored_characters = await db.get_session_characters(session_id)
        assert len(restored_characters) == 1
        restored_char = restored_characters[0]
        assert restored_char['name'] == 'Aria'

        restored_inventory = await db.get_inventory(restored_char['id'])
        assert len(restored_inventory) == 1
        assert restored_inventory[0]['item_name'] == 'Rope'

        restored_quests = await db.get_quests(session_id=session_id)
        assert len(restored_quests) == 1
        restored_quest = restored_quests[0]
        assert restored_quest['title'] == 'Lost Relic'

        quest_stage = await db.get_quest_current_stage(restored_quest['id'], restored_char['id'])
        assert quest_stage['total'] == 1

        restored_npcs = await db.get_npcs_by_session(session_id)
        assert len(restored_npcs) == 1
        assert restored_npcs[0]['name'] == 'Wren'

        restored_locations = await db.get_locations(session_id=session_id)
        assert len(restored_locations) == 2
        restored_town = next(location for location in restored_locations if location['name'] == 'Oakheart')
        connections = await db.get_nearby_locations(restored_town['id'])
        assert len(connections) == 1
        assert connections[0]['name'] == 'Whisperwood'

        messages = await db.get_recent_messages_by_session(12345, session_id, limit=10)
        assert any(message['content'] == 'Original message' for message in messages)


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

    async def test_complete_quest_blocks_duplicate_rewards(self, db_with_full_setup):
        """Test quest rewards are only granted once."""
        data = db_with_full_setup

        await data['db'].accept_quest(data['quest_id'], data['character_id'])
        first = await data['db'].complete_quest(data['quest_id'], data['character_id'])
        second = await data['db'].complete_quest(data['quest_id'], data['character_id'])

        assert first['success'] is True
        assert second['error'] == 'Quest already completed'

        char = await data['db'].get_character(data['character_id'])
        assert char['gold'] == 100
        assert char['experience'] == 50

    async def test_get_quest_stages_from_objectives(self, db_with_full_setup):
        """Test synthesizing quest stages from objective data."""
        data = db_with_full_setup

        stages = await data['db'].get_quest_stages(data['quest_id'])

        assert len(stages) == 3
        assert stages[0]['title'] == "Objective 1"
        assert stages[0]['description'] == "Talk to the innkeeper"
        assert stages[0]['completed'] is False


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

    async def test_create_npc_with_location_id_syncs_location_text(self, db_with_session):
        db, session_id = db_with_session
        location_id = await db.create_location(
            guild_id=67890,
            session_id=session_id,
            created_by=12345,
            name="East Gate",
        )

        npc_id = await db.create_npc(
            guild_id=67890,
            session_id=session_id,
            name="Gate Warden",
            description="Keeps watch.",
            personality="Suspicious",
            created_by=12345,
            location_id=location_id,
        )

        npc = await db.get_npc(npc_id)
        assert npc['location_id'] == location_id
        assert npc['location'] == 'East Gate'

    async def test_update_npc_location_id_syncs_location_text(self, db_with_session):
        db, session_id = db_with_session
        old_location_id = await db.create_location(
            guild_id=67890,
            session_id=session_id,
            created_by=12345,
            name="Docks",
        )
        new_location_id = await db.create_location(
            guild_id=67890,
            session_id=session_id,
            created_by=12345,
            name="Watchtower",
        )
        npc_id = await db.create_npc(
            guild_id=67890,
            session_id=session_id,
            name="Harbor Scout",
            description="Reports ship traffic.",
            personality="Alert",
            created_by=12345,
            location_id=old_location_id,
        )

        await db.update_npc(npc_id, location_id=new_location_id)

        npc = await db.get_npc(npc_id)
        assert npc['location_id'] == new_location_id
        assert npc['location'] == 'Watchtower'

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

    async def test_get_active_combat_by_session(self, db_with_session):
        """Test getting active combat by session for web chat contexts."""
        db, session_id = db_with_session

        combat_id = await db.create_combat(
            guild_id=67890,
            channel_id=11111,
            session_id=session_id,
        )

        combat = await db.get_active_combat_by_session(session_id)

        assert combat is not None
        assert combat['id'] == combat_id
        assert combat['session_id'] == session_id

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

    async def test_add_character_combatant_snapshots_equipped_armor_class(self, db_with_character):
        """Character combatants should snapshot authoritative AC from equipped gear."""
        db, char_id = db_with_character
        await db.add_item(
            character_id=char_id,
            item_id="armor_chain",
            item_name="Chain Mail",
            item_type="armor",
            is_equipped=True,
            slot="body",
            properties={"ac_base": 16, "max_dex_bonus": 0},
        )
        await db.add_item(
            character_id=char_id,
            item_id="shield_wooden",
            item_name="Wooden Shield",
            item_type="armor",
            is_equipped=True,
            slot="off_hand",
            properties={"ac_bonus": 2},
        )

        combat_id = await db.create_combat(67890, 11111)
        await db.add_combatant(
            combat_id, "character", char_id, "Test Hero", 20, 20, 2, is_player=True
        )

        combatant = (await db.get_combatants(combat_id))[0]
        assert combatant['armor_class'] == 18
        assert combatant['combat_stats']['ac'] == 18
        assert combatant['combat_stats']['armor_class'] == 18

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

    async def test_tick_combat_status_effects_removes_expired(self, db):
        """Test combat status effects tick down and expire."""
        combat_id = await db.create_combat(67890, 11111)
        participant_id = await db.add_combatant(
            combat_id, "player", 12345, "Test Hero", 20, 20, 15
        )

        await db.add_status_effect(participant_id, "defending", duration=1)
        effects = await db.tick_combat_status_effects(participant_id)

        assert effects == []

        combatants = await db.get_combatants(combat_id)
        assert combatants[0]['status_effects'] == []

    async def test_set_initiative_order_and_current_turn(self, db):
        """Test persisting initiative order and turn index."""
        combat_id = await db.create_combat(67890, 11111)
        player_id = await db.add_combatant(
            combat_id, "character", 12345, "Test Hero", 20, 20, 15
        )
        enemy_id = await db.add_combatant(
            combat_id, "enemy", 1, "Goblin", 7, 7, 12, is_player=False
        )

        await db.set_initiative_order(combat_id, [enemy_id, player_id])
        await db.set_current_turn(combat_id, 1)

        combat = await db.get_active_combat(channel_id=11111)
        participants = await db.get_combat_participants(combat_id)

        assert combat['initiative_order'] == [enemy_id, player_id]
        assert combat['current_turn'] == 1
        assert [p['id'] for p in participants] == [enemy_id, player_id]
        assert participants[1]['character_id'] == 12345

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
# LOCATION TESTS
# =============================================================================

class TestLocations:
    """Tests for location operations."""

    async def test_get_nearby_locations_returns_destination_shape(self, db_with_session):
        """Test nearby locations return the destination fields callers expect."""
        db, session_id = db_with_session

        town_id = await db.create_location(
            guild_id=67890,
            name="Town",
            description="Starting town",
            created_by=12345,
            session_id=session_id,
        )
        forest_id = await db.create_location(
            guild_id=67890,
            name="Forest",
            description="Dark woods",
            created_by=12345,
            session_id=session_id,
            location_type="wilderness",
        )

        await db.connect_locations(town_id, forest_id, direction="north", travel_time=2)

        nearby = await db.get_nearby_locations(town_id)

        assert len(nearby) == 1
        assert nearby[0]['id'] == forest_id
        assert nearby[0]['name'] == "Forest"
        assert nearby[0]['location_type'] == "wilderness"

    async def test_location_connection_crud_round_trip(self, db_with_session):
        db, session_id = db_with_session

        town_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name="Town")
        cave_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name="Cave")

        connection_id = await db.create_location_connection(
            from_location_id=town_id,
            to_location_id=cave_id,
            direction='north',
            travel_time=2,
            hidden=False,
            bidirectional=True,
        )

        connection = await db.get_location_connection(connection_id)
        assert connection['from_location_name'] == 'Town'
        assert connection['to_location_name'] == 'Cave'
        assert connection['direction'] == 'north'

        all_connections = await db.list_location_connections(location_id=town_id)
        assert len(all_connections) == 1
        assert all_connections[0]['id'] == connection_id

        await db.update_location_connection(connection_id, direction='east', hidden=True)
        updated = await db.get_location_connection(connection_id)
        assert updated['direction'] == 'east'
        assert updated['hidden'] == 1

        deleted = await db.delete_location_connection(connection_id)
        assert deleted is True
        assert await db.get_location_connection(connection_id) is None

    async def test_get_adjacent_locations_uses_session_current_location(self, db_with_session):
        db, session_id = db_with_session

        town_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name="Town")
        cave_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name="Cave")
        await db.create_location_connection(from_location_id=town_id, to_location_id=cave_id, direction='east')
        await db.save_game_state(session_id, current_location='Town', current_location_id=town_id)

        adjacent = await db.get_adjacent_locations(session_id)

        assert len(adjacent) == 1
        assert adjacent[0]['id'] == cave_id
        assert adjacent[0]['direction'] == 'east'


class TestStoryContent:
    async def test_update_story_item_normalizes_discovered_alias(self, db_with_session):
        db, session_id = db_with_session

        item_id = await db.create_story_item(
            guild_id=67890,
            session_id=session_id,
            name="Ancient Seal",
            created_by=12345,
        )

        await db.update_story_item(item_id, discovered=True, location="Legacy Name")

        item = await db.get_story_item(item_id)
        assert item['is_discovered'] == 1
        assert item['location_id'] is None

    async def test_update_story_event_normalizes_legacy_statuses(self, db_with_session):
        db, session_id = db_with_session

        event_id = await db.create_story_event(
            guild_id=67890,
            session_id=session_id,
            name="Bridge Ambush",
            created_by=12345,
        )

        await db.update_story_event(event_id, status='active')
        event = await db.get_story_event(event_id)
        assert event['status'] == 'triggered'

        await db.update_story_event(event_id, status='completed')
        event = await db.get_story_event(event_id)
        assert event['status'] == 'resolved'

    async def test_get_active_events_returns_triggered_events(self, db_with_session):
        db, session_id = db_with_session

        triggered_id = await db.create_story_event(
            guild_id=67890,
            session_id=session_id,
            name="Rising Tension",
            created_by=12345,
        )
        resolved_id = await db.create_story_event(
            guild_id=67890,
            session_id=session_id,
            name="Spent Lead",
            created_by=12345,
        )

        await db.trigger_event(triggered_id)
        await db.resolve_event(resolved_id, outcome='success')

        active_events = await db.get_active_events(session_id)

        assert [event['id'] for event in active_events] == [triggered_id]


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

    async def test_conversation_history_by_session(self, db_with_session):
        """Test loading recent conversation history by session and user."""
        db, session_id = db_with_session

        await db.save_message(12345, 67890, 11111, "user", "First", session_id=session_id)
        await db.save_message(12345, 67890, 22222, "assistant", "Second", session_id=session_id)
        await db.save_message(12345, 67890, 33333, "user", "Third", session_id=session_id)
        await db.save_message(12345, 67890, 44444, "user", "Other session", session_id=session_id + 1)

        messages = await db.get_recent_messages_by_session(12345, session_id, limit=20)

        assert [message['content'] for message in messages] == ["First", "Second", "Third"]

    async def test_web_identity_storage(self, db):
        """Test creating and validating a web identity."""
        identity = "123e4567-e89b-12d3-a456-426614174000"

        await db.create_web_identity(identity, "hashed-ip")

        assert await db.web_identity_exists(identity) is True
        assert await db.web_identity_exists("missing") is False

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
