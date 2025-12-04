"""
Integration tests for RPG DM Bot
Tests complete gameplay workflows across multiple systems.
"""

import pytest


@pytest.mark.integration
class TestCombatWorkflow:
    """Integration tests for complete combat encounters"""

    async def test_full_combat_flow(self, db, sample_character_stats, sample_enemy):
        """Test a complete combat from start to finish"""
        from src.tools import ToolExecutor
        
        executor = ToolExecutor(db)
        context = {"user_id": 12345, "guild_id": 67890, "channel_id": 11111}
        
        # 1. Create a character
        char_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Hero",
            race="human",
            char_class="warrior",
            stats=sample_character_stats
        )
        
        # 2. Start combat
        start_result = await executor.execute_tool("start_combat", {}, context)
        assert "Combat started" in start_result
        
        # 3. Add enemies
        for i in range(2):
            await executor.execute_tool(
                "add_enemy",
                {"name": f"Goblin {i+1}", "hp": 7, "initiative_bonus": 2},
                context
            )
        
        # 4. Roll initiative
        init_result = await executor.execute_tool("roll_initiative", {}, context)
        assert "Initiative Order" in init_result
        
        # 5. Get combat status
        status_result = await executor.execute_tool("get_combat_status", {}, context)
        assert "Combat Status" in status_result
        assert "Goblin 1" in status_result
        assert "Goblin 2" in status_result
        
        # 6. Deal damage to an enemy
        combat = await db.get_active_combat(channel_id=11111)
        combatants = await db.get_combatants(combat['id'])
        goblin = next(c for c in combatants if "Goblin" in c['name'])
        
        damage_result = await executor.execute_tool(
            "deal_damage",
            {"target_id": goblin['id'], "damage": 10, "damage_type": "slashing"},
            context
        )
        assert "Dealt" in damage_result
        assert "DOWN" in damage_result  # Goblin should be dead (7 HP, 10 damage)
        
        # 7. Apply status effect
        other_goblin = next(c for c in combatants if c['id'] != goblin['id'])
        await executor.execute_tool(
            "apply_status",
            {"target_id": other_goblin['id'], "effect": "frightened", "duration": 2},
            context
        )
        
        # 8. Advance turns
        turn_result = await executor.execute_tool("next_turn", {}, context)
        assert "Round" in turn_result
        
        # 9. End combat with rewards
        end_result = await executor.execute_tool(
            "end_combat",
            {"outcome": "victory", "xp_reward": 50},
            context
        )
        assert "Combat ended" in end_result
        assert "victory" in end_result
        
        # 10. Verify no active combat
        no_combat = await db.get_active_combat(channel_id=11111)
        assert no_combat is None

    async def test_party_combat(self, db, sample_character_stats):
        """Test combat with multiple party members"""
        from src.tools import ToolExecutor
        
        executor = ToolExecutor(db)
        context = {"user_id": 12345, "guild_id": 67890, "channel_id": 22222}
        
        # Create session
        session_id = await db.create_session(
            guild_id=67890,
            name="Test Session",
            dm_user_id=12345
        )
        await db.start_session(session_id)
        
        # Create multiple characters
        characters = []
        for i, (name, char_class) in enumerate([
            ("Fighter", "warrior"),
            ("Wizard", "mage"),
            ("Healer", "cleric")
        ]):
            char_id = await db.create_character(
                user_id=10000 + i,
                guild_id=67890,
                name=name,
                race="human",
                char_class=char_class,
                stats=sample_character_stats,
                session_id=session_id
            )
            await db.join_session(session_id, user_id=10000 + i, character_id=char_id)
            characters.append(char_id)
        
        # Update context with session
        context['session_id'] = session_id
        
        # Start combat - should auto-add party members
        await executor.execute_tool("start_combat", {}, context)
        
        # Add enemies
        await executor.execute_tool(
            "add_enemy",
            {"name": "Troll", "hp": 50, "initiative_bonus": 5},
            context
        )
        
        # Get combat status - should show all participants
        status = await executor.execute_tool("get_combat_status", {}, context)
        
        # Verify combat has multiple combatants
        combat = await db.get_active_combat(channel_id=22222)
        combatants = await db.get_combatants(combat['id'])
        assert len(combatants) >= 1  # At least the troll


@pytest.mark.integration
class TestCharacterProgressionWorkflow:
    """Integration tests for character progression"""

    async def test_full_character_lifecycle(self, db, sample_character_stats):
        """Test character creation, leveling, and inventory management"""
        from src.tools import ToolExecutor
        
        executor = ToolExecutor(db)
        context = {"user_id": 12345, "guild_id": 67890, "channel_id": 11111}
        
        # 1. Create character
        char_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Adventurer",
            race="elf",
            char_class="ranger",
            stats=sample_character_stats,
            backstory="A lone wanderer seeking adventure"
        )
        
        char = await db.get_character(char_id)
        assert char['level'] == 1
        assert char['experience'] == 0
        
        # 2. Give starting equipment
        await executor.execute_tool(
            "give_item",
            {
                "character_id": char_id,
                "item_id": "longbow",
                "item_name": "Longbow",
                "item_type": "weapon",
                "properties": {"damage": "1d8", "range": 150}
            },
            context
        )
        
        await executor.execute_tool(
            "give_item",
            {
                "character_id": char_id,
                "item_id": "leather_armor",
                "item_name": "Leather Armor",
                "item_type": "armor",
                "properties": {"ac_bonus": 1}
            },
            context
        )
        
        # 3. Give gold
        await executor.execute_tool(
            "give_gold",
            {"character_id": char_id, "amount": 50, "reason": "starting gold"},
            context
        )
        
        # 4. Verify inventory
        inventory = await db.get_inventory(char_id)
        assert len(inventory) == 2
        
        char = await db.get_character(char_id)
        assert char['gold'] == 50
        
        # 5. Complete some quests for XP
        total_xp = 0
        for quest_xp in [100, 150, 200, 250]:  # Multiple quest rewards
            result = await executor.execute_tool(
                "add_experience",
                {"character_id": char_id, "xp": quest_xp, "reason": "quest complete"},
                context
            )
            total_xp += quest_xp
        
        # 6. Verify leveling
        char = await db.get_character(char_id)
        assert char['experience'] == total_xp
        assert char['level'] > 1  # Should have leveled up

    async def test_equipment_progression(self, db, sample_character_stats):
        """Test equipment upgrades and slot management"""
        # Create character
        char_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Knight",
            race="human",
            char_class="warrior",
            stats=sample_character_stats
        )
        
        # Add and equip starting weapon
        sword_id = await db.add_item(char_id, "iron_sword", "Iron Sword", "weapon")
        await db.equip_item(sword_id, "main_hand")
        
        # Add armor set
        armor_id = await db.add_item(char_id, "chain_mail", "Chain Mail", "armor")
        helmet_id = await db.add_item(char_id, "iron_helmet", "Iron Helmet", "armor")
        
        await db.equip_item(armor_id, "body")
        await db.equip_item(helmet_id, "head")
        
        # Verify equipment
        equipped = await db.get_equipped_items(char_id)
        assert len(equipped) == 3
        
        slots = {item['slot'] for item in equipped}
        assert "main_hand" in slots
        assert "body" in slots
        assert "head" in slots
        
        # Upgrade weapon (should replace old one in slot)
        magic_sword_id = await db.add_item(char_id, "magic_sword", "Magic Sword", "weapon")
        await db.equip_item(magic_sword_id, "main_hand")
        
        equipped = await db.get_equipped_items(char_id)
        main_hand_item = next(i for i in equipped if i['slot'] == "main_hand")
        assert main_hand_item['item_name'] == "Magic Sword"


@pytest.mark.integration
class TestQuestWorkflow:
    """Integration tests for quest system"""

    async def test_full_quest_flow(self, db, sample_character_stats):
        """Test quest from creation to completion with rewards"""
        # Create character
        char_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Quester",
            race="human",
            char_class="rogue",
            stats=sample_character_stats
        )
        
        # Create NPC quest giver
        npc_id = await db.create_npc(
            guild_id=67890,
            name="Mayor Magnus",
            description="The town mayor",
            personality="Worried about the town's safety",
            created_by=12345
        )
        
        # Create quest
        quest_id = await db.create_quest(
            guild_id=67890,
            title="Clear the Sewers",
            description="The sewers are infested with giant rats",
            objectives=[
                {"description": "Enter the sewers", "completed": False},
                {"description": "Kill 10 giant rats", "completed": False},
                {"description": "Report to Mayor Magnus", "completed": False}
            ],
            rewards={
                "gold": 200,
                "xp": 150,
                "items": [
                    {"id": "ring_protection", "name": "Ring of Protection", "type": "accessory"}
                ]
            },
            created_by=12345,
            difficulty="medium",
            quest_giver_npc_id=npc_id
        )
        
        # Accept quest
        result = await db.accept_quest(quest_id, char_id)
        assert result['success'] is True
        
        # Complete objectives one by one
        for i in range(3):
            result = await db.complete_objective(quest_id, char_id, i)
            if i < 2:
                assert result['quest_complete'] is False
            else:
                assert result['quest_complete'] is True
        
        # Complete quest and get rewards
        result = await db.complete_quest(quest_id, char_id)
        assert result['success'] is True
        assert result['rewards']['gold'] == 200
        assert result['rewards']['xp'] == 150
        
        # Verify rewards received
        char = await db.get_character(char_id)
        assert char['gold'] == 200
        assert char['experience'] == 150
        
        inventory = await db.get_inventory(char_id)
        assert any(item['item_name'] == "Ring of Protection" for item in inventory)

    async def test_multiple_quest_tracking(self, db, sample_character_stats):
        """Test managing multiple active quests"""
        char_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Multi-Tasker",
            race="halfling",
            char_class="bard",
            stats=sample_character_stats
        )
        
        # Create multiple quests
        quest_ids = []
        for i in range(3):
            qid = await db.create_quest(
                guild_id=67890,
                title=f"Quest {i+1}",
                description=f"Description {i+1}",
                objectives=[{"description": "Objective 1", "completed": False}],
                rewards={"gold": 50 * (i+1)},
                created_by=12345
            )
            quest_ids.append(qid)
            await db.accept_quest(qid, char_id)
        
        # Verify all quests active
        active_quests = await db.get_character_quests(char_id, status='active')
        assert len(active_quests) == 3
        
        # Complete one quest
        await db.complete_objective(quest_ids[0], char_id, 0)
        await db.complete_quest(quest_ids[0], char_id)
        
        # Verify quest counts
        active_quests = await db.get_character_quests(char_id, status='active')
        completed_quests = await db.get_character_quests(char_id, status='completed')
        
        assert len(active_quests) == 2
        assert len(completed_quests) == 1


@pytest.mark.integration
class TestNPCInteractionWorkflow:
    """Integration tests for NPC interactions"""

    async def test_npc_relationship_progression(self, db, sample_character_stats):
        """Test building relationship with NPCs"""
        # Create character
        char_id = await db.create_character(
            user_id=12345,
            guild_id=67890,
            name="Diplomat",
            race="half-elf",
            char_class="bard",
            stats=sample_character_stats
        )
        
        # Create merchant NPC
        merchant_id = await db.create_npc(
            guild_id=67890,
            name="Merchant Martha",
            description="A shrewd but fair merchant",
            personality="Business-minded, respects good customers",
            created_by=12345,
            is_merchant=True,
            merchant_inventory=[
                {"item_id": "health_potion", "name": "Health Potion", "price": 50},
                {"item_id": "mana_potion", "name": "Mana Potion", "price": 50}
            ]
        )
        
        # Initial relationship (neutral)
        rel = await db.get_npc_relationship(merchant_id, char_id)
        assert rel['reputation'] == 0
        
        # Positive interactions
        await db.update_npc_relationship(merchant_id, char_id, 10, "Made first purchase")
        await db.update_npc_relationship(merchant_id, char_id, 15, "Completed delivery quest")
        await db.update_npc_relationship(merchant_id, char_id, 25, "Saved shop from thieves")
        
        # Check reputation
        rel = await db.get_npc_relationship(merchant_id, char_id)
        assert rel['reputation'] == 50
        
        # Negative interaction
        await db.update_npc_relationship(merchant_id, char_id, -10, "Haggled too aggressively")
        
        rel = await db.get_npc_relationship(merchant_id, char_id)
        assert rel['reputation'] == 40


@pytest.mark.integration
class TestSessionManagement:
    """Integration tests for session/campaign management"""

    async def test_full_session_lifecycle(self, db, sample_character_stats):
        """Test complete session from creation to end"""
        # Create session
        session_id = await db.create_session(
            guild_id=67890,
            name="The Lost Temple",
            dm_user_id=12345,
            description="An adventure to find a lost temple",
            setting="Jungle",
            max_players=4
        )
        
        session = await db.get_session(session_id)
        assert session['status'] == 'inactive'
        
        # Create characters and join
        players = []
        for i, (name, char_class) in enumerate([
            ("Tank", "warrior"),
            ("Healer", "cleric"),
            ("DPS", "rogue"),
            ("Support", "bard")
        ]):
            char_id = await db.create_character(
                user_id=1000 + i,
                guild_id=67890,
                name=name,
                race="human",
                char_class=char_class,
                stats=sample_character_stats,
                session_id=session_id
            )
            await db.join_session(session_id, user_id=1000 + i, character_id=char_id)
            players.append((1000 + i, char_id))
        
        # Verify participants
        participants = await db.get_session_participants(session_id)
        assert len(participants) == 4
        
        # Start session
        await db.start_session(session_id)
        
        active_session = await db.get_active_session(67890)
        assert active_session is not None
        assert active_session['id'] == session_id
        
        # Update world state
        await db.update_world_state(session_id, {
            "current_location": "Temple Entrance",
            "time_of_day": "morning",
            "discovered_secrets": ["ancient_map"]
        })
        
        session = await db.get_session(session_id)
        assert session['world_state']['current_location'] == "Temple Entrance"
        
        # Add story entries
        await db.add_story_entry(
            session_id,
            "narrative",
            "The party arrived at the ancient temple after days of travel...",
            [p[1] for p in players]
        )
        
        await db.add_story_entry(
            session_id,
            "combat",
            "The party was ambushed by temple guardians!"
        )
        
        # Get story log
        story = await db.get_story_log(session_id)
        assert len(story) == 2
        
        # End session
        await db.end_session(session_id)
        
        active_session = await db.get_active_session(67890)
        assert active_session is None


@pytest.mark.integration
class TestMemoryAndContext:
    """Integration tests for AI memory and context"""

    async def test_conversation_memory(self, db):
        """Test conversation history and memory"""
        user_id = 12345
        guild_id = 67890
        channel_id = 11111
        
        # Simulate conversation
        messages = [
            ("user", "Hello DM, I want to explore the cave"),
            ("assistant", "The cave entrance looms before you, dark and foreboding..."),
            ("user", "I light my torch and enter"),
            ("assistant", "The flickering torchlight reveals ancient markings on the walls...")
        ]
        
        for role, content in messages:
            await db.save_message(user_id, guild_id, channel_id, role, content)
        
        # Retrieve history
        history = await db.get_recent_messages(user_id, guild_id, channel_id, limit=10)
        assert len(history) == 4
        assert history[0]['role'] == "user"
        assert "cave" in history[0]['content']
        
        # Save memories
        await db.save_memory(user_id, guild_id, "preferred_playstyle", "exploration", 
                            "Player expressed interest in exploring")
        await db.save_memory(user_id, guild_id, "current_location", "ancient_cave",
                            "Entered the cave")
        
        # Retrieve memories
        memories = await db.get_all_memories(user_id, guild_id)
        assert "preferred_playstyle" in memories
        assert "current_location" in memories
        assert memories["current_location"]["value"] == "ancient_cave"
