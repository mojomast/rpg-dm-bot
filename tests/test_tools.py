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

    async def test_award_experience_alias(self, tool_executor_with_character, mock_context):
        """Test legacy award_experience alias routes to add_experience."""
        executor, db, char_id = tool_executor_with_character

        result = await executor.execute_tool(
            "award_experience",
            {"character_id": char_id, "xp": 50, "reason": "story milestone"},
            mock_context,
        )

        assert "50 XP" in result
        assert "story milestone" in result

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

    async def test_start_combat_adds_session_participants_with_snapshot_ac(self, tool_executor, mock_context):
        """Tool combat start should add all bound session participants with canonical AC snapshots."""
        db = tool_executor.db
        session_id = await db.create_session(67890, "Test Campaign", 12345)
        stats_one = {"strength": 16, "dexterity": 14, "constitution": 15, "intelligence": 10, "wisdom": 12, "charisma": 8}
        stats_two = {"strength": 12, "dexterity": 10, "constitution": 14, "intelligence": 10, "wisdom": 15, "charisma": 11}
        char_one = await db.create_character(12345, 67890, "Aria", "human", "warrior", stats_one, session_id=session_id)
        char_two = await db.create_character(54321, 67890, "Borin", "dwarf", "cleric", stats_two, session_id=session_id)
        await db.add_item(char_one, "armor_chain", "Chain Mail", "armor", is_equipped=True, slot="body", properties={"ac_base": 16, "max_dex_bonus": 0})
        await db.add_item(char_one, "shield_wooden", "Wooden Shield", "armor", is_equipped=True, slot="off_hand", properties={"ac_bonus": 2})
        await db.add_session_player(session_id, char_one)
        await db.add_session_player(session_id, char_two)
        mock_context['session_id'] = session_id

        result = await tool_executor.execute_tool("start_combat", {}, mock_context)

        assert "Combat started" in result
        combat = await db.get_active_combat(channel_id=11111)
        combatants = await db.get_combatants(combat['id'])
        assert {combatant['name'] for combatant in combatants} == {"Aria", "Borin"}
        aria = next(c for c in combatants if c['name'] == "Aria")
        assert aria['armor_class'] == 18

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
                "initiative_bonus": 2,
                "stats": {"ac": sample_enemy['ac']}
            },
            mock_context
        )
        
        assert "Added" in result
        assert sample_enemy['name'] in result
        assert "AC: 15" in result

        combat = await tool_executor.db.get_active_combat(channel_id=mock_context['channel_id'])
        combatants = await tool_executor.db.get_combatants(combat['id'])
        enemy = next(c for c in combatants if c['participant_type'] == 'enemy')
        assert enemy['armor_class'] == 15
        assert enemy['combat_stats']['ac'] == 15
        assert enemy['combat_stats']['armor_class'] == 15

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
        combat = await tool_executor.db.get_active_combat(channel_id=mock_context['channel_id'])
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
        
        combat = await tool_executor.db.get_active_combat(channel_id=mock_context['channel_id'])
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
        
        combat = await tool_executor.db.get_active_combat(channel_id=mock_context['channel_id'])
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
        
        combat = await tool_executor.db.get_active_combat(channel_id=mock_context['channel_id'])
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

    async def test_roll_attack_uses_target_armor_class(self, tool_executor, mock_context):
        """Tool attack resolution should use persisted target AC instead of a default."""
        await tool_executor.execute_tool("start_combat", {}, mock_context)
        combat = await tool_executor.db.get_active_combat(channel_id=mock_context['channel_id'])
        attacker_id = await tool_executor.db.add_combatant(
            combat['id'], "character", 12345, "Test Hero", 20, 20, 2, is_player=True
        )
        await tool_executor.execute_tool(
            "add_enemy",
            {"name": "Goblin", "hp": 7, "stats": {"ac": 15}},
            mock_context,
        )

        combatants = await tool_executor.db.get_combatants(combat['id'])
        target = next(c for c in combatants if not c['is_player'])

        original_roll = tool_executor.dice.roll
        rolls = iter([
            {"total": 14, "rolls": [10], "kept": [10], "modifier": 4, "critical": False, "fumble": False},
        ])
        tool_executor.dice.roll = lambda *args, **kwargs: next(rolls)
        try:
            result = await tool_executor.execute_tool(
                "roll_attack",
                {
                    "attacker_id": attacker_id,
                    "target_id": target['id'],
                    "attack_bonus": 4,
                    "damage_dice": "1d8+3",
                },
                mock_context,
            )
        finally:
            tool_executor.dice.roll = original_roll

        assert "vs AC 15" in result
        assert "MISS" in result


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
                "objectives": [
                    {"description": "Find the entrance", "optional": False},
                    "Defeat the guardian",
                ],
                "rewards": {"gold": 100, "xp": 50},
                "difficulty": "medium"
            },
            mock_context
        )
        
        # Should confirm quest creation
        assert "quest" in result.lower() or "created" in result.lower()

        quests = await tool_executor.db.get_available_quests(mock_context['guild_id'])
        quest = next(q for q in quests if q['title'] == "The Dark Cave")
        assert quest['objectives'][0]['description'] == "Find the entrance"
        assert quest['objectives'][1]['description'] == "Defeat the guardian"

    async def test_create_quest_requires_valid_objective(self, tool_executor, mock_context):
        """Test create_quest rejects empty objective input."""
        result = await tool_executor.execute_tool(
            "create_quest",
            {
                "title": "Bad Quest",
                "description": "No real objective",
                "objectives": [{"optional": True}, "   "],
            },
            mock_context,
        )

        assert "valid quest objective" in result.lower()

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
        
        assert "remembered" in result.lower() or "saved" in result.lower() or "memory" in result.lower()

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


# =============================================================================
# HARDENING REGRESSION TESTS
# =============================================================================

class TestHardeningRegressions:
    """Focused tests for hardened tool/database contracts."""

    async def test_short_rest_uses_db_return_safely(self, tool_executor_with_character, mock_context):
        """short_rest should format output from the DB contract without crashing."""
        executor, db, char_id = tool_executor_with_character
        await db.update_character(char_id, hp=5, mana=1)

        result = await executor.execute_tool(
            "short_rest",
            {"character_id": char_id},
            mock_context,
        )

        assert "short rest" in result.lower()
        assert "Recovered" in result

    async def test_get_comprehensive_session_state_handles_real_db_shape(self, tool_executor, mock_context):
        """Comprehensive session state should handle the DB's flattened payload."""
        session_id = await tool_executor.db.create_session(
            guild_id=mock_context['guild_id'],
            name="State Test",
            dm_user_id=mock_context['user_id'],
            description="State coverage",
        )
        await tool_executor.db.start_session(session_id)

        result = await tool_executor.execute_tool(
            "get_comprehensive_session_state",
            {"session_id": session_id},
            mock_context,
        )

        assert "Session State" in result
        assert "State Test" in result

    async def test_end_combat_with_rewards_uses_current_db_contract(self, tool_executor_with_character, mock_context):
        """Combat reward wrapper should use the DB's current kwargs and return shape."""
        executor, db, char_id = tool_executor_with_character
        mock_context['user_id'] = 12345
        mock_context['guild_id'] = 67890

        await db.create_session(guild_id=67890, name="Combat Rewards", dm_user_id=12345)
        await executor.execute_tool("start_combat", {}, mock_context)

        result = await executor.execute_tool(
            "end_combat_with_rewards",
            {"victory": True, "bonus_xp": 25, "bonus_gold": 10},
            mock_context,
        )

        assert "VICTORY" in result
        assert "Error" not in result


class TestTravelTools:
    async def test_move_party_to_connected_location_updates_session_and_party(self, tool_executor, db, sample_character_stats, mock_context):
        session_id = await db.create_session(
            guild_id=67890,
            name="Travel Session",
            dm_user_id=12345,
        )
        await db.update_session(session_id, status='active')
        town_id = await db.create_location(
            guild_id=67890,
            session_id=session_id,
            created_by=12345,
            name="Oakheart",
            description="Town square",
            location_type="town",
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
        await db.join_session(session_id, 12345, character_id=char_id)
        await db.save_game_state(session_id, current_location='Oakheart', current_location_id=town_id)
        await db.update_character(char_id, current_location_id=town_id)

        result = await tool_executor.execute_tool(
            "move_party_to_location",
            {"location_id": forest_id, "travel_description": "The road bends into the pines."},
            {**mock_context, "session_id": session_id},
        )

        assert "Whisperwood" in result
        state = await db.get_game_state(session_id)
        assert state['current_location_id'] == forest_id
        char = await db.get_character(char_id)
        assert char['current_location_id'] == forest_id

    async def test_move_party_to_unconnected_location_is_rejected(self, tool_executor, db, sample_character_stats, mock_context):
        session_id = await db.create_session(
            guild_id=67890,
            name="Travel Session",
            dm_user_id=12345,
        )
        await db.update_session(session_id, status='active')
        town_id = await db.create_location(
            guild_id=67890,
            session_id=session_id,
            created_by=12345,
            name="Oakheart",
            description="Town square",
            location_type="town",
        )
        mountain_id = await db.create_location(
            guild_id=67890,
            session_id=session_id,
            created_by=12345,
            name="Stormpeak",
            description="Frozen cliffs",
            location_type="landmark",
        )
        char_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Aria",
            race="human",
            char_class="warrior",
            stats=sample_character_stats,
            session_id=session_id,
        )
        await db.join_session(session_id, 12345, character_id=char_id)
        await db.save_game_state(session_id, current_location='Oakheart', current_location_id=town_id)
        await db.update_character(char_id, current_location_id=town_id)

        result = await tool_executor.execute_tool(
            "move_party_to_location",
            {"location_id": mountain_id},
            {**mock_context, "session_id": session_id},
        )

        assert "not directly connected" in result
        state = await db.get_game_state(session_id)
        assert state['current_location_id'] == town_id


class TestMonsterTemplateTools:
    async def test_spawn_enemy_template_combatants_uses_pack_stats(self, tool_executor, db, mock_context):
        session_id = await db.create_session(
            guild_id=67890,
            name='Template Combat',
            dm_user_id=12345,
        )
        await db.update_session(session_id, status='active', content_pack_id='fantasy_core')
        encounter_id = await db.create_combat(guild_id=67890, channel_id=999, session_id=session_id)

        created_ids = await tool_executor.spawn_enemy_template_combatants(
            encounter_id,
            'goblin',
            count=2,
            context={'session_id': session_id, 'guild_id': 67890},
        )

        assert len(created_ids) == 2
        participants = await db.get_combatants(encounter_id)
        enemies = [participant for participant in participants if participant['participant_type'] == 'enemy']
        assert len(enemies) == 2
        assert enemies[0]['armor_class'] == 12
        assert enemies[0]['combat_stats']['template_id'] == 'goblin'

    async def test_list_enemy_templates_returns_sorted_templates(self, tool_executor, db):
        session_id = await db.create_session(
            guild_id=67890,
            name='Template Listing',
            dm_user_id=12345,
        )
        await db.update_session(session_id, status='active', content_pack_id='fantasy_core')

        templates = await tool_executor.list_enemy_templates({'session_id': session_id, 'guild_id': 67890})

        assert templates
        assert any(template['id'] == 'goblin' for template in templates)
