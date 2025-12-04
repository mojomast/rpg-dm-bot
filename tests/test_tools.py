"""
Unit tests for ToolExecutor class in src/tools.py
Tests tool execution for all game mechanics.
"""

import pytest


# =============================================================================
# CHARACTER TOOL TESTS
# =============================================================================

class TestCharacterTools:
    """Tests for character-related tools"""

    async def test_get_character_info(self, tool_executor_with_character, mock_context):
        """Test getting character info"""
        executor, db, char_id = tool_executor_with_character
        mock_context['user_id'] = 12345
        mock_context['guild_id'] = 67890
        
        result = await executor.execute_tool(
            "get_character_info",
            {"user_id": 12345},
            mock_context
        )
        
        assert "Test Hero" in result
        assert "warrior" in result.lower()
        assert "HP:" in result

    async def test_get_character_info_by_id(self, tool_executor_with_character, mock_context):
        """Test getting character info by ID"""
        executor, db, char_id = tool_executor_with_character
        
        result = await executor.execute_tool(
            "get_character_info",
            {"character_id": char_id},
            mock_context
        )
        
        assert "Test Hero" in result

    async def test_get_character_info_not_found(self, tool_executor, mock_context):
        """Test getting character info when none exists"""
        result = await tool_executor.execute_tool(
            "get_character_info",
            {"user_id": 99999},
            mock_context
        )
        
        assert "No character found" in result

    async def test_update_character_hp_damage(self, tool_executor_with_character, mock_context):
        """Test dealing damage to character"""
        executor, db, char_id = tool_executor_with_character
        
        char_before = await db.get_character(char_id)
        hp_before = char_before['hp']
        
        result = await executor.execute_tool(
            "update_character_hp",
            {"character_id": char_id, "hp_change": -5, "reason": "trap damage"},
            mock_context
        )
        
        assert "took damage" in result
        assert "trap damage" in result
        
        char_after = await db.get_character(char_id)
        assert char_after['hp'] == hp_before - 5

    async def test_update_character_hp_healing(self, tool_executor_with_character, mock_context):
        """Test healing character"""
        executor, db, char_id = tool_executor_with_character
        
        # First damage the character
        await db.update_character(char_id, hp=5)
        
        result = await executor.execute_tool(
            "update_character_hp",
            {"character_id": char_id, "hp_change": 10, "reason": "healing potion"},
            mock_context
        )
        
        assert "healed" in result
        assert "healing potion" in result

    async def test_add_experience(self, tool_executor_with_character, mock_context):
        """Test adding experience to character"""
        executor, db, char_id = tool_executor_with_character
        
        result = await executor.execute_tool(
            "add_experience",
            {"character_id": char_id, "xp": 100, "reason": "defeated goblin"},
            mock_context
        )
        
        assert "100 XP" in result
        assert "defeated goblin" in result

    async def test_add_experience_level_up(self, tool_executor_with_character, mock_context):
        """Test adding enough experience to level up"""
        executor, db, char_id = tool_executor_with_character
        
        result = await executor.execute_tool(
            "add_experience",
            {"character_id": char_id, "xp": 500, "reason": "quest reward"},
            mock_context
        )
        
        assert "LEVEL UP" in result
        assert "level 2" in result.lower()

    async def test_update_character_stats(self, tool_executor_with_character, mock_context):
        """Test updating character stats"""
        executor, db, char_id = tool_executor_with_character
        
        result = await executor.execute_tool(
            "update_character_stats",
            {"character_id": char_id, "stat_changes": {"strength": 2, "dexterity": 1}},
            mock_context
        )
        
        assert "Stats updated" in result
        assert "strength" in result.lower()


# =============================================================================
# INVENTORY TOOL TESTS
# =============================================================================

class TestInventoryTools:
    """Tests for inventory-related tools"""

    async def test_give_item(self, tool_executor_with_character, mock_context, sample_item):
        """Test giving an item to a character"""
        executor, db, char_id = tool_executor_with_character
        
        result = await executor.execute_tool(
            "give_item",
            {
                "character_id": char_id,
                "item_id": sample_item['id'],
                "item_name": sample_item['name'],
                "item_type": sample_item['type'],
                "quantity": 1,
                "properties": sample_item['properties']
            },
            mock_context
        )
        
        assert "Added" in result
        assert sample_item['name'] in result

    async def test_get_inventory(self, tool_executor_with_character, mock_context, sample_item):
        """Test getting character inventory"""
        executor, db, char_id = tool_executor_with_character
        
        # Add item first
        await db.add_item(char_id, sample_item['id'], sample_item['name'], sample_item['type'])
        
        result = await executor.execute_tool(
            "get_inventory",
            {"character_id": char_id},
            mock_context
        )
        
        assert "Inventory" in result
        assert sample_item['name'] in result

    async def test_get_inventory_empty(self, tool_executor_with_character, mock_context):
        """Test getting empty inventory"""
        executor, db, char_id = tool_executor_with_character
        
        result = await executor.execute_tool(
            "get_inventory",
            {"character_id": char_id},
            mock_context
        )
        
        assert "empty" in result.lower()

    async def test_remove_item(self, tool_executor_with_character, mock_context):
        """Test removing an item"""
        executor, db, char_id = tool_executor_with_character
        
        # Add item first
        inv_id = await db.add_item(char_id, "test_item", "Test Item", "consumable", 5)
        
        result = await executor.execute_tool(
            "remove_item",
            {"inventory_id": inv_id, "quantity": 2},
            mock_context
        )
        
        assert "Removed" in result
        
        # Verify quantity reduced
        inventory = await db.get_inventory(char_id)
        assert inventory[0]['quantity'] == 3

    async def test_give_gold(self, tool_executor_with_character, mock_context):
        """Test giving gold to character"""
        executor, db, char_id = tool_executor_with_character
        
        result = await executor.execute_tool(
            "give_gold",
            {"character_id": char_id, "amount": 100, "reason": "treasure"},
            mock_context
        )
        
        assert "100 gold" in result
        assert "treasure" in result

    async def test_take_gold(self, tool_executor_with_character, mock_context):
        """Test taking gold from character"""
        executor, db, char_id = tool_executor_with_character
        
        # Give gold first
        await db.update_gold(char_id, 100)
        
        result = await executor.execute_tool(
            "take_gold",
            {"character_id": char_id, "amount": 30, "reason": "shop purchase"},
            mock_context
        )
        
        assert "Spent 30 gold" in result
        assert "70" in result  # Remaining

    async def test_take_gold_insufficient(self, tool_executor_with_character, mock_context):
        """Test taking gold when insufficient"""
        executor, db, char_id = tool_executor_with_character
        
        result = await executor.execute_tool(
            "take_gold",
            {"character_id": char_id, "amount": 1000, "reason": "expensive item"},
            mock_context
        )
        
        assert "Not enough gold" in result


# =============================================================================
# COMBAT TOOL TESTS
# =============================================================================

class TestCombatTools:
    """Tests for combat-related tools"""

    async def test_start_combat(self, tool_executor, mock_context):
        """Test starting combat"""
        result = await tool_executor.execute_tool(
            "start_combat",
            {"description": "Goblins emerge from the shadows!"},
            mock_context
        )
        
        assert "Combat started" in result
        assert "Goblins emerge" in result

    async def test_start_combat_already_active(self, tool_executor, mock_context):
        """Test starting combat when one is already active"""
        # Start first combat
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        
        # Try to start another
        result = await tool_executor.execute_tool("start_combat", {}, mock_context)
        
        assert "Error" in result
        assert "already active" in result

    async def test_add_enemy(self, tool_executor, mock_context, sample_enemy):
        """Test adding enemy to combat"""
        # Start combat first
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        
        result = await tool_executor.execute_tool(
            "add_enemy",
            {
                "name": sample_enemy['name'],
                "hp": sample_enemy['hp'],
                "initiative_bonus": 2
            },
            mock_context
        )
        
        assert "Added" in result
        assert sample_enemy['name'] in result

    async def test_add_enemy_no_combat(self, tool_executor, mock_context, sample_enemy):
        """Test adding enemy when no combat active"""
        result = await tool_executor.execute_tool(
            "add_enemy",
            {"name": "Goblin", "hp": 7},
            mock_context
        )
        
        assert "Error" in result
        assert "No active combat" in result

    async def test_roll_initiative(self, tool_executor, mock_context):
        """Test rolling initiative"""
        # Start combat and add enemies
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        await tool_executor.execute_tool(
            "add_enemy",
            {"name": "Goblin", "hp": 7, "initiative_bonus": 2},
            mock_context
        )
        
        result = await tool_executor.execute_tool("roll_initiative", {}, mock_context)
        
        assert "Initiative Order" in result
        assert "Goblin" in result

    async def test_deal_damage(self, tool_executor, mock_context):
        """Test dealing damage in combat"""
        # Setup combat with enemy
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        add_result = await tool_executor.execute_tool(
            "add_enemy",
            {"name": "Goblin", "hp": 10},
            mock_context
        )
        
        # Extract combatant ID from result
        combat = await tool_executor.db.get_active_combat(mock_context['channel_id'])
        combatants = await tool_executor.db.get_combatants(combat['id'])
        enemy_id = combatants[0]['id']
        
        result = await tool_executor.execute_tool(
            "deal_damage",
            {"target_id": enemy_id, "damage": 5, "damage_type": "slashing"},
            mock_context
        )
        
        assert "Dealt 5" in result
        assert "slashing" in result

    async def test_deal_lethal_damage(self, tool_executor, mock_context):
        """Test dealing lethal damage"""
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        await tool_executor.execute_tool(
            "add_enemy",
            {"name": "Goblin", "hp": 7},
            mock_context
        )
        
        combat = await tool_executor.db.get_active_combat(mock_context['channel_id'])
        combatants = await tool_executor.db.get_combatants(combat['id'])
        enemy_id = combatants[0]['id']
        
        result = await tool_executor.execute_tool(
            "deal_damage",
            {"target_id": enemy_id, "damage": 10},
            mock_context
        )
        
        assert "DOWN" in result or "dead" in result.lower()

    async def test_heal_combatant(self, tool_executor, mock_context):
        """Test healing a combatant"""
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        await tool_executor.execute_tool(
            "add_enemy",
            {"name": "Orc", "hp": 15},
            mock_context
        )
        
        combat = await tool_executor.db.get_active_combat(mock_context['channel_id'])
        combatants = await tool_executor.db.get_combatants(combat['id'])
        orc_id = combatants[0]['id']
        
        # Damage first
        await tool_executor.execute_tool(
            "deal_damage",
            {"target_id": orc_id, "damage": 10},
            mock_context
        )
        
        # Then heal
        result = await tool_executor.execute_tool(
            "heal_combatant",
            {"target_id": orc_id, "healing": 5},
            mock_context
        )
        
        assert "Healed" in result
        assert "5 HP" in result

    async def test_apply_status(self, tool_executor, mock_context):
        """Test applying status effect"""
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        await tool_executor.execute_tool(
            "add_enemy",
            {"name": "Goblin", "hp": 7},
            mock_context
        )
        
        combat = await tool_executor.db.get_active_combat(mock_context['channel_id'])
        combatants = await tool_executor.db.get_combatants(combat['id'])
        enemy_id = combatants[0]['id']
        
        result = await tool_executor.execute_tool(
            "apply_status",
            {"target_id": enemy_id, "effect": "poisoned", "duration": 3},
            mock_context
        )
        
        assert "Applied" in result
        assert "poisoned" in result
        assert "3 rounds" in result

    async def test_get_combat_status(self, tool_executor, mock_context):
        """Test getting combat status"""
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        await tool_executor.execute_tool(
            "add_enemy",
            {"name": "Goblin", "hp": 7},
            mock_context
        )
        
        result = await tool_executor.execute_tool("get_combat_status", {}, mock_context)
        
        assert "Combat Status" in result
        assert "Goblin" in result

    async def test_get_combat_status_no_combat(self, tool_executor, mock_context):
        """Test getting combat status when no combat"""
        result = await tool_executor.execute_tool("get_combat_status", {}, mock_context)
        
        assert "No active combat" in result

    async def test_next_turn(self, tool_executor, mock_context):
        """Test advancing combat turn"""
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        await tool_executor.execute_tool(
            "add_enemy",
            {"name": "Goblin 1", "hp": 7, "initiative_bonus": 10},
            mock_context
        )
        await tool_executor.execute_tool(
            "add_enemy",
            {"name": "Goblin 2", "hp": 7, "initiative_bonus": 5},
            mock_context
        )
        
        result = await tool_executor.execute_tool("next_turn", {}, mock_context)
        
        assert "Round" in result
        assert "turn" in result.lower()

    async def test_end_combat(self, tool_executor, mock_context):
        """Test ending combat"""
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        
        result = await tool_executor.execute_tool(
            "end_combat",
            {"outcome": "victory", "xp_reward": 50},
            mock_context
        )
        
        assert "Combat ended" in result
        assert "victory" in result

    async def test_end_combat_no_active(self, tool_executor, mock_context):
        """Test ending combat when none active"""
        result = await tool_executor.execute_tool("end_combat", {}, mock_context)
        
        assert "No active combat" in result


# =============================================================================
# DICE TOOL TESTS
# =============================================================================

class TestDiceTools:
    """Tests for dice-related tools"""

    async def test_roll_dice_simple(self, tool_executor, mock_context):
        """Test simple dice roll"""
        result = await tool_executor.execute_tool(
            "roll_dice",
            {"dice": "2d6", "purpose": "damage"},
            mock_context
        )
        
        assert "🎲" in result
        assert "damage" in result

    async def test_roll_dice_with_modifier(self, tool_executor, mock_context):
        """Test dice roll with modifier"""
        result = await tool_executor.execute_tool(
            "roll_dice",
            {"dice": "1d20+5", "purpose": "skill check"},
            mock_context
        )
        
        assert "skill check" in result

    async def test_roll_dice_with_advantage(self, tool_executor, mock_context):
        """Test dice roll with advantage"""
        result = await tool_executor.execute_tool(
            "roll_dice",
            {"dice": "1d20", "advantage": True, "purpose": "attack roll"},
            mock_context
        )
        
        assert "attack roll" in result

    async def test_roll_dice_invalid(self, tool_executor, mock_context):
        """Test invalid dice expression"""
        result = await tool_executor.execute_tool(
            "roll_dice",
            {"dice": "invalid", "purpose": "test"},
            mock_context
        )
        
        # Should contain error message
        assert "Invalid" in result or "error" in result.lower()


# =============================================================================
# QUEST TOOL TESTS
# =============================================================================

class TestQuestTools:
    """Tests for quest-related tools"""

    async def test_create_quest(self, tool_executor, mock_context):
        """Test creating a quest"""
        result = await tool_executor.execute_tool(
            "create_quest",
            {
                "title": "The Dark Cave",
                "description": "Explore the mysterious cave",
                "objectives": ["Find the entrance", "Defeat the guardian"],
                "rewards": {"gold": 100, "xp": 50},
                "difficulty": "medium"
            },
            mock_context
        )
        
        # Should confirm quest creation
        assert "quest" in result.lower() or "created" in result.lower()

    async def test_get_quests(self, tool_executor, mock_context):
        """Test getting available quests"""
        # Create a quest first
        await tool_executor.db.create_quest(
            guild_id=mock_context['guild_id'],
            title="Test Quest",
            description="A test quest",
            objectives=[],
            rewards={},
            created_by=mock_context['user_id']
        )
        
        result = await tool_executor.execute_tool(
            "get_quests",
            {"status": "available"},
            mock_context
        )
        
        assert "Test Quest" in result or "quest" in result.lower()


# =============================================================================
# NPC TOOL TESTS
# =============================================================================

class TestNPCTools:
    """Tests for NPC-related tools"""

    async def test_create_npc(self, tool_executor, mock_context):
        """Test creating an NPC"""
        result = await tool_executor.execute_tool(
            "create_npc",
            {
                "name": "Merchant Mike",
                "description": "A friendly merchant",
                "personality": "Cheerful and helpful",
                "npc_type": "friendly",
                "location": "Market Square"
            },
            mock_context
        )
        
        assert "Merchant Mike" in result or "created" in result.lower()

    async def test_get_npc_info(self, tool_executor, mock_context):
        """Test getting NPC info"""
        # Create NPC first
        npc_id = await tool_executor.db.create_npc(
            guild_id=mock_context['guild_id'],
            name="Blacksmith Bob",
            description="A burly blacksmith",
            personality="Gruff but fair",
            created_by=mock_context['user_id']
        )
        
        result = await tool_executor.execute_tool(
            "get_npc_info",
            {"npc_id": npc_id},
            mock_context
        )
        
        assert "Blacksmith Bob" in result or "blacksmith" in result.lower()

    async def test_get_npcs(self, tool_executor, mock_context):
        """Test getting NPCs in a location"""
        # Create some NPCs
        await tool_executor.db.create_npc(
            guild_id=mock_context['guild_id'],
            name="Guard 1",
            description="A city guard",
            personality="Alert",
            created_by=mock_context['user_id'],
            location="City Gate"
        )
        
        result = await tool_executor.execute_tool(
            "get_npcs",
            {"location": "City Gate"},
            mock_context
        )
        
        assert "Guard" in result or "NPC" in result


# =============================================================================
# MEMORY TOOL TESTS
# =============================================================================

class TestMemoryTools:
    """Tests for memory-related tools"""

    async def test_save_memory(self, tool_executor, mock_context):
        """Test saving a memory"""
        result = await tool_executor.execute_tool(
            "save_memory",
            {
                "key": "player_preference",
                "value": "likes stealth approaches",
                "context": "During goblin encounter"
            },
            mock_context
        )
        
        assert "saved" in result.lower() or "memory" in result.lower()

    async def test_get_player_memories(self, tool_executor, mock_context):
        """Test retrieving player memories"""
        # Save a memory first
        await tool_executor.db.save_memory(
            user_id=mock_context['user_id'],
            guild_id=mock_context['guild_id'],
            key="test_memory",
            value="test value"
        )
        
        result = await tool_executor.execute_tool(
            "get_player_memories",
            {"user_id": mock_context['user_id']},
            mock_context
        )
        
        assert "test" in result.lower() or "memory" in result.lower()


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestToolErrorHandling:
    """Tests for error handling in tool execution"""

    async def test_unknown_tool(self, tool_executor, mock_context):
        """Test calling an unknown tool"""
        result = await tool_executor.execute_tool(
            "nonexistent_tool",
            {},
            mock_context
        )
        
        assert "Unknown tool" in result or "Error" in result

    async def test_missing_required_args(self, tool_executor, mock_context):
        """Test calling tool with missing required arguments"""
        # update_character_hp requires character_id
        result = await tool_executor.execute_tool(
            "update_character_hp",
            {"hp_change": 5},  # Missing character_id
            mock_context
        )
        
        # Should handle gracefully
        assert "Error" in result or "not found" in result.lower()
