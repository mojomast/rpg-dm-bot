"""
RPG DM Bot - Tool Executor
Handles execution of LLM tool calls for game mechanics.
"""

import random
import re
from typing import List, Dict, Any, Optional
import json
import logging

from src.content_packs import load_content_file, load_session_content_file
from src.tool_schemas import TOOLS_SCHEMA, get_tool_names
from src.mechanics_tracker import get_tracker, MechanicType

logger = logging.getLogger('rpg.tools')


class DiceRoller:
    """Utility class for dice rolling"""
    
    DICE_PATTERN = re.compile(r'(\d+)?d(\d+)([+-]\d+)?(?:kh(\d+))?(?:kl(\d+))?')
    
    @classmethod
    def roll(cls, expression: str, advantage: bool = False, 
             disadvantage: bool = False) -> Dict[str, Any]:
        """
        Roll dice from an expression like '2d6+3', '1d20', '4d6kh3'
        kh = keep highest, kl = keep lowest
        """
        expression = expression.lower().replace(' ', '')
        match = cls.DICE_PATTERN.match(expression)
        
        if not match:
            return {"error": f"Invalid dice expression: {expression}"}
        
        num_dice = int(match.group(1) or 1)
        die_size = int(match.group(2))
        modifier = int(match.group(3) or 0)
        keep_highest = int(match.group(4)) if match.group(4) else None
        keep_lowest = int(match.group(5)) if match.group(5) else None
        
        # Roll the dice
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        
        # Handle advantage/disadvantage for d20 rolls
        if die_size == 20 and num_dice == 1:
            if advantage:
                second_roll = random.randint(1, 20)
                rolls = [max(rolls[0], second_roll)]
                result = {
                    "rolls": [rolls[0], second_roll],
                    "kept": [max(rolls[0], second_roll)],
                    "advantage": True
                }
            elif disadvantage:
                second_roll = random.randint(1, 20)
                rolls = [min(rolls[0], second_roll)]
                result = {
                    "rolls": [rolls[0], second_roll],
                    "kept": [min(rolls[0], second_roll)],
                    "disadvantage": True
                }
            else:
                result = {"rolls": rolls, "kept": rolls}
        else:
            # Handle keep highest/lowest
            kept = rolls.copy()
            if keep_highest:
                kept = sorted(rolls, reverse=True)[:keep_highest]
            elif keep_lowest:
                kept = sorted(rolls)[:keep_lowest]
            result = {"rolls": rolls, "kept": kept}
        
        subtotal = sum(result["kept"])
        total = subtotal + modifier
        
        # Check for natural 20/1 on d20
        is_nat_20 = die_size == 20 and num_dice == 1 and result["kept"][0] == 20
        is_nat_1 = die_size == 20 and num_dice == 1 and result["kept"][0] == 1
        
        return {
            **result,
            "expression": expression,
            "modifier": modifier,
            "subtotal": subtotal,
            "total": total,
            "natural_20": is_nat_20,
            "natural_1": is_nat_1,
            "critical": is_nat_20,
            "fumble": is_nat_1
        }


class ToolExecutor:
    """Executes tool calls from the LLM"""
    
    def __init__(self, db):
        self.db = db
        self.dice = DiceRoller()

    async def _load_theme_content(self, context: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Load static content from the active session's content pack, defaulting to fantasy_core."""
        session = await self._get_session_for_context(context)
        return load_session_content_file(session, filename)

    async def _get_context_character(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Prefer an explicit character in context before active-character lookup."""
        character_id = context.get('character_id')
        if character_id:
            return await self.db.get_character(character_id)

        user_id = context.get('user_id')
        guild_id = context.get('guild_id')
        if user_id and guild_id:
            return await self.db.get_active_character(user_id, guild_id)

        return None
    
    async def _get_session_for_context(self, context: Dict[str, Any]) -> Optional[Dict]:
        """Get the correct session for the given context.
        
        Uses session_id from context if available (preferred for session isolation),
        otherwise falls back to user's active session, then guild's active session.
        """
        session_id = context.get('session_id')
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        
        # If we have a specific session_id, use it
        if session_id:
            session = await self.db.get_session(session_id)
            if session:
                return session
        
        # Fall back to user's active session (preferred over any guild session)
        if user_id and guild_id:
            user_session = await self.db.get_user_active_session(guild_id, user_id)
            if user_session:
                return user_session
        
        # Last resort: get any active session for the guild
        if guild_id:
            return await self.db.get_active_session(guild_id)
        
        return None
    
    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any], 
                           context: Dict[str, Any]) -> str:
        """Execute a tool by name with arguments"""
        logger.info(f"Executing tool {tool_name} with args {tool_args}")
        
        try:
            if tool_name == "award_experience":
                tool_name = "add_experience"
            elif tool_name == "update_weather":
                tool_name = "update_location"
                tool_args = {
                    "location_id": tool_args.get("location_id"),
                    "current_weather": tool_args.get("weather") or tool_args.get("current_weather"),
                }

            # Character tools
            if tool_name == "get_character_info":
                return await self._get_character_info(context, tool_args)
            elif tool_name == "update_character_hp":
                return await self._update_character_hp(tool_args)
            elif tool_name == "add_experience":
                return await self._add_experience(tool_args)
            elif tool_name == "update_character_stats":
                return await self._update_character_stats(tool_args)
            
            # Inventory tools
            elif tool_name == "give_item":
                return await self._give_item(tool_args)
            elif tool_name == "remove_item":
                return await self._remove_item(tool_args)
            elif tool_name == "get_inventory":
                return await self._get_inventory(tool_args)
            elif tool_name == "give_gold":
                return await self._give_gold(tool_args)
            elif tool_name == "take_gold":
                return await self._take_gold(tool_args)
            
            # Combat tools
            elif tool_name == "start_combat":
                return await self._start_combat(context, tool_args)
            elif tool_name == "add_enemy":
                return await self._add_enemy(context, tool_args)
            elif tool_name == "roll_initiative":
                return await self._roll_initiative(context)
            elif tool_name == "deal_damage":
                return await self._deal_damage(context, tool_args)
            elif tool_name == "heal_combatant":
                return await self._heal_combatant(context, tool_args)
            elif tool_name == "apply_status":
                return await self._apply_status(tool_args)
            elif tool_name == "next_turn":
                return await self._next_turn(context)
            elif tool_name == "get_combat_status":
                return await self._get_combat_status(context)
            elif tool_name == "end_combat":
                return await self._end_combat(context, tool_args)
            
            # Dice tools
            elif tool_name == "roll_dice":
                return await self._roll_dice(context, tool_args)
            elif tool_name == "roll_attack":
                return await self._roll_attack(context, tool_args)
            elif tool_name == "roll_save":
                return await self._roll_save(tool_args)
            elif tool_name == "roll_skill_check":
                return await self._roll_skill_check(tool_args)
            
            # Quest tools
            elif tool_name == "create_quest":
                return await self._create_quest(context, tool_args)
            elif tool_name == "update_quest":
                return await self._update_quest(tool_args)
            elif tool_name == "complete_objective":
                return await self._complete_objective(tool_args)
            elif tool_name == "give_quest_rewards":
                return await self._give_quest_rewards(tool_args)
            elif tool_name == "get_quests":
                return await self._get_quests(context, tool_args)
            
            # NPC tools
            elif tool_name == "get_npc_info":
                return await self._get_npc_info(tool_args)
            elif tool_name == "create_npc":
                return await self._create_npc(context, tool_args)
            elif tool_name == "update_npc_relationship":
                return await self._update_npc_relationship(tool_args)
            elif tool_name == "get_npcs":
                return await self._get_npcs(context, tool_args)
            
            # NPC Party Member tools
            elif tool_name == "add_npc_to_party":
                return await self._add_npc_to_party(context, tool_args)
            elif tool_name == "remove_npc_from_party":
                return await self._remove_npc_from_party(tool_args)
            elif tool_name == "get_party_npcs":
                return await self._get_party_npcs(context)
            elif tool_name == "update_npc_loyalty":
                return await self._update_npc_loyalty(tool_args)
            elif tool_name == "npc_party_action":
                return await self._npc_party_action(context, tool_args)
            
            # Session tools
            elif tool_name == "get_party_info":
                return await self._get_party_info(context)
            elif tool_name == "add_story_entry":
                return await self._add_story_entry(context, tool_args)
            elif tool_name == "get_story_log":
                return await self._get_story_log(context, tool_args)
            
            # Memory tools
            elif tool_name == "save_memory":
                return await self._save_memory(context, tool_args)
            elif tool_name == "get_player_memories":
                return await self._get_player_memories(context, tool_args)
            
            # Spell & Ability tools
            elif tool_name == "get_character_spells":
                return await self._get_character_spells(tool_args)
            elif tool_name == "cast_spell":
                return await self._cast_spell(context, tool_args)
            elif tool_name == "use_ability":
                return await self._use_ability(tool_args)
            elif tool_name == "get_character_abilities":
                return await self._get_character_abilities(tool_args)
            elif tool_name == "rest_character":
                return await self._rest_character(tool_args)
            
            # Location tools
            elif tool_name == "create_location":
                return await self._create_location(context, tool_args)
            elif tool_name == "get_location":
                return await self._get_location(tool_args)
            elif tool_name == "get_nearby_locations":
                return await self._get_nearby_locations(tool_args)
            elif tool_name == "update_location":
                return await self._update_location(tool_args)
            elif tool_name == "move_party_to_location":
                return await self._move_party_to_location(context, tool_args)
            
            # Story Item tools
            elif tool_name == "create_story_item":
                return await self._create_story_item(context, tool_args)
            elif tool_name == "reveal_story_item":
                return await self._reveal_story_item(tool_args)
            elif tool_name == "transfer_story_item":
                return await self._transfer_story_item(tool_args)
            elif tool_name == "get_story_items":
                return await self._get_story_items(context, tool_args)
            
            # Story Event tools
            elif tool_name == "create_story_event":
                return await self._create_story_event(context, tool_args)
            elif tool_name == "trigger_event":
                return await self._trigger_event(tool_args)
            elif tool_name == "resolve_event":
                return await self._resolve_event(tool_args)
            elif tool_name == "get_active_events":
                return await self._get_active_events(context)
            
            # Enhanced NPC tools  
            elif tool_name == "generate_npc":
                return await self._generate_npc(context, tool_args)
            elif tool_name == "generate_npc_dialogue":
                return await self._generate_npc_dialogue(context, tool_args)
            elif tool_name == "set_npc_secret":
                return await self._set_npc_secret(tool_args)
            
            # Cross-system wiring tools
            elif tool_name == "move_character_to_location":
                return await self._move_character_to_location(tool_args)
            elif tool_name == "get_characters_at_location":
                return await self._get_characters_at_location(tool_args)
            elif tool_name == "get_npcs_at_location":
                return await self._get_npcs_at_location(tool_args)
            elif tool_name == "explore_location":
                return await self._explore_location(context, tool_args)
            elif tool_name == "pickup_story_item":
                return await self._pickup_story_item(context, tool_args)
            elif tool_name == "drop_story_item":
                return await self._drop_story_item(context, tool_args)
            elif tool_name == "long_rest":
                return await self._long_rest(context, tool_args)
            elif tool_name == "short_rest":
                return await self._short_rest(tool_args)
            elif tool_name == "end_combat_with_rewards":
                return await self._end_combat_with_rewards(context, tool_args)
            elif tool_name == "complete_quest_with_rewards":
                return await self._complete_quest_with_rewards(context, tool_args)
            elif tool_name == "get_comprehensive_session_state":
                return await self._get_comprehensive_session_state(tool_args)
            
            # Generative AI / Worldbuilding tools
            elif tool_name == "generate_world":
                return await self._generate_world(context, tool_args)
            elif tool_name == "generate_key_npcs":
                return await self._generate_key_npcs(context, tool_args)
            elif tool_name == "generate_location":
                return await self._generate_location(context, tool_args)
            elif tool_name == "generate_quest":
                return await self._generate_quest(context, tool_args)
            elif tool_name == "generate_encounter":
                return await self._generate_encounter(context, tool_args)
            elif tool_name == "generate_backstory":
                return await self._generate_backstory(context, tool_args)
            elif tool_name == "generate_loot":
                return await self._generate_loot(context, tool_args)
            elif tool_name == "initialize_campaign":
                return await self._initialize_campaign(context, tool_args)
            
            else:
                return f"Error: Unknown tool '{tool_name}'"
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return f"Error executing tool: {str(e)}"
    
    # =========================================================================
    # CHARACTER TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _get_character_info(self, context: Dict, args: Dict) -> str:
        """Get character information"""
        char_id = args.get('character_id')
        user_id = args.get('user_id') or context.get('user_id')
        guild_id = context.get('guild_id')
        
        if char_id:
            char = await self.db.get_character(char_id)
        else:
            char = await self._get_context_character(context)
        
        if not char:
            return "No character found."
        
        # Get equipped items
        equipped = await self.db.get_equipped_items(char['id'])
        equipped_str = ", ".join([f"{i['item_name']} ({i['slot']})" for i in equipped]) or "None"
        
        return f"""**{char['name']}** - Level {char['level']} {char['race']} {char['char_class']}
HP: {char['hp']}/{char['max_hp']} | Mana: {char['mana']}/{char['max_mana']} | Gold: {char['gold']}
STR: {char['strength']} | DEX: {char['dexterity']} | CON: {char['constitution']}
INT: {char['intelligence']} | WIS: {char['wisdom']} | CHA: {char['charisma']}
XP: {char['experience']} | Equipped: {equipped_str}
Backstory: {char['backstory'] or 'Unknown'}"""
    
    async def _update_character_hp(self, args: Dict) -> str:
        """Update character HP"""
        char_id = args.get('character_id')
        hp_change = args.get('hp_change', 0)
        reason = args.get('reason', 'unspecified')
        
        char = await self.db.get_character(char_id)
        if not char:
            return "Error: Character not found"
        
        new_hp = max(0, min(char['max_hp'], char['hp'] + hp_change))
        await self.db.update_character(char_id, hp=new_hp)
        
        action = "healed" if hp_change > 0 else "took damage"
        return f"{char['name']} {action}: {abs(hp_change)} HP ({reason}). HP: {new_hp}/{char['max_hp']}"
    
    async def _add_experience(self, args: Dict) -> str:
        """Add experience to character"""
        char_id = args.get('character_id')
        xp = args.get('xp', 0)
        reason = args.get('reason', 'unspecified')
        
        result = await self.db.add_experience(char_id, xp)
        if 'error' in result:
            return f"Error: {result['error']}"
        
        msg = f"Gained {xp} XP ({reason}). Total: {result['total_xp']}"
        if result['leveled_up']:
            msg += f"\n🎉 LEVEL UP! Now level {result['new_level']}! +{result['hp_increase']} max HP!"
        return msg
    
    async def _update_character_stats(self, args: Dict) -> str:
        """Update character stats"""
        char_id = args.get('character_id')
        stat_changes = args.get('stat_changes', {})
        
        char = await self.db.get_character(char_id)
        if not char:
            return "Error: Character not found"
        
        updates = {}
        for stat, change in stat_changes.items():
            if stat in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma', 'mana']:
                if stat == 'mana':
                    new_val = max(0, min(char['max_mana'], char['mana'] + change))
                else:
                    new_val = max(1, char[stat] + change)
                updates[stat] = new_val
        
        if updates:
            await self.db.update_character(char_id, **updates)
            changes_str = ", ".join([f"{k}: {'+' if stat_changes[k] > 0 else ''}{stat_changes[k]}" for k in updates])
            return f"Stats updated for {char['name']}: {changes_str}"
        return "No valid stat changes provided."
    
    # =========================================================================
    # INVENTORY TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _give_item(self, args: Dict) -> str:
        """Give item to character"""
        char_id = args.get('character_id')
        item_id = args.get('item_id')
        item_name = args.get('item_name')
        item_type = args.get('item_type')
        quantity = args.get('quantity', 1)
        properties = args.get('properties', {})
        
        inv_id = await self.db.add_item(char_id, item_id, item_name, item_type, quantity, properties)
        return f"Added {quantity}x {item_name} to inventory (ID: {inv_id})"
    
    async def _remove_item(self, args: Dict) -> str:
        """Remove item from inventory"""
        inv_id = args.get('inventory_id')
        quantity = args.get('quantity', 1)
        
        success = await self.db.remove_item(inv_id, quantity)
        if success:
            return f"Removed {quantity}x item from inventory"
        return "Error: Item not found"
    
    async def _get_inventory(self, args: Dict) -> str:
        """Get character inventory"""
        char_id = args.get('character_id')
        
        items = await self.db.get_inventory(char_id)
        if not items:
            return "Inventory is empty."
        
        lines = []
        for item in items:
            equipped = "⚔️" if item['is_equipped'] else ""
            qty = f" x{item['quantity']}" if item['quantity'] > 1 else ""
            lines.append(f"{equipped}[{item['id']}] {item['item_name']}{qty} ({item['item_type']})")
        
        return "**Inventory:**\n" + "\n".join(lines)
    
    async def _give_gold(self, args: Dict) -> str:
        """Give gold to character"""
        char_id = args.get('character_id')
        amount = args.get('amount', 0)
        reason = args.get('reason', 'reward')
        
        new_gold = await self.db.update_gold(char_id, amount)
        return f"Gained {amount} gold ({reason}). Total: {new_gold} gold"
    
    async def _take_gold(self, args: Dict) -> str:
        """Remove gold from character"""
        char_id = args.get('character_id')
        amount = args.get('amount', 0)
        reason = args.get('reason', 'purchase')
        
        char = await self.db.get_character(char_id)
        if char['gold'] < amount:
            return f"Error: Not enough gold. Has {char['gold']}, needs {amount}"
        
        new_gold = await self.db.update_gold(char_id, -amount)
        return f"Spent {amount} gold ({reason}). Remaining: {new_gold} gold"
    
    # =========================================================================
    # COMBAT TOOL IMPLEMENTATIONS
    # =========================================================================

    async def add_character_combatant(self, encounter_id: int, character_id: int) -> Optional[int]:
        """Insert a character into combat using the canonical DB snapshot path."""
        char = await self.db.get_character(character_id)
        if not char:
            return None

        dex_mod = (char['dexterity'] - 10) // 2
        return await self.db.add_combatant(
            encounter_id,
            'character',
            char['id'],
            char['name'],
            char['hp'],
            char['max_hp'],
            dex_mod,
            is_player=True,
        )

    async def add_enemy_combatant(
        self,
        encounter_id: int,
        name: str,
        hp: int,
        initiative_bonus: int = 0,
        stats: Optional[Dict[str, Any]] = None,
        armor_class: Optional[int] = None,
    ) -> int:
        """Insert an enemy into combat using canonical stat normalization."""
        stats = dict(stats or {})
        if armor_class is None:
            armor_class = stats.get('ac') or stats.get('armor_class')
        if armor_class is None:
            armor_class = 10

        stats.setdefault('ac', armor_class)
        stats.setdefault('armor_class', armor_class)
        stats.setdefault('max_hp', max(hp or 0, 0))

        return await self.db.add_combatant(
            encounter_id,
            'enemy',
            0,
            name,
            hp,
            hp,
            initiative_bonus,
            is_player=False,
            armor_class=armor_class,
            combat_stats=stats,
        )
    
    async def _start_combat(self, context: Dict, args: Dict) -> str:
        """Start a combat encounter"""
        guild_id = context.get('guild_id')
        channel_id = context.get('channel_id')
        description = args.get('description', 'Combat begins!')
        
        # Check for existing combat
        existing = await self.db.get_active_combat(channel_id=channel_id)
        if existing:
            return "Error: Combat already active in this channel. End it first with end_combat."
        
        # Get session using proper isolation
        session = await self._get_session_for_context(context)
        session_id = session['id'] if session else None
        
        encounter_id = await self.db.create_combat(guild_id, channel_id, session_id)
        
        # Add all party members from THIS session to combat
        if session:
            participants = await self.db.get_session_participants(session['id'])
            for p in participants:
                if p.get('character_id'):
                    await self.add_character_combatant(encounter_id, p['character_id'])
        
        return f"⚔️ Combat started! (Encounter #{encounter_id})\n{description}\nUse add_enemy to add enemies, then roll_initiative to begin."
    
    async def _add_enemy(self, context: Dict, args: Dict) -> str:
        """Add enemy to combat"""
        channel_id = context.get('channel_id')
        name = args.get('name')
        hp = args.get('hp')
        init_bonus = args.get('initiative_bonus', 0)
        stats = dict(args.get('stats') or {})
        armor_class = args.get('armor_class')
        
        combat = await self.db.get_active_combat(channel_id=channel_id)
        if not combat:
            return "Error: No active combat. Start combat first."
        
        combatant_id = await self.add_enemy_combatant(
            combat['id'],
            name,
            hp,
            initiative_bonus=init_bonus,
            stats=stats,
            armor_class=armor_class,
        )

        normalized_ac = armor_class or stats.get('ac') or stats.get('armor_class') or 10
        
        return f"Added {name} to combat (HP: {hp}, AC: {normalized_ac}, ID: {combatant_id})"
    
    async def _roll_initiative(self, context: Dict) -> str:
        """Roll initiative for all combatants"""
        channel_id = context.get('channel_id')
        
        combat = await self.db.get_active_combat(channel_id=channel_id)
        if not combat:
            return "Error: No active combat."
        
        combatants = await self.db.get_combatants(combat['id'])
        results = []
        
        for c in combatants:
            roll = self.dice.roll(f"1d20+{c['initiative']}")
            # Update initiative with rolled value
            await self.db.update_combatant_initiative(c['id'], roll['total'])
            results.append((c['name'], roll['total'], c['is_player']))
        
        # Sort by initiative
        results.sort(key=lambda x: x[1], reverse=True)
        
        lines = ["**Initiative Order:**"]
        for i, (name, init, is_player) in enumerate(results):
            marker = "🎮" if is_player else "👹"
            lines.append(f"{i+1}. {marker} {name}: {init}")
        
        return "\n".join(lines)
    
    async def _deal_damage(self, context: Dict, args: Dict) -> str:
        """Deal damage to combatant"""
        channel_id = context.get('channel_id')
        target_id = args.get('target_id')
        damage = args.get('damage')
        damage_type = args.get('damage_type', 'physical')
        
        result = await self.db.update_combatant_hp(target_id, -damage)
        if 'error' in result:
            return f"Error: {result['error']}"
        
        status = f"💀 {result['name']} is DOWN!" if result['is_dead'] else f"{result['name']}: {result['new_hp']}/{result['max_hp']} HP"
        return f"Dealt {damage} {damage_type} damage to {result['name']}! {status}"
    
    async def _heal_combatant(self, context: Dict, args: Dict) -> str:
        """Heal a combatant"""
        target_id = args.get('target_id')
        healing = args.get('healing')
        
        result = await self.db.update_combatant_hp(target_id, healing)
        if 'error' in result:
            return f"Error: {result['error']}"
        
        return f"Healed {result['name']} for {healing} HP! Now at {result['new_hp']}/{result['max_hp']} HP"
    
    async def _apply_status(self, args: Dict) -> str:
        """Apply status effect"""
        target_id = args.get('target_id')
        effect = args.get('effect')
        duration = args.get('duration', -1)
        
        success = await self.db.add_status_effect(target_id, effect, duration)
        if success:
            dur_str = f"for {duration} rounds" if duration > 0 else "until removed"
            return f"Applied {effect} {dur_str}"
        return "Error: Could not apply status effect"
    
    async def _next_turn(self, context: Dict) -> str:
        """Advance to next turn"""
        channel_id = context.get('channel_id')
        
        combat = await self.db.get_active_combat(channel_id=channel_id)
        if not combat:
            return "Error: No active combat."
        
        result = await self.db.advance_combat_turn(combat['id'])
        if 'error' in result:
            return f"Error: {result['error']}"
        
        combatant = result['current_combatant']
        marker = "🎮" if combatant['is_player'] else "👹"
        return f"**Round {result['round']}** - {marker} {combatant['name']}'s turn! (HP: {combatant['current_hp']}/{combatant['max_hp']})"
    
    async def _get_combat_status(self, context: Dict) -> str:
        """Get current combat status"""
        channel_id = context.get('channel_id')
        
        combat = await self.db.get_active_combat(channel_id=channel_id)
        if not combat:
            return "No active combat."
        
        combatants = await self.db.get_combatants(combat['id'])
        
        lines = [f"**Combat Status** (Round {combat['round_number']})"]
        for c in combatants:
            hp_bar = "█" * int(c['current_hp'] / c['max_hp'] * 10) + "░" * (10 - int(c['current_hp'] / c['max_hp'] * 10))
            status = " ".join([f"[{e['effect']}]" for e in c['status_effects']])
            dead = "💀" if c['current_hp'] <= 0 else ""
            marker = "🎮" if c['is_player'] else "👹"
            lines.append(f"{dead}{marker} {c['name']}: AC {c.get('armor_class', 10)} | {hp_bar} {c['current_hp']}/{c['max_hp']} {status}")
        
        return "\n".join(lines)
    
    async def _end_combat(self, context: Dict, args: Dict) -> str:
        """End combat encounter"""
        channel_id = context.get('channel_id')
        outcome = args.get('outcome', 'victory')
        xp_reward = args.get('xp_reward', 0)
        
        combat = await self.db.get_active_combat(channel_id=channel_id)
        if not combat:
            return "No active combat to end."
        
        await self.db.end_combat(combat['id'])
        
        # Award XP to surviving players
        if xp_reward > 0:
            combatants = await self.db.get_combatants(combat['id'])
            for c in combatants:
                if c['is_player'] and c['current_hp'] > 0 and c['participant_type'] == 'character':
                    await self.db.add_experience(c['participant_id'], xp_reward)
        
        return f"⚔️ Combat ended! Outcome: {outcome}. Each surviving player earned {xp_reward} XP."
    
    # =========================================================================
    # DICE TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _roll_dice(self, context: Dict, args: Dict) -> str:
        """Roll dice"""
        dice = args.get('dice')
        purpose = args.get('purpose', 'roll')
        advantage = args.get('advantage', False)
        disadvantage = args.get('disadvantage', False)
        
        result = self.dice.roll(dice, advantage, disadvantage)
        if 'error' in result:
            return result['error']
        
        # Log the roll
        user_id = context.get('user_id')
        guild_id = context.get('guild_id')
        char = await self._get_context_character(context)
        char_name = char['name'] if char else 'Unknown'
        
        await self.db.log_dice_roll(
            user_id, guild_id, 'general', dice, result['rolls'],
            result['modifier'], result['total'],
            char['id'] if char else None, purpose
        )
        
        # Track in mechanics tracker
        tracker = get_tracker()
        tracker.add_dice_roll(
            character_name=char_name,
            dice=dice,
            rolls=result['rolls'],
            modifier=result['modifier'],
            total=result['total'],
            critical=result.get('critical', False),
            fumble=result.get('fumble', False)
        )
        
        # Format result
        rolls_str = ", ".join(map(str, result['rolls']))
        kept_str = ", ".join(map(str, result['kept'])) if result['rolls'] != result['kept'] else ""
        mod_str = f" + {result['modifier']}" if result['modifier'] > 0 else f" - {abs(result['modifier'])}" if result['modifier'] < 0 else ""
        
        special = ""
        if result.get('critical'):
            special = " 🎯 **NATURAL 20!**"
        elif result.get('fumble'):
            special = " 💥 **NATURAL 1!**"
        
        msg = f"🎲 **{purpose}**: [{rolls_str}]"
        if kept_str:
            msg += f" (kept: {kept_str})"
        msg += f"{mod_str} = **{result['total']}**{special}"
        
        return msg
    
    async def _roll_attack(self, context: Dict, args: Dict) -> str:
        """Roll an attack"""
        attacker_id = args.get('attacker_id')
        target_id = args.get('target_id')
        attack_bonus = args.get('attack_bonus', 0)
        damage_dice = args.get('damage_dice')
        damage_type = args.get('damage_type', 'physical')
        
        channel_id = context.get('channel_id')
        combat = await self.db.get_active_combat(channel_id=channel_id)
        if not combat:
            return "Error: No active combat for attack roll."
        
        combatants = await self.db.get_combatants(combat['id'])
        attacker = next((c for c in combatants if c['id'] == attacker_id), None)
        target = next((c for c in combatants if c['id'] == target_id), None)
        
        if not attacker or not target:
            return "Error: Invalid attacker or target."
        
        # Roll to hit
        attack_roll = self.dice.roll(f"1d20+{attack_bonus}")
        target_ac = target.get('armor_class') or target.get('combat_stats', {}).get('ac') or 10
        
        hit = attack_roll['total'] >= target_ac or attack_roll['critical']
        
        result_lines = [
            f"⚔️ **{attacker['name']}** attacks **{target['name']}**!",
            f"Attack: {attack_roll['rolls'][0]} + {attack_bonus} = {attack_roll['total']} vs AC {target_ac}"
        ]
        
        if attack_roll['critical']:
            result_lines.append("🎯 **CRITICAL HIT!**")
            damage_roll = self.dice.roll(damage_dice)
            total_damage = damage_roll['total'] * 2  # Double damage on crit
            await self.db.update_combatant_hp(target_id, -total_damage)
            result_lines.append(f"Damage: {damage_roll['total']} x2 = **{total_damage}** {damage_type} damage!")
        elif attack_roll['fumble']:
            result_lines.append("💥 **CRITICAL MISS!** The attack goes wildly astray!")
        elif hit:
            result_lines.append("✅ **HIT!**")
            damage_roll = self.dice.roll(damage_dice)
            await self.db.update_combatant_hp(target_id, -damage_roll['total'])
            result_lines.append(f"Damage: **{damage_roll['total']}** {damage_type} damage!")
        else:
            result_lines.append("❌ **MISS!**")
        
        return "\n".join(result_lines)
    
    async def _roll_save(self, args: Dict) -> str:
        """Roll a saving throw"""
        char_id = args.get('character_id')
        save_type = args.get('save_type')
        dc = args.get('dc')
        reason = args.get('reason', 'effect')
        
        char = await self.db.get_character(char_id)
        if not char:
            return "Error: Character not found"
        
        stat_value = char.get(save_type, 10)
        modifier = (stat_value - 10) // 2
        
        roll = self.dice.roll(f"1d20+{modifier}")
        success = roll['total'] >= dc
        
        # Track in mechanics tracker
        tracker = get_tracker()
        tracker.add_saving_throw(
            character_name=char['name'],
            save_type=save_type,
            dc=dc,
            roll=roll['rolls'][0],
            modifier=modifier,
            total=roll['total'],
            success=success,
            reason=reason
        )
        
        result = "✅ **SUCCESS!**" if success else "❌ **FAILED!**"
        special = " (NAT 20!)" if roll['critical'] else " (NAT 1!)" if roll['fumble'] else ""
        
        return f"🎲 **{char['name']}** {save_type.upper()} Save vs DC {dc} ({reason}): {roll['rolls'][0]} + {modifier} = **{roll['total']}**{special} {result}"
    
    async def _roll_skill_check(self, args: Dict) -> str:
        """Roll a skill check"""
        char_id = args.get('character_id')
        skill = args.get('skill')
        dc = args.get('dc')
        stat = args.get('stat')
        
        char = await self.db.get_character(char_id)
        if not char:
            return "Error: Character not found"
        
        stat_value = char.get(stat, 10)
        modifier = (stat_value - 10) // 2
        
        roll = self.dice.roll(f"1d20+{modifier}")
        success = roll['total'] >= dc
        
        # Track in mechanics tracker
        tracker = get_tracker()
        tracker.add_skill_check(
            character_name=char['name'],
            skill=skill,
            stat=stat,
            dc=dc,
            roll=roll['rolls'][0],
            modifier=modifier,
            total=roll['total'],
            success=success,
            critical=roll.get('critical', False),
            fumble=roll.get('fumble', False)
        )
        
        result = "✅ **SUCCESS!**" if success else "❌ **FAILED!**"
        special = " (NAT 20!)" if roll['critical'] else " (NAT 1!)" if roll['fumble'] else ""
        
        return f"🎲 **{char['name']}** {skill.title()} Check ({stat.upper()}) vs DC {dc}: {roll['rolls'][0]} + {modifier} = **{roll['total']}**{special} {result}"
    
    # =========================================================================
    # QUEST TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _create_quest(self, context: Dict, args: Dict) -> str:
        """Create a new quest"""
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        session = await self._get_session_for_context(context)
        objectives = []
        for objective in args.get('objectives', []):
            if isinstance(objective, dict):
                description = objective.get('description')
                if not description:
                    continue
                objectives.append({
                    'description': description,
                    'optional': bool(objective.get('optional', False)),
                    'completed': bool(objective.get('completed', False)),
                })
            elif isinstance(objective, str) and objective.strip():
                objectives.append({
                    'description': objective.strip(),
                    'optional': False,
                    'completed': False,
                })

        if not objectives:
            return "Error: At least one valid quest objective is required"
        
        quest_id = await self.db.create_quest(
            guild_id=guild_id,
            title=args.get('title'),
            description=args.get('description'),
            objectives=objectives,
            rewards=args.get('rewards', {}),
            created_by=user_id,
            session_id=session['id'] if session else None,
            difficulty=args.get('difficulty', 'medium'),
            dm_plan=args.get('dm_plan')
        )
        
        return f"📜 Quest created: **{args['title']}** (ID: {quest_id})"
    
    async def _update_quest(self, args: Dict) -> str:
        """Update a quest"""
        quest_id = args.get('quest_id')
        updates = {k: v for k, v in args.items() if k != 'quest_id' and v is not None}
        
        if not updates:
            return "No updates provided"
        
        await self.db.update_quest(quest_id, **updates)
        return f"Quest {quest_id} updated: {', '.join(updates.keys())}"
    
    async def _complete_objective(self, args: Dict) -> str:
        """Complete a quest objective"""
        quest_id = args.get('quest_id')
        char_id = args.get('character_id')
        obj_index = args.get('objective_index')
        
        result = await self.db.complete_objective(quest_id, char_id, obj_index)
        if 'error' in result:
            return f"Error: {result['error']}"
        
        msg = f"✅ Objective {obj_index + 1} completed!"
        if result['quest_complete']:
            msg += " 🎉 **All objectives complete! Quest ready to turn in!**"
        
        return msg
    
    async def _give_quest_rewards(self, args: Dict) -> str:
        """Give quest rewards"""
        quest_id = args.get('quest_id')
        char_id = args.get('character_id')
        
        result = await self.db.complete_quest(quest_id, char_id)
        if 'error' in result:
            return f"Error: {result['error']}"
        
        rewards = result['rewards']
        lines = ["🎉 **Quest Complete!** Rewards:"]
        if 'gold' in rewards:
            lines.append(f"  💰 {rewards['gold']} gold")
        if 'xp' in rewards:
            lines.append(f"  ⭐ {rewards['xp']} XP")
        if rewards.get('level_up'):
            lines.append("  🎊 **LEVEL UP!**")
        if 'items' in rewards:
            for item in rewards['items']:
                lines.append(f"  📦 {item['name']}")
        
        return "\n".join(lines)
    
    async def _get_quests(self, context: Dict, args: Dict) -> str:
        """Get quests"""
        guild_id = context.get('guild_id')
        char_id = args.get('character_id')
        status = args.get('status', 'available')
        
        if char_id:
            quests = await self.db.get_character_quests(char_id, status if status != 'all' else None)
        else:
            quests = await self.db.get_available_quests(guild_id)
        
        if not quests:
            return "No quests found."
        
        lines = [f"**Quests ({status}):**"]
        for q in quests:
            obj_count = len(q.get('objectives', []))
            completed = len(q.get('objectives_completed', []))
            lines.append(f"[{q['id']}] **{q['title']}** ({q['difficulty']}) - {completed}/{obj_count} objectives")
        
        return "\n".join(lines)
    
    # =========================================================================
    # NPC TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _get_npc_info(self, args: Dict) -> str:
        """Get NPC information"""
        npc_id = args.get('npc_id')
        char_id = args.get('character_id')
        
        npc = await self.db.get_npc(npc_id)
        if not npc:
            return "Error: NPC not found"
        
        relationship = {"reputation": 0, "relationship_notes": None}
        if char_id:
            relationship = await self.db.get_npc_relationship(npc_id, char_id)
        
        rep = relationship.get('reputation', 0)
        disposition = "hostile" if rep < -30 else "unfriendly" if rep < -10 else \
                      "neutral" if rep < 10 else "friendly" if rep < 30 else "devoted"
        
        return f"""**{npc['name']}** ({npc['npc_type']})
{npc['description']}
Personality: {npc['personality']}
Location: {npc['location'] or 'Unknown'}
Merchant: {'Yes' if npc['is_merchant'] else 'No'}
Reputation: {rep} ({disposition})
Notes: {relationship.get('relationship_notes') or 'No prior interactions'}"""
    
    async def _create_npc(self, context: Dict, args: Dict) -> str:
        """Create a new NPC"""
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        session = await self._get_session_for_context(context)
        
        npc_id = await self.db.create_npc(
            guild_id=guild_id,
            name=args.get('name'),
            description=args.get('description'),
            personality=args.get('personality'),
            created_by=user_id,
            npc_type=args.get('npc_type', 'neutral'),
            location=args.get('location'),
            is_merchant=args.get('is_merchant', False),
            merchant_inventory=args.get('merchant_inventory'),
            session_id=session['id'] if session else None
        )
        
        return f"👤 Created NPC: **{args['name']}** (ID: {npc_id})"
    
    async def _update_npc_relationship(self, args: Dict) -> str:
        """Update NPC-character relationship"""
        npc_id = args.get('npc_id')
        char_id = args.get('character_id')
        rep_change = args.get('reputation_change', 0)
        notes = args.get('notes')
        
        new_rep = await self.db.update_npc_relationship(npc_id, char_id, rep_change, notes)
        
        npc = await self.db.get_npc(npc_id)
        change_str = f"+{rep_change}" if rep_change > 0 else str(rep_change)
        
        return f"Relationship with {npc['name']} changed by {change_str}. New reputation: {new_rep}"
    
    async def _get_npcs(self, context: Dict, args: Dict) -> str:
        """Get NPCs"""
        guild_id = context.get('guild_id')
        location = args.get('location')
        
        if location:
            npcs = await self.db.get_npcs_by_location(guild_id, location)
        else:
            npcs = await self.db.get_guild_npcs(guild_id)
        
        if not npcs:
            return "No NPCs found."
        
        lines = ["**NPCs:**"]
        for npc in npcs:
            merchant = "🛒" if npc['is_merchant'] else ""
            lines.append(f"[{npc['id']}] {merchant}**{npc['name']}** ({npc['npc_type']}) - {npc['location'] or 'Unknown location'}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # SESSION/STORY TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _get_party_info(self, context: Dict) -> str:
        """Get party information"""
        session = await self._get_session_for_context(context)
        
        if not session:
            return "No active session."
        
        participants = await self.db.get_session_participants(session['id'])
        
        if not participants:
            return "No players in session."
        
        lines = [f"**Party ({session['name']}) - Session ID: {session['id']}:**"]
        for p in participants:
            if p.get('character_name'):
                char_id = p.get('character_id', '?')
                lines.append(f"- {p['character_name']} [ID: {char_id}] (Lvl {p['level']} {p['character_class']})")
            else:
                lines.append(f"- <@{p['user_id']}> (no character)")
        
        return "\n".join(lines)
    
    async def _add_story_entry(self, context: Dict, args: Dict) -> str:
        """Add story log entry"""
        session = await self._get_session_for_context(context)
        
        if not session:
            return "No active session to log story."
        
        entry_type = args.get('entry_type', 'narration')
        content = args.get('content')
        
        await self.db.add_story_entry(session['id'], entry_type, content)
        return f"📖 Story logged: [{entry_type}]"
    
    async def _get_story_log(self, context: Dict, args: Dict) -> str:
        """Get story log"""
        session = await self._get_session_for_context(context)
        
        if not session:
            return "No active session."
        
        limit = args.get('limit', 10)
        entries = await self.db.get_story_log(session['id'], limit)
        
        if not entries:
            return "No story entries yet."
        
        lines = ["**Recent Story:**"]
        for e in entries[-5:]:  # Show last 5
            type_emoji = {"narration": "📖", "combat": "⚔️", "dialogue": "💬", 
                         "discovery": "🔍", "milestone": "🏆"}.get(e['entry_type'], "📝")
            preview = e['content'][:100] + "..." if len(e['content']) > 100 else e['content']
            lines.append(f"{type_emoji} {preview}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # MEMORY TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _save_memory(self, context: Dict, args: Dict) -> str:
        """Save a memory"""
        user_id = context.get('user_id')
        guild_id = context.get('guild_id')
        key = args.get('key')
        value = args.get('value')
        mem_context = args.get('context')
        
        await self.db.save_memory(user_id, guild_id, key, value, mem_context)
        return f"💭 Remembered: {key}"
    
    async def _get_player_memories(self, context: Dict, args: Dict) -> str:
        """Get player memories"""
        user_id = args.get('user_id') or context.get('user_id')
        guild_id = context.get('guild_id')
        
        memories = await self.db.get_all_memories(user_id, guild_id)
        
        if not memories:
            return "No memories stored for this player."
        
        lines = ["**Player Memories:**"]
        for key, data in memories.items():
            value = data.get('value') if isinstance(data, dict) else data
            lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # SPELL & ABILITY TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _get_character_spells(self, args: Dict) -> str:
        """Get character's known spells"""
        char_id = args.get('character_id')
        prepared_only = args.get('prepared_only', False)
        
        if not char_id:
            return "Error: character_id required"
        
        spells = await self.db.get_character_spells(char_id, prepared_only)
        slots = await self.db.get_spell_slots(char_id)
        
        if not spells:
            return "This character doesn't know any spells."
        
        lines = ["**Known Spells:**"]
        
        # Group by level
        cantrips = [s for s in spells if s['is_cantrip']]
        leveled = {}
        for s in spells:
            if not s['is_cantrip']:
                lvl = s['spell_level']
                if lvl not in leveled:
                    leveled[lvl] = []
                leveled[lvl].append(s)
        
        if cantrips:
            lines.append(f"✨ Cantrips: {', '.join([s['spell_name'] for s in cantrips])}")
        
        for lvl in sorted(leveled.keys()):
            slot_info = f" ({slots.get(lvl, {}).get('remaining', 0)} slots)" if slots else ""
            lines.append(f"📖 Level {lvl}{slot_info}: {', '.join([s['spell_name'] for s in leveled[lvl]])}")
        
        if slots:
            lines.append("\n**Spell Slots:**")
            for lvl, data in sorted(slots.items()):
                lines.append(f"  Level {lvl}: {data['remaining']}/{data['total']}")
        
        return "\n".join(lines)
    
    async def _cast_spell(self, context: Dict, args: Dict) -> str:
        """Cast a spell for a character"""
        char_id = args.get('character_id')
        spell_id = args.get('spell_id')
        slot_level = args.get('slot_level')
        target = args.get('target', 'target')
        
        if not char_id or not spell_id:
            return "Error: character_id and spell_id required"
        
        # Load spell data
        try:
            spells_data = await self._load_theme_content(context, 'spells.json')
        except FileNotFoundError:
            return "Error: Spell data not found"
        
        spell = spells_data.get('spells', {}).get(spell_id)
        if not spell:
            return f"Error: Unknown spell '{spell_id}'"
        
        # Check if character knows the spell
        known_spells = await self.db.get_character_spells(char_id)
        if not any(s['spell_id'] == spell_id for s in known_spells):
            return f"Character doesn't know {spell['name']}!"
        
        char = await self.db.get_character(char_id)
        char_name = char['name'] if char else "Character"
        
        # Handle cantrips (no slot needed)
        is_cantrip = spell['level'] == 0
        
        if not is_cantrip:
            # Use spell slot
            if not slot_level:
                slot_level = spell['level']
            
            if slot_level < spell['level']:
                return f"Cannot cast {spell['name']} with a level {slot_level} slot (requires level {spell['level']})"
            
            success = await self.db.use_spell_slot(char_id, slot_level)
            if not success:
                return f"No level {slot_level} spell slots remaining!"
        
        # Calculate effects
        result_parts = [f"✨ **{char_name}** casts **{spell['name']}**!"]
        
        if target:
            result_parts.append(f"*Target: {target}*")

        target_combatant = None
        target_character = None
        if target and context.get('channel_id') and context.get('guild_id'):
            combat = await self.db.get_active_combat(context.get('guild_id'), context.get('channel_id'))
            if combat:
                for combatant in await self.db.get_combatants(combat['id']):
                    if target.lower() in combatant['name'].lower() and combatant['current_hp'] > 0:
                        target_combatant = combatant
                        break

        if target and target.lower() == 'self':
            target_character = char
        elif target and not target_combatant:
            session = await self._get_session_for_context(context)
            if session:
                for participant in await self.db.get_session_participants(session['id']):
                    if participant.get('character_id') and target.lower() in (participant.get('character_name') or '').lower():
                        target_character = await self.db.get_character(participant['character_id'])
                        break
        
        # Handle damage
        if spell.get('damage'):
            damage_dice = spell['damage']
            
            # Apply cantrip scaling based on level
            if is_cantrip and spell.get('scaling') and char:
                char_level = char.get('level', 1)
                for level_threshold, scaled_damage in sorted(spell['scaling'].items(), key=lambda x: int(x[0]), reverse=True):
                    if char_level >= int(level_threshold):
                        damage_dice = scaled_damage
                        break
            
            # Apply upcast bonus
            upcast_levels = (slot_level - spell['level']) if slot_level else 0
            if upcast_levels > 0 and spell.get('upcast') and '+1d' in spell.get('upcast', ''):
                import re
                match = re.search(r'\+1d(\d+)', spell['upcast'])
                if match:
                    base_roll = self.dice.roll(damage_dice)
                    bonus_roll = self.dice.roll(f"{upcast_levels}d{match.group(1)}")
                    if base_roll.get('error') or bonus_roll.get('error'):
                        return f"Error: Could not roll damage for {spell['name']}"
                    total_damage = base_roll['total'] + bonus_roll['total']
                    all_rolls = base_roll['rolls'] + bonus_roll['rolls']
                    roll_result = {'total': total_damage, 'rolls': all_rolls}
                else:
                    roll_result = self.dice.roll(damage_dice)
            else:
                roll_result = self.dice.roll(damage_dice)

            if roll_result.get('error'):
                return f"Error: {roll_result['error']}"
            damage_type = spell.get('damage_type', 'magical')
            result_parts.append(f"💥 **{roll_result['total']}** {damage_type} damage!")
            result_parts.append(f"🎲 Rolled {damage_dice}: {roll_result['rolls']}")

            if target_combatant:
                hp_result = await self.db.update_combatant_hp(target_combatant['id'], -roll_result['total'])
                if not hp_result.get('error'):
                    if hp_result['is_dead']:
                        result_parts.append(f"💀 **{hp_result['name']}** is defeated!")
                    else:
                        result_parts.append(f"❤️ {hp_result['name']}: {hp_result['new_hp']}/{hp_result['max_hp']} HP")
            
            if spell.get('save'):
                result_parts.append(f"🛡️ {spell['save'].upper()} save for half damage")
        
        # Handle healing
        elif spell.get('healing'):
            healing_dice = spell['healing'].replace(' + spellcasting modifier', '')
            
            # Add spellcasting modifier
            if char:
                char_class = char.get('char_class', '').lower()
                if char_class in ['cleric', 'paladin', 'ranger', 'druid']:
                    mod = (char.get('wisdom', 10) - 10) // 2
                elif char_class in ['bard', 'warlock']:
                    mod = (char.get('charisma', 10) - 10) // 2
                else:
                    mod = (char.get('intelligence', 10) - 10) // 2
                
                if mod > 0:
                    healing_dice = f"{healing_dice}+{mod}"
            
            # Apply upcast
            upcast_levels = (slot_level - spell['level']) if slot_level else 0
            if upcast_levels > 0 and spell.get('upcast') and '+1d' in spell.get('upcast', ''):
                import re
                match = re.search(r'\+1d(\d+)', spell['upcast'])
                if match:
                    base_roll = self.dice.roll(healing_dice)
                    bonus_roll = self.dice.roll(f"{upcast_levels}d{match.group(1)}")
                    if base_roll.get('error') or bonus_roll.get('error'):
                        return f"Error: Could not roll healing for {spell['name']}"
                    total_healing = base_roll['total'] + bonus_roll['total']
                    all_rolls = base_roll['rolls'] + bonus_roll['rolls']
                    roll_result = {'total': total_healing, 'rolls': all_rolls}
                else:
                    roll_result = self.dice.roll(healing_dice)
            else:
                roll_result = self.dice.roll(healing_dice)

            if roll_result.get('error'):
                return f"Error: {roll_result['error']}"
            result_parts.append(f"💚 **{roll_result['total']}** HP healed!")
            result_parts.append(f"🎲 Rolled {healing_dice}: {roll_result['rolls']}")

            heal_target = target_character or char
            hp_result = await self.db.update_character_hp(heal_target['id'], roll_result['total'])
            if not hp_result.get('error'):
                result_parts.append(f"❤️ {hp_result['name']}: {hp_result['new_hp']}/{hp_result['max_hp']} HP")
        
        # Handle effects
        elif spell.get('effect'):
            result_parts.append(f"✨ Effect: {spell['effect']}")
        
        # Show spell description snippet
        if spell.get('description'):
            result_parts.append(f"*{spell['description'][:150]}...*" if len(spell.get('description', '')) > 150 else f"*{spell['description']}*")
        
        return "\n".join(result_parts)

    async def _generate_npc_dialogue(self, context: Dict, args: Dict) -> str:
        """Generate NPC dialogue through the configured LLM when available."""
        llm = context.get('llm')
        npc_id = args.get('npc_id')
        character_id = args.get('character_id')
        player_message = args.get('message') or args.get('player_message')

        if not llm:
            return "NPC dialogue generation is unavailable because the LLM client is not configured."
        if not npc_id or not character_id or not player_message:
            return "Error: npc_id, character_id, and message are required"

        npc = await self.db.get_npc(npc_id)
        character = await self.db.get_character(character_id)
        if not npc or not character:
            return "Error: NPC or character not found"

        relationship = await self.db.get_npc_relationship(npc_id, character_id)
        dialogue = await llm.generate_npc_dialogue(
            npc=npc,
            character=character,
            relationship=relationship or {'reputation': 0},
            player_message=player_message,
            context=args.get('context'),
        )
        return dialogue or "..."
    
    async def _use_ability(self, args: Dict) -> str:
        """Use a class ability"""
        char_id = args.get('character_id')
        ability_id = args.get('ability_id')
        target = args.get('target')
        
        if not char_id or not ability_id:
            return "Error: character_id and ability_id required"
        
        # Check if character has the ability
        abilities = await self.db.get_character_abilities(char_id)
        ability = next((a for a in abilities if a['ability_id'] == ability_id), None)
        
        if not ability:
            return f"Character doesn't have the ability '{ability_id}'!"
        
        # Try to use it (checks uses remaining)
        success = await self.db.use_ability(char_id, ability_id)
        
        if not success:
            return f"No uses remaining for {ability['ability_name']}! Rest to recover."
        
        char = await self.db.get_character(char_id)
        char_name = char['name'] if char else "Character"
        
        # Load ability data for effects
        try:
            character = await self.db.get_character(char_id)
            session = await self._get_session_for_context({
                'session_id': character.get('session_id') if character else None,
                'guild_id': character.get('guild_id') if character else None,
                'user_id': character.get('user_id') if character else None,
            })
            classes_data = load_session_content_file(session, 'classes.json')
        except FileNotFoundError:
            classes_data = {}
        
        ability_info = classes_data.get('abilities', {}).get(ability_id, {})
        description = ability_info.get('description', ability['ability_name'])
        
        result_parts = [f"⚡ **{char_name}** uses **{ability['ability_name']}**!"]
        
        if target:
            result_parts.append(f"*Target: {target}*")
        
        result_parts.append(f"📜 {description}")
        
        # Handle specific abilities
        if ability_id == 'second_wind' and char:
            # Heal 1d10 + level
            healing = self.dice.roll(f"1d10+{char.get('level', 1)}")
            new_hp = min(char['hp'] + healing['total'], char['max_hp'])
            await self.db.update_character(char_id, hp=new_hp)
            result_parts.append(f"💚 Recovered **{healing['total']}** HP! (Now at {new_hp}/{char['max_hp']})")
        
        elif ability_id == 'action_surge':
            result_parts.append("⚔️ You can take an additional action this turn!")
        
        elif ability_id == 'sneak_attack' and char:
            level = char.get('level', 1)
            sneak_dice = f"{(level + 1) // 2}d6"
            damage = self.dice.roll(sneak_dice)
            result_parts.append(f"🗡️ Sneak Attack deals **{damage['total']}** extra damage!")
            result_parts.append(f"🎲 Rolled {sneak_dice}: {damage['rolls']}")
        
        elif ability_id == 'bardic_inspiration':
            result_parts.append("🎵 Target gains a d6 inspiration die to add to a roll!")
        
        elif ability_id == 'lay_on_hands' and char:
            pool = char.get('level', 1) * 5
            result_parts.append(f"✋ Healing pool: {pool} HP available")
        
        # Show uses remaining
        if ability.get('max_uses'):
            uses_after = ability.get('uses_remaining', 0) - 1
            result_parts.append(f"*({uses_after}/{ability['max_uses']} uses remaining)*")
        
        return "\n".join(result_parts)
    
    async def _get_character_abilities(self, args: Dict) -> str:
        """Get character's class abilities"""
        char_id = args.get('character_id')
        
        if not char_id:
            return "Error: character_id required"
        
        abilities = await self.db.get_character_abilities(char_id)
        
        if not abilities:
            return "Character has no special abilities."
        
        lines = ["**Class Abilities:**"]
        
        for a in abilities:
            uses_text = ""
            if a.get('max_uses'):
                uses_text = f" ({a.get('uses_remaining', 0)}/{a['max_uses']} uses)"
            
            lines.append(f"⚡ **{a['ability_name']}**{uses_text}")
        
        return "\n".join(lines)
    
    async def _rest_character(self, args: Dict) -> str:
        """Have a character take a rest"""
        char_id = args.get('character_id')
        rest_type = args.get('rest_type', 'long')
        
        if not char_id:
            return "Error: character_id required"
        
        char = await self.db.get_character(char_id)
        if not char:
            return "Character not found."
        
        char_name = char['name']
        result_parts = []
        
        if rest_type == 'long':
            # Long rest: full HP, all spell slots, all abilities
            await self.db.update_character(char_id, hp=char['max_hp'])
            await self.db.restore_spell_slots(char_id)
            await self.db.restore_abilities(char_id, 'long_rest')
            
            result_parts.append(f"🌙 **{char_name}** takes a long rest...")
            result_parts.append(f"💚 HP fully restored: {char['max_hp']}/{char['max_hp']}")
            result_parts.append("💫 All spell slots recovered")
            result_parts.append("⚡ All abilities recharged")
            
        else:  # Short rest
            # Short rest: spend hit dice (simplified), some abilities
            await self.db.restore_abilities(char_id, 'short_rest')
            
            # Heal some HP (1d8 + con mod per hit die spent, simplified to just 1)
            con_mod = (char.get('constitution', 10) - 10) // 2
            healing = self.dice.roll(f"1d8+{con_mod}")['total']
            new_hp = min(char['hp'] + healing, char['max_hp'])
            await self.db.update_character(char_id, hp=new_hp)
            
            result_parts.append(f"☕ **{char_name}** takes a short rest...")
            result_parts.append(f"💚 Recovered {healing} HP (now {new_hp}/{char['max_hp']})")
            result_parts.append("⚡ Short rest abilities recharged")
        
        return "\n".join(result_parts)
    
    # =========================================================================
    # LOCATION TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _create_location(self, context: Dict, args: Dict) -> str:
        """Create a new location"""
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        session = await self._get_session_for_context(context)
        
        location_id = await self.db.create_location(
            guild_id=guild_id,
            name=args.get('name'),
            created_by=user_id,
            session_id=session['id'] if session else None,
            description=args.get('description'),
            location_type=args.get('location_type', 'generic'),
            points_of_interest=args.get('points_of_interest', []),
            current_weather=args.get('current_weather'),
            danger_level=args.get('danger_level', 0),
            hidden_secrets=args.get('hidden_secrets')
        )
        
        return f"📍 Location created: **{args['name']}** (ID: {location_id})"
    
    async def _get_location(self, args: Dict) -> str:
        """Get location details"""
        location_id = args.get('location_id')
        
        loc = await self.db.get_location(location_id)
        if not loc:
            return "Error: Location not found"
        
        pois = ", ".join(loc.get('points_of_interest', [])) or "None"
        
        return f"""📍 **{loc['name']}** ({loc['location_type']})
{loc['description'] or 'No description'}
Weather: {loc.get('current_weather') or 'Normal'}
Danger Level: {loc.get('danger_level', 0)}/10
Points of Interest: {pois}"""
    
    async def _get_nearby_locations(self, args: Dict) -> str:
        """Get connected locations"""
        location_id = args.get('location_id')
        
        locations = await self.db.get_nearby_locations(location_id)
        if not locations:
            return "No nearby locations found."
        
        lines = ["**Nearby Locations:**"]
        for loc in locations:
            danger = "⚠️" if loc.get('danger_level', 0) >= 5 else ""
            lines.append(f"{danger}[{loc['id']}] **{loc['name']}** ({loc['location_type']})")
        
        return "\n".join(lines)
    
    async def _update_location(self, args: Dict) -> str:
        """Update location"""
        location_id = args.get('location_id')
        updates = {k: v for k, v in args.items() if k != 'location_id' and v is not None}
        
        if not updates:
            return "No updates provided"
        
        await self.db.update_location(location_id, **updates)
        return f"Location {location_id} updated: {', '.join(updates.keys())}"
    
    async def _move_party_to_location(self, context: Dict, args: Dict) -> str:
        """Move party to new location"""
        location_id = args.get('location_id')
        travel_desc = args.get('travel_description', '')
        
        session = await self._get_session_for_context(context)
        if not session:
            return "Error: No active session"
        
        loc = await self.db.get_location(location_id)
        if not loc:
            return "Error: Location not found"

        current_state = await self.db.get_game_state(session['id']) or {}
        current_location_id = current_state.get('current_location_id')
        if current_location_id and current_location_id != location_id:
            nearby_locations = await self.db.get_nearby_locations(current_location_id)
            if not any(nearby.get('id') == location_id for nearby in nearby_locations):
                current_location = await self.db.get_location(current_location_id)
                current_name = current_location.get('name', 'Unknown') if current_location else 'Unknown'
                return f"Error: **{loc['name']}** is not directly connected to **{current_name}**"

        participants = await self.db.get_session_participants(session['id'])
        moved_characters = []
        for participant in participants:
            character_id = participant.get('character_id')
            if not character_id:
                continue
            result = await self.db.move_character_to_location(character_id, location_id)
            if not result.get('error'):
                moved_characters.append(character_id)
        
        # Update game state with new location
        await self.db.save_game_state(
            session['id'],
            current_location=loc['name'],
            current_location_id=location_id,
        )
        
        # Log the travel
        await self.db.add_story_log_entry(
            session['id'],
            'travel',
            f"Party traveled to {loc['name']}. {travel_desc}".strip(),
            moved_characters,
        )

        nearby_locations = await self.db.get_nearby_locations(location_id)
        exits = ""
        if nearby_locations:
            exit_lines = [f"• {nearby.get('name', 'Unknown')} ({nearby.get('direction', 'path')})" for nearby in nearby_locations[:5]]
            exits = "\n\n🚪 Exits:\n" + "\n".join(exit_lines)

        return f"🚶 The party travels to **{loc['name']}**.\n{travel_desc}\n\n{loc['description'] or ''}{exits}"
    
    # =========================================================================
    # STORY ITEM TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _create_story_item(self, context: Dict, args: Dict) -> str:
        """Create a story item"""
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        session = await self._get_session_for_context(context)
        
        item_id = await self.db.create_story_item(
            guild_id=guild_id,
            name=args.get('name'),
            created_by=user_id,
            session_id=session['id'] if session else None,
            description=args.get('description'),
            item_type=args.get('item_type', 'misc'),
            lore=args.get('lore'),
            discovery_conditions=args.get('discovery_conditions'),
            dm_notes=args.get('dm_notes')
        )
        
        return f"📜 Story item created: **{args['name']}** (ID: {item_id})"
    
    async def _reveal_story_item(self, args: Dict) -> str:
        """Reveal a story item"""
        item_id = args.get('item_id')
        
        item = await self.db.get_story_item(item_id)
        if not item:
            return "Error: Story item not found"
        
        await self.db.reveal_story_item(item_id)
        
        lore_hint = f"\n*{item.get('lore', '')[:100]}...*" if item.get('lore') else ""
        return f"✨ **{item['name']}** has been discovered!\n{item['description']}{lore_hint}"
    
    async def _transfer_story_item(self, args: Dict) -> str:
        """Transfer story item"""
        item_id = args.get('item_id')
        holder_id = args.get('new_holder_id')
        holder_type = args.get('holder_type', 'none')
        
        item = await self.db.get_story_item(item_id)
        if not item:
            return "Error: Story item not found"
        
        await self.db.transfer_story_item(item_id, holder_id, holder_type)
        
        if holder_type == 'none':
            return f"**{item['name']}** has been dropped/placed."
        else:
            return f"**{item['name']}** transferred to {holder_type} #{holder_id}."
    
    async def _get_story_items(self, context: Dict, args: Dict) -> str:
        """Get story items"""
        session = await self._get_session_for_context(context)
        
        items = await self.db.get_story_items(
            session_id=session['id'] if session else None,
            guild_id=context.get('guild_id') if not session else None,
        )

        holder_id = args.get('holder_id')
        is_discovered = args.get('is_discovered')
        if holder_id is not None:
            items = [item for item in items if item.get('current_holder_id') == holder_id]
        if is_discovered is not None:
            discovered_flag = bool(is_discovered)
            items = [item for item in items if bool(item.get('is_discovered')) == discovered_flag]
        
        if not items:
            return "No story items found."
        
        lines = ["**Story Items:**"]
        for item in items:
            status = "✨" if item['is_discovered'] else "🔒"
            holder = f" - held by character #{item['current_holder_id']}" if item.get('current_holder_id') else ""
            lines.append(f"{status} [{item['id']}] **{item['name']}** ({item['item_type']}){holder}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # STORY EVENT TOOL IMPLEMENTATIONS  
    # =========================================================================
    
    async def _create_story_event(self, context: Dict, args: Dict) -> str:
        """Create a story event"""
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        session = await self._get_session_for_context(context)
        
        event_id = await self.db.create_story_event(
            guild_id=guild_id,
            name=args.get('name'),
            created_by=user_id,
            session_id=session['id'] if session else None,
            description=args.get('description'),
            event_type=args.get('event_type', 'side_event'),
            trigger_conditions=args.get('trigger_conditions'),
            location_id=args.get('location_id'),
            dm_notes=args.get('dm_notes')
        )
        
        return f"📅 Story event created: **{args['name']}** (ID: {event_id})"
    
    async def _trigger_event(self, args: Dict) -> str:
        """Activate a pending event"""
        event_id = args.get('event_id')
        
        event = await self.db.get_story_event(event_id)
        if not event:
            return "Error: Event not found"
        
        await self.db.trigger_event(event_id)
        
        return f"⚡ **{event['name']}** has begun!\n{event['description']}"
    
    async def _resolve_event(self, args: Dict) -> str:
        """Complete a story event"""
        event_id = args.get('event_id')
        outcome = args.get('outcome', 'success')
        notes = args.get('resolution_notes')
        
        event = await self.db.get_story_event(event_id)
        if not event:
            return "Error: Event not found"
        
        await self.db.resolve_event(event_id, outcome, notes)
        
        emoji = "🎉" if outcome == 'success' else "💔" if outcome == 'failure' else "⚖️"
        return f"{emoji} **{event['name']}** resolved: {outcome.upper()}\n{notes or ''}"
    
    async def _get_active_events(self, context: Dict) -> str:
        """Get active events"""
        session = await self._get_session_for_context(context)
        
        if not session:
            return "No active session."
        
        active = await self.db.get_active_events(session['id'])
        pending = await self.db.get_pending_events(session['id'])
        
        lines = []
        if active:
            lines.append("**Active Events:**")
            for e in active:
                lines.append(f"⚡ [{e['id']}] **{e['name']}** ({e['event_type']})")
        
        if pending:
            lines.append("\n**Pending Events:**")
            for e in pending:
                trigger = f" - {e['trigger_conditions'][:30]}..." if e.get('trigger_conditions') else ""
                lines.append(f"⏳ [{e['id']}] **{e['name']}**{trigger}")
        
        return "\n".join(lines) if lines else "No events active or pending."
    
    # =========================================================================
    # ENHANCED NPC TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _generate_npc(self, context: Dict, args: Dict) -> str:
        """Generate an NPC from template"""
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        session = await self._get_session_for_context(context)
        
        template = args.get('template', 'generic')
        name = args.get('name')
        location = args.get('location')
        purpose = args.get('purpose')
        custom_traits = args.get('custom_traits', {})
        
        # Template-based personality generation
        template_data = {
            'merchant': {'npc_type': 'neutral', 'personality': 'Shrewd but fair, always looking for a good deal. Knows local gossip.', 'is_merchant': True},
            'guard': {'npc_type': 'neutral', 'personality': 'Professional and vigilant, loyal to their post and the law.', 'is_merchant': False},
            'scholar': {'npc_type': 'friendly', 'personality': 'Curious and knowledgeable, easily distracted by intellectual topics.', 'is_merchant': False},
            'innkeeper': {'npc_type': 'friendly', 'personality': 'Welcoming and hospitable, loves to hear stories from travelers.', 'is_merchant': True},
            'noble': {'npc_type': 'neutral', 'personality': 'Proud and politically aware, concerned with status and alliances.', 'is_merchant': False},
            'criminal': {'npc_type': 'hostile', 'personality': 'Streetwise and cautious, speaks in coded language.', 'is_merchant': False},
            'mystic': {'npc_type': 'neutral', 'personality': 'Cryptic and enigmatic, speaks in riddles and prophecies.', 'is_merchant': False},
            'peasant': {'npc_type': 'friendly', 'personality': 'Humble and hardworking, knows the local area well.', 'is_merchant': False},
            'adventurer': {'npc_type': 'friendly', 'personality': 'Bold and confident, eager to share tales of adventure.', 'is_merchant': False},
            'villain': {'npc_type': 'hostile', 'personality': 'Calculating and dangerous, has their own sinister agenda.', 'is_merchant': False},
        }
        
        base = template_data.get(template, {'npc_type': 'neutral', 'personality': 'A mysterious figure.', 'is_merchant': False})
        
        # Apply custom traits
        personality = base['personality']
        if custom_traits:
            trait_str = ", ".join([f"{k}: {v}" for k, v in custom_traits.items()])
            personality += f" Additional traits: {trait_str}"
        
        # Create the NPC
        npc_id = await self.db.create_npc(
            guild_id=guild_id,
            name=name or f"Unknown {template.title()}",
            description=f"A {template} encountered by the party.",
            personality=personality,
            location=location,
            npc_type=base['npc_type'],
            is_merchant=base['is_merchant'],
            created_by=user_id,
            session_id=session['id'] if session else None
        )
        
        return f"👤 NPC Generated: **{name or f'Unknown {template.title()}'}** (ID: {npc_id})\nTemplate: {template.title()}\nPersonality: {personality[:100]}..."
    
    async def _set_npc_secret(self, args: Dict) -> str:
        """Set an NPC's hidden secret"""
        npc_id = args.get('npc_id')
        secret = args.get('secret')
        
        npc = await self.db.get_npc(npc_id)
        if not npc:
            return "Error: NPC not found"
        
        # Store secret in dialogue_context (using existing field)
        current_context = npc.get('dialogue_context') or '{}'
        try:
            context_data = json.loads(current_context)
        except:
            context_data = {}
        
        context_data['secret'] = secret
        await self.db.update_npc(npc_id, dialogue_context=json.dumps(context_data))
        
        return f"🔒 Secret set for **{npc['name']}**: {secret[:50]}..."

    # =========================================================================
    # CROSS-SYSTEM WIRING TOOL IMPLEMENTATIONS
    # These tools integrate multiple game systems for seamless gameplay
    # =========================================================================
    
    async def _move_character_to_location(self, args: Dict) -> str:
        """Move a character to a new location"""
        char_id = args.get('character_id')
        location_id = args.get('location_id')
        
        result = await self.db.move_character_to_location(char_id, location_id)
        
        if result.get('error'):
            return f"Error: {result['error']}"
        
        char = await self.db.get_character(char_id) or {}
        location = await self.db.get_location(location_id) or {}
        others = [other for other in await self.db.get_characters_at_location(location_id) if other.get('id') != char_id]
        npcs = await self.db.get_npcs_at_location(location_id)
        
        lines = [f"🚶 **{char.get('name', 'Character')}** moved to **{location.get('name', 'Unknown')}**"]
        lines.append(f"_{location.get('description', '')}_")
        
        if others:
            names = [o.get('name', 'Unknown') for o in others]
            lines.append(f"\n👥 Also here: {', '.join(names)}")
        
        if npcs:
            npc_names = [n.get('name', 'Unknown') for n in npcs]
            lines.append(f"🧑 NPCs present: {', '.join(npc_names)}")
        
        return "\n".join(lines)
    
    async def _get_characters_at_location(self, args: Dict) -> str:
        """Get all characters at a location"""
        location_id = args.get('location_id')
        
        characters = await self.db.get_characters_at_location(location_id)
        location = await self.db.get_location(location_id)
        
        if not location:
            return "Error: Location not found"
        
        if not characters:
            return f"No characters at **{location['name']}**"
        
        lines = [f"👥 Characters at **{location['name']}**:"]
        for char in characters:
            lines.append(f"  - {char['name']} (Level {char['level']} {char['char_class']})")
        
        return "\n".join(lines)
    
    async def _get_npcs_at_location(self, args: Dict) -> str:
        """Get all NPCs at a location"""
        location_id = args.get('location_id')
        
        npcs = await self.db.get_npcs_at_location(location_id)
        location = await self.db.get_location(location_id)
        
        if not location:
            return "Error: Location not found"
        
        if not npcs:
            return f"No NPCs at **{location['name']}**"
        
        lines = [f"🧑 NPCs at **{location['name']}**:"]
        for npc in npcs:
            disposition = npc.get('npc_type', 'neutral')
            merchant = " 🛒" if npc.get('is_merchant') else ""
            lines.append(f"  - **{npc['name']}**{merchant} ({disposition})")
            if npc.get('personality'):
                lines.append(f"    _{npc['personality'][:60]}..._")
        
        return "\n".join(lines)
    
    async def _explore_location(self, context: Dict, args: Dict) -> str:
        """Explore the current location - returns NPCs, items, events, connections"""
        char_id = args.get('character_id')
        char = await self.db.get_character(char_id)
        if not char:
            return "Error: Character not found"

        location_id = args.get('location_id') or char.get('current_location_id')
        if not location_id:
            return "Error: Character has no current location"
        
        result = await self.db.explore_location(char_id, location_id)
        
        if result.get('error'):
            return f"Error: {result['error']}"
        
        location = result.get('location', {})
        npcs = result.get('npcs', [])
        items = result.get('visible_items', [])
        connections = result.get('connections', [])
        characters = result.get('other_characters', [])
        events = []

        if char.get('session_id'):
            events = [
                event for event in await self.db.get_active_events(char['session_id'])
                if not event.get('location_id') or event.get('location_id') == location_id
            ]
        
        lines = [f"🔍 **Exploring {location.get('name', 'Unknown')}**"]
        lines.append(f"_{location.get('description', '')}_")
        
        if characters:
            names = [c.get('name') for c in characters]
            lines.append(f"\n👥 **Party members here:** {', '.join(names)}")
        
        if npcs:
            lines.append(f"\n🧑 **NPCs present:**")
            for npc in npcs:
                merchant = " (Merchant)" if npc.get('is_merchant') else ""
                lines.append(f"  - {npc['name']}{merchant}")
        
        if items:
            lines.append(f"\n📦 **Items found:**")
            for item in items:
                status = "✨ NEW!" if not item.get('is_discovered') else ""
                lines.append(f"  - {item['name']} {status}")
        
        if events:
            lines.append(f"\n⚡ **Active events here:**")
            for event in events:
                lines.append(f"  - {event['name']}")
        
        if connections:
            lines.append(f"\n🚪 **Exits:**")
            for conn in connections:
                direction = f"({conn.get('direction', 'path')})" if conn.get('direction') else ""
                lines.append(f"  - {conn.get('to_name', 'Unknown')} {direction}")
        
        if not (npcs or items or events or connections):
            lines.append("\n_The area seems quiet and unremarkable._")
        
        return "\n".join(lines)
    
    async def _pickup_story_item(self, context: Dict, args: Dict) -> str:
        """Character picks up a story item"""
        char_id = args.get('character_id')
        item_id = args.get('item_id')
        result = await self.db.pickup_story_item(item_id, char_id)
        
        if result.get('error'):
            return f"Error: {result['error']}"
        
        char = await self.db.get_character(char_id) or {}
        item = await self.db.get_story_item(item_id) or {}
        
        lines = [f"✨ **{char.get('name', 'Character')}** picks up **{item.get('name', 'item')}**!"]
        lines.append(f"_{item.get('description', '')}_")
        
        if item.get('lore') and not item.get('is_discovered'):
            lines.append(f"\n📜 *{item.get('lore')[:200]}...*")
        
        return "\n".join(lines)
    
    async def _drop_story_item(self, context: Dict, args: Dict) -> str:
        """Character drops a story item at current location"""
        char_id = args.get('character_id')
        item_id = args.get('item_id')
        char = await self.db.get_character(char_id)
        if not char:
            return "Error: Character not found"

        result = await self.db.drop_story_item(item_id, char.get('current_location_id'))
        
        if result.get('error'):
            return f"Error: {result['error']}"
        
        item = await self.db.get_story_item(item_id) or {}
        location = await self.db.get_location(char.get('current_location_id')) if char.get('current_location_id') else {}
        
        return f"📦 **{char.get('name', 'Character')}** drops **{item.get('name', 'item')}** at {location.get('name', 'this location')}."
    
    async def _long_rest(self, context: Dict, args: Dict) -> str:
        """Character takes a long rest - full recovery"""
        char_id = args.get('character_id')
        location_desc = args.get('location_description', 'at camp')
        interrupted = args.get('interrupted', False)

        if interrupted:
            return "Long rest was interrupted. No automatic recovery was applied."

        before = await self.db.get_character(char_id)
        result = await self.db.long_rest(char_id)
        
        if result.get('error'):
            return f"Error: {result['error']}"

        char = await self.db.get_character(char_id) or {}
        restored = result.get('restored', [])
        hp_restored = max(0, char.get('hp', 0) - (before or {}).get('hp', 0))
        mana_restored = max(0, char.get('mana', 0) - (before or {}).get('mana', 0))
        effects_cleared = sum(1 for entry in restored if 'cleared' in entry.lower())
        
        lines = [f"🌙 **{char.get('name', 'Character')}** takes a long rest {location_desc}"]
        lines.append("✨ _Eight hours pass peacefully..._")
        lines.append(f"💚 HP fully restored: {char.get('hp', 0)}/{char.get('max_hp', 0)}")
        lines.append(f"💙 Mana restored: +{mana_restored} ({char.get('mana', 0)}/{char.get('max_mana', 0)})")
        
        if effects_cleared > 0:
            lines.append(f"🧹 {effects_cleared} status effect(s) cleared")
        
        return "\n".join(lines)
    
    async def _short_rest(self, args: Dict) -> str:
        """Character takes a short rest - partial recovery"""
        char_id = args.get('character_id')
        before = await self.db.get_character(char_id)
        
        result = await self.db.short_rest(char_id)
        
        if result.get('error'):
            return f"Error: {result['error']}"

        char = await self.db.get_character(char_id) or {}
        hp_restored = max(0, char.get('hp', 0) - (before or {}).get('hp', 0))
        mana_restored = max(0, char.get('mana', 0) - (before or {}).get('mana', 0))
        
        lines = [f"⏰ **{char.get('name', 'Character')}** takes a short rest (1 hour)"]
        lines.append(f"💚 Recovered {hp_restored} HP → {char.get('hp', 0)}/{char.get('max_hp', 0)}")
        lines.append(f"💙 Recovered {mana_restored} mana → {char.get('mana', 0)}/{char.get('max_mana', 0)}")
        
        return "\n".join(lines)
    
    async def _end_combat_with_rewards(self, context: Dict, args: Dict) -> str:
        """End combat and distribute rewards"""
        combat_id = args.get('combat_id')
        victory = args.get('victory', True)
        bonus_xp = args.get('bonus_xp', 0)
        bonus_gold = args.get('bonus_gold', 0)
        loot_items = args.get('loot_items', [])
        
        # If no combat_id provided, try to get active combat
        if not combat_id:
            channel_id = context.get('channel_id')
            session = await self._get_session_for_context(context)
            if session:
                combat = await self.db.get_combat_for_channel(session['id'], channel_id)
                if combat:
                    combat_id = combat['id']
            if not combat_id and context.get('guild_id') and channel_id:
                combat = await self.db.get_active_combat(context.get('guild_id'), channel_id)
                if combat:
                    combat_id = combat['id']
        
        if not combat_id:
            return "Error: No active combat found"

        if not victory:
            await self.db.end_combat(combat_id)
            return "💀 **DEFEAT!** The party falls..."
        
        result = await self.db.end_combat_with_rewards(
            encounter_id=combat_id,
            xp_per_character=bonus_xp,
            gold_per_character=bonus_gold,
            loot_items=loot_items
        )
        
        if result.get('error'):
            return f"Error: {result['error']}"
        
        lines = []
        lines.append("⚔️ **VICTORY!** Combat concluded.")

        xp_awards = result.get('xp_awarded', [])
        gold_awards = result.get('gold_awarded', [])
        loot_distributed = result.get('loot_distributed', [])
        total_xp = bonus_xp
        total_gold = bonus_gold
        
        if xp_awards:
            lines.append(f"\n📈 **Experience Earned:** {total_xp} XP each")
            for award in xp_awards:
                level_up = " 🎉 LEVEL UP!" if award.get('leveled_up') else ""
                lines.append(f"  - {award.get('name', 'Character')}: +{award.get('xp_gained', 0)} XP{level_up}")
        
        if gold_awards:
            lines.append(f"\n💰 **Gold Looted:** {total_gold} gold (split)")
            for award in gold_awards:
                lines.append(f"  - {award.get('name', 'Character')}: +{award.get('gold_gained', 0)} gold")
        
        if loot_distributed:
            lines.append(f"\n🎁 **Items Found:**")
            for item in loot_distributed:
                lines.append(f"  - {item.get('item_name', 'Unknown')} → {item.get('given_to', 'Party')}")
        
        # Sync damage back to characters
        sync_result = result.get('hp_synced', [])
        if sync_result:
            lines.append(f"\n❤️ **Post-Combat HP:**")
            for hp_data in sync_result:
                char = await self.db.get_character(hp_data.get('character_id'))
                name = char['name'] if char else f"Character #{hp_data.get('character_id')}"
                lines.append(f"  - {name}: {hp_data.get('new_hp', 0)}/{hp_data.get('max_hp', 0)} HP")
        
        return "\n".join(lines)
    
    async def _complete_quest_with_rewards(self, context: Dict, args: Dict) -> str:
        """Complete a quest and distribute rewards to participants"""
        quest_id = args.get('quest_id')
        character_ids = args.get('character_ids', [])
        bonus_rewards = args.get('bonus_rewards', {})

        if not character_ids:
            return "Error: character_ids is required"

        results = []
        for character_id in character_ids:
            result = await self.db.complete_quest_with_rewards(quest_id, character_id)
            if result.get('error'):
                return f"Error: {result['error']}"

            if bonus_rewards.get('xp'):
                xp_result = await self.db.add_experience(character_id, bonus_rewards['xp'])
                result['xp_gained'] += bonus_rewards['xp']
                result['leveled_up'] = result.get('leveled_up') or xp_result.get('leveled_up', False)
                result['new_level'] = xp_result.get('new_level', result.get('new_level'))

            if bonus_rewards.get('gold'):
                await self.db.update_gold(character_id, bonus_rewards['gold'])
                result['gold_gained'] += bonus_rewards['gold']

            results.append(result)
        
        quest = await self.db.get_quest(quest_id) or {}
        lines = [f"🎊 **QUEST COMPLETE: {quest.get('title', 'Unknown')}**"]
        lines.append(f"_{quest.get('description', '')}_")
        
        if results:
            lines.append(f"\n🏆 **Rewards distributed:**")
            for char in results:
                level_up = " 🎉 LEVEL UP!" if char.get('leveled_up') else ""
                lines.append(f"  - **{char.get('character_name', 'Character')}**: +{char.get('xp_gained', 0)} XP, +{char.get('gold_gained', 0)} gold{level_up}")
        
        return "\n".join(lines)
    
    async def _get_comprehensive_session_state(self, args: Dict) -> str:
        """Get complete session state for context"""
        session_id = args.get('session_id')
        
        result = await self.db.get_comprehensive_session_state(session_id)

        if not result:
            return "Error: Session not found"

        session = result
        party = result.get('characters_full', [])
        game_state = result.get('game_state') or {}
        location = None
        location_name = game_state.get('current_location')
        if location_name:
            locations = await self.db.get_locations(session_id=session_id)
            location = next((loc for loc in locations if loc.get('name') == location_name), None)
        npcs = await self.db.get_npcs_by_location(session.get('guild_id'), location_name) if location_name else []
        active_quest = await self.db.get_quest(session.get('current_quest_id')) if session.get('current_quest_id') else None
        events = result.get('story_events', [])
        recent_story = result.get('story_log', [])
        
        lines = [f"📋 **Session State: {session.get('name', 'Unknown')}**"]
        lines.append(f"Setting: {session.get('setting', 'Unknown')}")
        
        # Party info
        if party:
            lines.append(f"\n👥 **Party ({len(party)} members):**")
            for char in party:
                hp_pct = int((char.get('hp', 0) / max(char.get('max_hp', 1), 1)) * 100)
                hp_bar = "🟢" if hp_pct > 50 else "🟡" if hp_pct > 25 else "🔴"
                lines.append(f"  {hp_bar} {char['name']} - Lv{char['level']} {char['char_class']} ({char['hp']}/{char['max_hp']} HP)")
        
        # Current location
        if location:
            lines.append(f"\n📍 **Current Location:** {location.get('name', 'Unknown')}")
            lines.append(f"  _{location.get('description', '')[:100]}..._")
        
        # NPCs present
        if npcs:
            npc_names = [n.get('name', 'Unknown') for n in npcs]
            lines.append(f"\n🧑 **NPCs Present:** {', '.join(npc_names)}")
        
        # Active quest
        if active_quest:
            lines.append(f"\n📜 **Active Quest:** {active_quest.get('title', 'Unknown')}")
            objectives = active_quest.get('objectives', [])
            completed = sum(1 for o in objectives if o.get('completed'))
            lines.append(f"  Progress: {completed}/{len(objectives)} objectives")
        
        # Active events
        if events:
            event_names = [e.get('name', 'Unknown') for e in events]
            lines.append(f"\n⚡ **Active Events:** {', '.join(event_names)}")
        
        # Recent story
        if recent_story:
            lines.append(f"\n📖 **Recent Events:**")
            for entry in recent_story[-3:]:  # Last 3 entries
                preview = entry.get('content') or entry.get('entry_text') or ''
                lines.append(f"  - {preview[:80]}...")
        
        return "\n".join(lines)
    
    # =========================================================================
    # NPC PARTY MEMBER TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _add_npc_to_party(self, context: Dict, args: Dict) -> str:
        """Add an NPC as a party member/companion"""
        npc_id = args.get('npc_id')
        party_role = args.get('party_role')
        combat_stats = args.get('combat_stats', {})
        
        npc = await self.db.get_npc(npc_id)
        if not npc:
            return f"Error: NPC with ID {npc_id} not found."
        
        # Default combat stats based on NPC type if not provided
        if not combat_stats:
            default_stats = {
                'hp': 20, 'max_hp': 20, 'ac': 12, 
                'attack_bonus': 3, 'damage': '1d8+1',
                'abilities': []
            }
            # Adjust based on NPC type
            if npc.get('npc_type') == 'hostile':
                default_stats['attack_bonus'] = 5
                default_stats['damage'] = '1d10+3'
            combat_stats = default_stats
        
        success = await self.db.add_npc_to_party(npc_id, party_role, combat_stats)
        
        if success:
            role_str = f" as {party_role}" if party_role else ""
            return f"🤝 **{npc['name']}** has joined the party{role_str}! They will travel with you and assist in combat."
        else:
            return f"Error: Could not add {npc['name']} to the party."
    
    async def _remove_npc_from_party(self, args: Dict) -> str:
        """Remove an NPC from the party"""
        npc_id = args.get('npc_id')
        reason = args.get('reason', 'departed')
        
        npc = await self.db.get_npc(npc_id)
        if not npc:
            return f"Error: NPC with ID {npc_id} not found."
        
        success = await self.db.remove_npc_from_party(npc_id)
        
        if success:
            return f"👋 **{npc['name']}** has left the party. Reason: {reason}"
        else:
            return f"Error: Could not remove {npc['name']} from the party."
    
    async def _get_party_npcs(self, context: Dict) -> str:
        """Get all NPC companions in the party"""
        session = await self._get_session_for_context(context)
        
        if not session:
            return "No active session."
        
        party_npcs = await self.db.get_party_npcs(session['id'])
        
        if not party_npcs:
            return "No NPC companions in the party."
        
        lines = ["🤝 **Party Companions:**"]
        for npc in party_npcs:
            role = npc.get('party_role', 'companion')
            loyalty = npc.get('loyalty', 50)
            loyalty_desc = "Devoted" if loyalty >= 80 else "Loyal" if loyalty >= 60 else "Friendly" if loyalty >= 40 else "Uncertain" if loyalty >= 20 else "Disloyal"
            
            combat_stats = npc.get('combat_stats', {})
            hp_str = ""
            if combat_stats:
                hp = combat_stats.get('hp', '?')
                max_hp = combat_stats.get('max_hp', '?')
                hp_str = f" | HP: {hp}/{max_hp}"
            
            lines.append(f"  [{npc['id']}] **{npc['name']}** ({role}) - {loyalty_desc} ({loyalty}/100){hp_str}")
        
        return "\n".join(lines)
    
    async def _update_npc_loyalty(self, args: Dict) -> str:
        """Update an NPC party member's loyalty"""
        npc_id = args.get('npc_id')
        loyalty_change = args.get('loyalty_change', 0)
        reason = args.get('reason', 'unspecified')
        
        npc = await self.db.get_npc(npc_id)
        if not npc:
            return f"Error: NPC with ID {npc_id} not found."
        
        new_loyalty = await self.db.update_npc_loyalty(npc_id, loyalty_change)
        
        change_str = f"+{loyalty_change}" if loyalty_change > 0 else str(loyalty_change)
        emoji = "💚" if loyalty_change > 0 else "💔"
        
        return f"{emoji} **{npc['name']}**'s loyalty changed by {change_str} ({reason}). Loyalty: {new_loyalty}/100"
    
    async def _npc_party_action(self, context: Dict, args: Dict) -> str:
        """Have an NPC party member take an action"""
        npc_id = args.get('npc_id')
        action_type = args.get('action_type')
        target = args.get('target')
        ability_name = args.get('ability_name')
        
        npc = await self.db.get_npc(npc_id)
        if not npc:
            return f"Error: NPC with ID {npc_id} not found."
        
        combat_stats = npc.get('combat_stats', {})
        if isinstance(combat_stats, str):
            combat_stats = json.loads(combat_stats) if combat_stats else {}
        
        result_lines = [f"⚔️ **{npc['name']}** takes action: {action_type}"]
        
        if action_type == "attack":
            attack_bonus = combat_stats.get('attack_bonus', 3)
            damage = combat_stats.get('damage', '1d6+1')
            
            # Roll attack
            roll = random.randint(1, 20)
            total = roll + attack_bonus
            crit = roll == 20
            
            result_lines.append(f"  Attack Roll: {roll} + {attack_bonus} = **{total}**" + (" CRITICAL!" if crit else ""))
            
            if target:
                result_lines.append(f"  Target: {target}")
                result_lines.append(f"  Damage on hit: {damage}" + (" (DOUBLE)" if crit else ""))
        
        elif action_type == "defend":
            result_lines.append(f"  {npc['name']} takes a defensive stance, gaining +2 AC until their next turn.")
        
        elif action_type == "heal":
            heal_amount = random.randint(1, 8) + 2
            result_lines.append(f"  {npc['name']} heals {target or 'an ally'} for **{heal_amount}** HP!")
        
        elif action_type == "support":
            result_lines.append(f"  {npc['name']} provides support to {target or 'the party'}, granting advantage on their next roll.")
        
        elif action_type == "ability" and ability_name:
            abilities = combat_stats.get('abilities', [])
            if ability_name in abilities:
                result_lines.append(f"  {npc['name']} uses **{ability_name}**!")
            else:
                result_lines.append(f"  {npc['name']} attempts to use {ability_name} but doesn't know that ability.")
        
        elif action_type == "flee":
            result_lines.append(f"  {npc['name']} attempts to flee from combat!")
            # Check loyalty - low loyalty NPCs might actually leave
            loyalty = await self.db.get_npc_loyalty(npc_id)
            if loyalty < 30:
                result_lines.append(f"  ⚠️ Due to low loyalty, {npc['name']} might not return...")
        
        return "\n".join(result_lines)
    
    # =========================================================================
    # GENERATIVE AI / WORLDBUILDING TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _generate_world(self, context: Dict, args: Dict) -> str:
        """Generate world elements based on campaign theme"""
        theme = args.get('theme', 'fantasy adventure')
        scope = args.get('scope', 'region')
        focus_elements = args.get('focus_elements', [])
        tone = args.get('tone', 'mixed')
        
        session = await self._get_session_for_context(context)
        
        lines = [f"🌍 **World Generation Request**"]
        lines.append(f"Theme: {theme}")
        lines.append(f"Scope: {scope}")
        lines.append(f"Tone: {tone}")
        if focus_elements:
            lines.append(f"Focus Elements: {', '.join(focus_elements)}")
        
        lines.append(f"\n**Suggested Elements to Create:**")
        
        if scope in ['region', 'full_world']:
            lines.append("- Main settlement(s)")
            lines.append("- Key factions or groups")
            lines.append("- Major landmarks")
            lines.append("- Regional threats/conflicts")
        
        if scope in ['city', 'full_world']:
            lines.append("- Districts/neighborhoods")
            lines.append("- Important buildings")
            lines.append("- Local power structures")
            lines.append("- Underground elements")
        
        if scope == 'dungeon':
            lines.append("- Entrance/approach")
            lines.append("- Room layouts")
            lines.append("- Traps and hazards")
            lines.append("- Boss encounter area")
            lines.append("- Treasure locations")
        
        lines.append(f"\n*Use create_location and create_npc tools to build out these elements.*")
        
        return "\n".join(lines)
    
    async def _generate_key_npcs(self, context: Dict, args: Dict) -> str:
        """Generate key NPCs for the campaign"""
        campaign_theme = args.get('campaign_theme', 'adventure')
        goals = args.get('goals', '')
        npc_types = args.get('npc_types', ['ally', 'villain', 'quest_giver'])
        count = args.get('count', 3)
        make_party_members = args.get('make_party_members', False)
        
        session = await self._get_session_for_context(context)
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        
        # Load NPC templates
        try:
            templates_data = await self._load_theme_content(context, 'npc_templates.json')
            templates = templates_data.get('templates', templates_data)
        except Exception:
            templates = {}
        
        created_npcs = []
        
        for i, npc_type in enumerate(npc_types[:count]):
            template_key = {
                'ally': 'adventurer',
                'mentor': 'scholar',
                'rival': 'adventurer',
                'villain': 'villain',
                'quest_giver': 'noble',
                'love_interest': 'innkeeper',
                'comic_relief': 'peasant',
                'mysterious_stranger': 'mystic',
                'key_figure': 'noble'
            }.get(npc_type, 'adventurer')
            
            template = templates.get(template_key, {})
            
            names = template.get('names', ['Unknown'])
            name = random.choice(names) if names else f"NPC_{i+1}"
            
            personalities = template.get('personalities', ['mysterious'])
            personality = random.choice(personalities)
            
            disposition = {
                'ally': 'friendly',
                'mentor': 'friendly', 
                'rival': 'neutral',
                'villain': 'hostile',
                'quest_giver': 'neutral',
                'love_interest': 'friendly',
                'comic_relief': 'friendly',
                'mysterious_stranger': 'neutral',
                'key_figure': 'neutral'
            }.get(npc_type, 'neutral')
            
            description = f"A {npc_type} fitting the theme: {campaign_theme}"
            if goals:
                description += f". Related to: {goals}"
            
            npc_id = await self.db.create_npc(
                guild_id=guild_id,
                name=name,
                description=description,
                personality=personality,
                created_by=user_id,
                npc_type=disposition,
                session_id=session['id'] if session else None
            )
            
            created_npcs.append({
                'id': npc_id,
                'name': name,
                'type': npc_type,
                'disposition': disposition
            })
            
            if make_party_members and npc_type in ['ally', 'mentor', 'comic_relief']:
                role = 'support' if npc_type == 'mentor' else 'damage' if npc_type == 'ally' else 'utility'
                await self.db.add_npc_to_party(npc_id, role, {
                    'hp': 25, 'max_hp': 25, 'ac': 14,
                    'attack_bonus': 4, 'damage': '1d8+2',
                    'abilities': ['special_attack']
                })
        
        lines = [f"👥 **Generated {len(created_npcs)} Key NPCs:**"]
        for npc in created_npcs:
            party_note = " (Can join party)" if make_party_members and npc['type'] in ['ally', 'mentor', 'comic_relief'] else ""
            lines.append(f"  [{npc['id']}] **{npc['name']}** - {npc['type']} ({npc['disposition']}){party_note}")
        
        lines.append(f"\n*Use get_npc_info to see details, or add_npc_to_party to recruit allies.*")
        
        return "\n".join(lines)
    
    async def _generate_location(self, context: Dict, args: Dict) -> str:
        """Generate a detailed location"""
        location_type = args.get('location_type', 'generic')
        theme = args.get('theme', '')
        purpose = args.get('purpose', '')
        danger_level = args.get('danger_level', 'medium')
        generate_npcs = args.get('generate_npcs', False)
        generate_loot = args.get('generate_loot', False)
        
        session = await self._get_session_for_context(context)
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        
        name_prefixes = {
            'town': ['Riverside', 'Hill', 'North', 'Iron', 'Golden'],
            'city': ['New', 'Old', 'Great', 'Port', 'Royal'],
            'dungeon': ['Dark', 'Ancient', 'Forgotten', 'Cursed', 'Hidden'],
            'wilderness': ['Wild', 'Savage', 'Peaceful', 'Dark', 'Misty'],
            'stronghold': ['Iron', 'Stone', 'Blood', 'Storm', 'Dragon'],
            'ruins': ['Lost', 'Ancient', 'Sunken', 'Crumbling', 'Haunted'],
            'tavern': ['The Rusty', 'The Golden', 'The Prancing', 'The Drunken', 'The Lucky'],
            'shop': ['Ye Olde', 'Fine', 'Discount', 'Rare', 'Curious'],
            'temple': ['Sacred', 'Holy', 'Dark', 'Ancient', 'Mystic'],
            'secret_base': ['Hidden', 'Secret', 'Underground', 'Shadow', 'Covert']
        }
        
        name_suffixes = {
            'town': ['burg', 'ton', 'ville', 'ford', 'haven'],
            'city': ['polis', 'heim', 'grad', 'dale', 'shire'],
            'dungeon': ['Depths', 'Caverns', 'Crypt', 'Lair', 'Maze'],
            'wilderness': ['Woods', 'Plains', 'Swamp', 'Mountains', 'Desert'],
            'stronghold': ['Keep', 'Fortress', 'Citadel', 'Hold', 'Tower'],
            'ruins': ['Ruins', 'Remnants', 'Remains', 'Tomb', 'Temple'],
            'tavern': ['Dragon', 'Pony', 'Mug', 'Sword', 'Pilgrim'],
            'shop': ['Goods', 'Wares', 'Emporium', 'Bazaar', 'Market'],
            'temple': ['Shrine', 'Sanctuary', 'Chapel', 'Cathedral', 'Altar'],
            'secret_base': ['Haven', 'Hideout', 'Sanctum', 'Lair', 'Den']
        }
        
        prefix = random.choice(name_prefixes.get(location_type, ['The']))
        suffix = random.choice(name_suffixes.get(location_type, ['Place']))
        
        if location_type == 'tavern':
            name = f"{prefix} {suffix}"
        else:
            name = f"{prefix}{suffix}"
        
        if theme:
            name = f"{name} ({theme})"
        
        description = f"A {danger_level}-danger {location_type}"
        if theme:
            description += f" with a {theme} theme"
        if purpose:
            description += f". Purpose: {purpose}"
        
        poi_options = {
            'town': ['market square', 'town hall', 'blacksmith', 'inn', 'temple', 'well'],
            'city': ['grand plaza', 'palace', 'warehouse district', 'slums', 'merchant quarter', 'arena'],
            'dungeon': ['entrance hall', 'trap corridor', 'treasure room', 'boss chamber', 'secret passage', 'puzzle room'],
            'wilderness': ['ancient tree', 'river crossing', 'cave entrance', 'abandoned camp', 'strange monument', 'hunting ground'],
            'stronghold': ['great hall', 'armory', 'dungeon', 'tower', 'courtyard', 'throne room'],
            'ruins': ['collapsed hall', 'intact chamber', 'sealed door', 'overgrown garden', 'crumbling tower', 'hidden vault'],
            'tavern': ['common room', 'private booths', 'cellar', 'upstairs rooms', 'kitchen', 'back alley'],
            'shop': ['display floor', 'back room', 'storage', 'counter', 'window display', 'secret stock'],
            'temple': ['altar', 'meditation chamber', 'library', 'crypt', 'bell tower', 'garden'],
            'secret_base': ['hidden entrance', 'meeting room', 'armory', 'escape tunnel', 'leader quarters', 'holding cells']
        }
        
        pois = random.sample(poi_options.get(location_type, ['notable feature']), min(3, len(poi_options.get(location_type, ['notable feature']))))
        
        location_id = await self.db.create_location(
            guild_id=guild_id,
            session_id=session['id'] if session else None,
            name=name,
            description=description,
            location_type=location_type,
            points_of_interest=pois,
            created_by=user_id
        )
        
        lines = [f"📍 **Generated Location:** {name}"]
        lines.append(f"Type: {location_type} | Danger: {danger_level}")
        lines.append(f"ID: {location_id}")
        lines.append(f"\n**Points of Interest:**")
        for poi in pois:
            lines.append(f"  - {poi}")
        
        if generate_npcs:
            lines.append(f"\n*Use generate_key_npcs to populate this location.*")
        
        if generate_loot:
            lines.append(f"*Use generate_loot to add treasure here.*")
        
        return "\n".join(lines)
    
    async def _generate_quest(self, context: Dict, args: Dict) -> str:
        """Generate a quest with objectives"""
        quest_type = args.get('quest_type', 'side')
        difficulty = args.get('difficulty', 'medium')
        theme = args.get('theme', '')
        related_npc_id = args.get('related_npc_id')
        location_id = args.get('location_id')
        auto_create = args.get('auto_create', False)
        
        session = await self._get_session_for_context(context)
        guild_id = context.get('guild_id')
        
        quest_titles = {
            'main': ['The Final Confrontation', 'Destiny Awaits', 'The Great Mission', 'The Ultimate Challenge'],
            'side': ['A Small Favor', 'Local Troubles', 'The Side Job', 'Unfinished Business'],
            'fetch': ['Retrieve the {item}', 'Find the Lost {item}', 'Gather {count} {item}s', 'The Missing {item}'],
            'kill': ['Hunt the {enemy}', 'Eliminate the Threat', 'Bounty: {enemy}', 'The {enemy} Problem'],
            'escort': ['Protect the {target}', 'Safe Passage', 'The Journey to {place}', 'Guard Duty'],
            'mystery': ['The Strange Occurrence', 'Investigate the {event}', 'Uncover the Truth', 'The Hidden Secret'],
            'rescue': ['Save the {target}', 'Rescue Mission', 'The Captive', 'Break Them Out'],
            'exploration': ['Chart the Unknown', 'Explore the {place}', 'The Lost {place}', 'Terra Incognita'],
            'boss': ['Face the {boss}', 'The Final Battle', 'Showdown with {boss}', 'The Ultimate Enemy']
        }
        
        title_templates = quest_titles.get(quest_type, ['A Quest'])
        title = random.choice(title_templates)
        
        items = ['artifact', 'crystal', 'scroll', 'weapon', 'key', 'relic']
        enemies = ['beast', 'bandit leader', 'monster', 'cultist', 'demon', 'dragon']
        targets = ['merchant', 'noble', 'child', 'prisoner', 'sage', 'heir']
        places = ['ruins', 'mountain', 'forest', 'castle', 'temple', 'cave']
        bosses = ['Dark Lord', 'Ancient Evil', 'Corrupt King', 'Demon Prince', 'Dragon']
        
        title = title.replace('{item}', random.choice(items))
        title = title.replace('{count}', str(random.randint(3, 10)))
        title = title.replace('{enemy}', random.choice(enemies))
        title = title.replace('{target}', random.choice(targets))
        title = title.replace('{place}', random.choice(places))
        title = title.replace('{boss}', random.choice(bosses))
        title = title.replace('{event}', 'mysterious disappearances')
        
        if theme:
            title = f"{title} ({theme})"
        
        objective_templates = {
            'main': [
                {'desc': 'Gather allies for the final battle', 'optional': False},
                {'desc': 'Acquire the necessary equipment', 'optional': False},
                {'desc': 'Defeat the main antagonist', 'optional': False}
            ],
            'side': [
                {'desc': 'Speak with the quest giver', 'optional': False},
                {'desc': 'Complete the task', 'optional': False},
                {'desc': 'Return for reward', 'optional': False}
            ],
            'fetch': [
                {'desc': 'Learn where the item is located', 'optional': False},
                {'desc': 'Travel to the location', 'optional': False},
                {'desc': 'Retrieve the item', 'optional': False},
                {'desc': 'Return the item', 'optional': False}
            ],
            'kill': [
                {'desc': 'Track down the target', 'optional': False},
                {'desc': 'Defeat the target', 'optional': False},
                {'desc': 'Collect proof of the deed', 'optional': True}
            ],
            'escort': [
                {'desc': 'Meet with the person to escort', 'optional': False},
                {'desc': 'Protect them during the journey', 'optional': False},
                {'desc': 'Arrive at the destination safely', 'optional': False}
            ],
            'mystery': [
                {'desc': 'Investigate the scene', 'optional': False},
                {'desc': 'Interview witnesses', 'optional': False},
                {'desc': 'Follow the clues', 'optional': False},
                {'desc': 'Confront the culprit', 'optional': False}
            ],
            'rescue': [
                {'desc': 'Learn where they are held', 'optional': False},
                {'desc': 'Infiltrate the location', 'optional': False},
                {'desc': 'Free the captive', 'optional': False},
                {'desc': 'Escape to safety', 'optional': False}
            ],
            'exploration': [
                {'desc': 'Find the entrance', 'optional': False},
                {'desc': 'Explore the area', 'optional': False},
                {'desc': 'Map key locations', 'optional': True},
                {'desc': 'Discover the secret', 'optional': False}
            ],
            'boss': [
                {'desc': 'Prepare for the confrontation', 'optional': False},
                {'desc': 'Reach the boss', 'optional': False},
                {'desc': 'Defeat the boss', 'optional': False}
            ]
        }
        
        objectives = objective_templates.get(quest_type, [{'desc': 'Complete the quest', 'optional': False}])
        
        reward_multiplier = {'easy': 1, 'medium': 2, 'hard': 3, 'epic': 5}.get(difficulty, 2)
        xp_reward = 100 * reward_multiplier
        gold_reward = 50 * reward_multiplier
        
        lines = [f"📜 **Generated Quest: {title}**"]
        lines.append(f"Type: {quest_type} | Difficulty: {difficulty}")
        lines.append(f"\n**Objectives:**")
        for i, obj in enumerate(objectives, 1):
            opt = " (optional)" if obj.get('optional') else ""
            lines.append(f"  {i}. {obj['desc']}{opt}")
        
        lines.append(f"\n**Suggested Rewards:**")
        lines.append(f"  - {xp_reward} XP per character")
        lines.append(f"  - {gold_reward} gold per character")
        
        if auto_create and session:
            quest_id = await self.db.create_quest(
                guild_id=guild_id,
                session_id=session['id'],
                title=title,
                description=f"A {difficulty} {quest_type} quest" + (f" with theme: {theme}" if theme else ""),
                quest_type=quest_type,
                giver_npc_id=related_npc_id,
                objectives=objectives,
                rewards={'xp': xp_reward, 'gold': gold_reward}
            )
            lines.append(f"\n✅ Quest created with ID: {quest_id}")
        else:
            lines.append(f"\n*Use create_quest tool to add this quest to the game.*")
        
        return "\n".join(lines)
    
    async def _generate_encounter(self, context: Dict, args: Dict) -> str:
        """Generate an encounter"""
        encounter_type = args.get('encounter_type', 'combat')
        difficulty = args.get('difficulty', 'medium')
        theme = args.get('theme', '')
        party_level = args.get('party_level')
        party_size = args.get('party_size')
        auto_start_combat = args.get('auto_start_combat', False)
        
        session = await self._get_session_for_context(context)
        
        if session and (not party_level or not party_size):
            participants = await self.db.get_session_participants(session['id'])
            if participants:
                levels = [p.get('level', 1) for p in participants if p.get('character_id')]
                party_level = party_level or (sum(levels) // len(levels) if levels else 1)
                party_size = party_size or len([p for p in participants if p.get('character_id')])
        
        party_level = party_level or 1
        party_size = party_size or 4
        
        try:
            enemies_payload = await self._load_theme_content(context, 'enemies.json')
            enemies_data = enemies_payload.get('enemies', enemies_payload)
        except Exception:
            enemies_data = {}
        
        lines = [f"⚔️ **Generated Encounter**"]
        lines.append(f"Type: {encounter_type} | Difficulty: {difficulty}")
        lines.append(f"Party Level: {party_level} | Party Size: {party_size}")
        
        if theme:
            lines.append(f"Theme: {theme}")
        
        if encounter_type == 'combat' or encounter_type == 'ambush' or encounter_type == 'boss':
            enemy_count = {
                'easy': max(1, party_size - 1),
                'medium': party_size,
                'hard': party_size + 1,
                'deadly': party_size + 2
            }.get(difficulty, party_size)
            
            if encounter_type == 'boss':
                enemy_count = 1
            
            available_enemies = list(enemies_data.keys()) if enemies_data else ['goblin', 'orc', 'skeleton']
            
            lines.append(f"\n**Suggested Enemies ({enemy_count}):**")
            for i in range(enemy_count):
                enemy_type = random.choice(available_enemies)
                enemy_data = enemies_data.get(enemy_type, {'hp': 10, 'ac': 12, 'damage': '1d6'})
                
                hp = enemy_data.get('hp', 10) + (party_level * 2)
                ac = enemy_data.get('ac', 12)
                damage = enemy_data.get('damage', '1d6')
                
                if encounter_type == 'boss':
                    hp *= 3
                    lines.append(f"  🔥 **BOSS: {enemy_type.title()}** - HP: {hp}, AC: {ac+2}, Damage: {damage}+{party_level}")
                else:
                    lines.append(f"  - {enemy_type.title()} - HP: {hp}, AC: {ac}, Damage: {damage}")
            
            base_xp = {'easy': 25, 'medium': 50, 'hard': 100, 'deadly': 200}.get(difficulty, 50)
            total_xp = base_xp * enemy_count * party_level
            lines.append(f"\n**XP Reward:** {total_xp} XP (to split)")
        
        elif encounter_type == 'social':
            lines.append(f"\n**Social Encounter:**")
            lines.append("- NPC with important information or obstacle")
            lines.append("- Skill checks: Persuasion, Deception, Intimidation")
            lines.append("- Potential outcomes: Alliance, Information, Passage")
        
        elif encounter_type == 'puzzle':
            lines.append(f"\n**Puzzle Encounter:**")
            puzzles = ['riddle door', 'pressure plates', 'elemental locks', 'symbol matching', 'lever sequence']
            lines.append(f"- Type: {random.choice(puzzles)}")
            lines.append("- Skill checks: Investigation, Intelligence, Arcana")
            lines.append(f"- DC: {10 + party_level + (3 if difficulty == 'hard' else 0)}")
        
        elif encounter_type == 'trap':
            lines.append(f"\n**Trap Encounter:**")
            traps = ['pit trap', 'arrow trap', 'poison gas', 'falling rocks', 'magical ward']
            trap_type = random.choice(traps)
            dc = 10 + party_level + {'easy': 0, 'medium': 2, 'hard': 5, 'deadly': 8}.get(difficulty, 2)
            damage = f"{party_level}d6"
            lines.append(f"- Type: {trap_type}")
            lines.append(f"- Detection DC: {dc}")
            lines.append(f"- Disarm DC: {dc + 2}")
            lines.append(f"- Damage: {damage}")
        
        if auto_start_combat and encounter_type in ['combat', 'ambush', 'boss']:
            lines.append(f"\n*Use start_combat and add_enemy tools to begin this encounter.*")
        
        return "\n".join(lines)
    
    async def _generate_backstory(self, context: Dict, args: Dict) -> str:
        """Generate or expand a character's backstory"""
        character_id = args.get('character_id')
        hooks = args.get('hooks', [])
        connection_to_plot = args.get('connection_to_plot', '')
        depth = args.get('depth', 'moderate')
        
        char = await self.db.get_character(character_id)
        if not char:
            return f"Error: Character with ID {character_id} not found."
        
        lines = [f"📖 **Backstory Generation for {char['name']}**"]
        lines.append(f"Race: {char['race']} | Class: {char['char_class']} | Level: {char['level']}")
        
        current = char.get('backstory') or 'No existing backstory.'
        lines.append(f"\n**Current Backstory:** {current[:200]}...")
        
        lines.append(f"\n**Generated Backstory Elements ({depth}):**")
        
        origins = {
            'human': ['small farming village', 'bustling city', 'coastal town', 'mountain settlement'],
            'elf': ['ancient forest', 'hidden enclave', 'crystal spire', 'woodland realm'],
            'dwarf': ['mountain stronghold', 'underground city', 'mining colony', 'forge town'],
            'halfling': ['peaceful shire', 'river community', 'traveling caravan', 'hidden village']
        }
        race_origins = origins.get(char['race'].lower(), ['unknown lands'])
        origin = random.choice(race_origins)
        lines.append(f"- **Origin:** Born in a {origin}")
        
        class_backgrounds = {
            'warrior': ['trained by a legendary knight', 'survived a brutal war', 'rose from gladiator pits'],
            'mage': ['discovered magic accidentally', 'apprenticed to a wizard', 'touched by wild magic'],
            'rogue': ['grew up on the streets', 'former guild member', 'wrongfully accused noble'],
            'cleric': ['received divine vision', 'raised in a temple', 'converted after tragedy'],
            'ranger': ['grew up in the wilderness', 'sole survivor of attack', 'former military scout'],
            'bard': ['trained in a college', 'traveling performer family', 'self-taught prodigy']
        }
        class_bg = class_backgrounds.get(char['char_class'].lower(), ['mysterious past'])
        lines.append(f"- **Training:** {random.choice(class_bg).title()}")
        
        if hooks:
            lines.append(f"- **Personal Hooks:** {', '.join(hooks)}")
        else:
            default_hooks = ['seeking lost family', 'pursuing ancient knowledge', 'running from dark past', 'proving themselves worthy']
            lines.append(f"- **Suggested Hook:** {random.choice(default_hooks).title()}")
        
        if connection_to_plot:
            lines.append(f"- **Plot Connection:** {connection_to_plot}")
        
        lines.append(f"- **Key Relationship:** A {random.choice(['mentor', 'rival', 'lost love', 'sibling', 'old friend'])} who shaped their path")
        
        secrets = ['knows forbidden knowledge', 'carries a cursed item', 'has a hidden bloodline', 'witnessed something they shouldn\'t have']
        lines.append(f"- **Potential Secret:** {random.choice(secrets).title()}")
        
        if depth == 'detailed':
            lines.append(f"\n**Detailed History:**")
            lines.append(f"- Early life shaped by {origin}")
            lines.append(f"- Pivotal moment that set them on their path")
            lines.append(f"- Previous adventures or accomplishments")
            lines.append(f"- Current goals and motivations")
            lines.append(f"- Fears and weaknesses")
        
        lines.append(f"\n*Update the character's backstory using update_character_stats or direct database update.*")
        
        return "\n".join(lines)
    
    async def _generate_loot(self, context: Dict, args: Dict) -> str:
        """Generate appropriate loot"""
        loot_context = args.get('context', 'treasure chest')
        value_tier = args.get('value_tier', 'common')
        item_types = args.get('item_types', ['gold', 'consumable'])
        party_level = args.get('party_level')
        auto_distribute = args.get('auto_distribute', False)
        
        session = await self._get_session_for_context(context)
        
        if session and not party_level:
            participants = await self.db.get_session_participants(session['id'])
            if participants:
                levels = [p.get('level', 1) for p in participants if p.get('character_id')]
                party_level = sum(levels) // len(levels) if levels else 1
        
        party_level = party_level or 1
        
        try:
            items_data = await self._load_theme_content(context, 'items.json')
        except Exception:
            items_data = {}
        
        gold_ranges = {
            'poor': (5, 20),
            'common': (20, 100),
            'uncommon': (100, 500),
            'rare': (500, 2000),
            'epic': (2000, 10000),
            'legendary': (10000, 50000)
        }
        
        gold_min, gold_max = gold_ranges.get(value_tier, (20, 100))
        gold_amount = random.randint(gold_min, gold_max) * party_level // 2
        
        lines = [f"💰 **Generated Loot**"]
        lines.append(f"Context: {loot_context}")
        lines.append(f"Tier: {value_tier} | Party Level: {party_level}")
        lines.append(f"\n**Found:**")
        
        generated_items = []
        
        if 'gold' in item_types:
            lines.append(f"  💰 {gold_amount} gold pieces")
            generated_items.append({'type': 'gold', 'amount': gold_amount})
        
        if 'weapon' in item_types:
            weapons = items_data.get('weapons', [{'name': 'Sword', 'damage': '1d8'}])
            weapon = random.choice(weapons) if weapons else {'name': 'Sword', 'damage': '1d8'}
            quality = {'poor': '', 'common': '', 'uncommon': 'Fine ', 'rare': 'Masterwork ', 'epic': 'Enchanted ', 'legendary': 'Legendary '}.get(value_tier, '')
            lines.append(f"  ⚔️ {quality}{weapon.get('name', 'Weapon')} ({weapon.get('damage', '1d6')} damage)")
            generated_items.append({'type': 'weapon', 'name': f"{quality}{weapon.get('name', 'Weapon')}"})
        
        if 'armor' in item_types:
            armors = items_data.get('armor', [{'name': 'Chainmail', 'ac_bonus': 5}])
            armor = random.choice(armors) if armors else {'name': 'Chainmail', 'ac_bonus': 5}
            quality = {'poor': 'Damaged ', 'common': '', 'uncommon': 'Fine ', 'rare': 'Masterwork ', 'epic': 'Enchanted ', 'legendary': 'Legendary '}.get(value_tier, '')
            lines.append(f"  🛡️ {quality}{armor.get('name', 'Armor')} (+{armor.get('ac_bonus', 2)} AC)")
            generated_items.append({'type': 'armor', 'name': f"{quality}{armor.get('name', 'Armor')}"})
        
        if 'consumable' in item_types:
            consumables = ['Health Potion', 'Mana Potion', 'Antidote', 'Scroll of Protection', 'Bomb']
            count = {'poor': 1, 'common': 2, 'uncommon': 3, 'rare': 4, 'epic': 5, 'legendary': 6}.get(value_tier, 2)
            for _ in range(count):
                item = random.choice(consumables)
                lines.append(f"  🧪 {item}")
                generated_items.append({'type': 'consumable', 'name': item})
        
        if 'treasure' in item_types:
            treasures = ['gemstone', 'golden chalice', 'silver necklace', 'ancient coin', 'jeweled ring']
            treasure = random.choice(treasures)
            value = random.randint(gold_min // 2, gold_max // 2)
            lines.append(f"  💎 {treasure.title()} (worth ~{value} gold)")
            generated_items.append({'type': 'treasure', 'name': treasure, 'value': value})
        
        if 'key_item' in item_types:
            lines.append(f"  🔑 **Key Item:** Something important to the story")
            lines.append(f"     *Use create_story_item to define this.*")
        
        if 'junk' in item_types:
            junk = ['broken weapon', 'torn cloth', 'rusty chain', 'empty vial', 'faded letter']
            lines.append(f"  🗑️ {random.choice(junk).title()} (vendor trash)")
        
        if auto_distribute and session:
            lines.append(f"\n*Use give_item and give_gold tools to distribute this loot.*")
        else:
            lines.append(f"\n*Loot ready for distribution. Use inventory tools to give items.*")
        
        return "\n".join(lines)
    
    async def _initialize_campaign(self, context: Dict, args: Dict) -> str:
        """Initialize a complete campaign with world, NPCs, and hooks"""
        campaign_name = args.get('campaign_name', 'New Campaign')
        theme = args.get('theme', 'fantasy adventure')
        tone = args.get('tone', 'mixed')
        starting_scenario = args.get('starting_scenario', '')
        key_npcs_count = args.get('key_npcs_to_generate', 3)
        include_ally = args.get('include_potential_ally', True)
        
        session = await self._get_session_for_context(context)
        guild_id = context.get('guild_id')
        user_id = context.get('user_id')
        
        lines = [f"🎭 **Campaign Initialization: {campaign_name}**"]
        lines.append(f"Theme: {theme}")
        lines.append(f"Tone: {tone}")
        
        if starting_scenario:
            lines.append(f"\n**Starting Scenario:** {starting_scenario}")
        
        lines.append(f"\n📍 **Creating Starting Location...**")
        start_location_result = await self._generate_location(context, {
            'location_type': 'town',
            'theme': theme,
            'purpose': 'Starting area for the campaign',
            'danger_level': 'safe'
        })
        lines.append(start_location_result)
        
        lines.append(f"\n👥 **Creating Key NPCs...**")
        npc_types = ['quest_giver', 'villain', 'mysterious_stranger']
        if include_ally:
            npc_types.insert(0, 'ally')
        
        npc_result = await self._generate_key_npcs(context, {
            'campaign_theme': theme,
            'goals': starting_scenario,
            'npc_types': npc_types[:key_npcs_count],
            'count': key_npcs_count,
            'make_party_members': include_ally
        })
        lines.append(npc_result)
        
        lines.append(f"\n📜 **Creating Initial Quest Hook...**")
        quest_result = await self._generate_quest(context, {
            'quest_type': 'main',
            'difficulty': 'medium',
            'theme': theme,
            'auto_create': True
        })
        lines.append(quest_result)
        
        lines.append(f"\n" + "="*50)
        lines.append(f"✅ **Campaign Ready!**")
        lines.append(f"- Starting location created")
        lines.append(f"- {key_npcs_count} key NPCs generated")
        lines.append(f"- Initial quest hook created")
        if include_ally:
            lines.append(f"- Potential party ally available")
        
        lines.append(f"\n*The stage is set. Let the adventure begin!*")
        
        return "\n".join(lines)
