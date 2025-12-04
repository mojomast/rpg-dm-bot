"""
RPG DM Bot - Tool Executor
Handles execution of LLM tool calls for game mechanics.
"""

import random
import re
from typing import List, Dict, Any
import json
import logging

from src.tool_schemas import TOOLS_SCHEMA, get_tool_names

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
    
    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any], 
                          context: Dict[str, Any]) -> str:
        """Execute a tool by name with arguments"""
        logger.info(f"Executing tool {tool_name} with args {tool_args}")
        
        try:
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
            char = await self.db.get_active_character(user_id, guild_id)
        
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
    
    async def _start_combat(self, context: Dict, args: Dict) -> str:
        """Start a combat encounter"""
        guild_id = context.get('guild_id')
        channel_id = context.get('channel_id')
        session_id = context.get('session_id')
        description = args.get('description', 'Combat begins!')
        
        # Check for existing combat
        existing = await self.db.get_active_combat(channel_id)
        if existing:
            return "Error: Combat already active in this channel. End it first with end_combat."
        
        encounter_id = await self.db.create_combat(guild_id, channel_id, session_id)
        
        # Add all party members to combat
        session = await self.db.get_active_session(guild_id)
        if session:
            participants = await self.db.get_session_participants(session['id'])
            for p in participants:
                if p.get('character_id'):
                    char = await self.db.get_character(p['character_id'])
                    if char:
                        dex_mod = (char['dexterity'] - 10) // 2
                        await self.db.add_combatant(
                            encounter_id, 'character', char['id'], char['name'],
                            char['hp'], char['max_hp'], dex_mod, is_player=True
                        )
        
        return f"⚔️ Combat started! (Encounter #{encounter_id})\n{description}\nUse add_enemy to add enemies, then roll_initiative to begin."
    
    async def _add_enemy(self, context: Dict, args: Dict) -> str:
        """Add enemy to combat"""
        channel_id = context.get('channel_id')
        name = args.get('name')
        hp = args.get('hp')
        init_bonus = args.get('initiative_bonus', 0)
        stats = args.get('stats', {})
        
        combat = await self.db.get_active_combat(channel_id)
        if not combat:
            return "Error: No active combat. Start combat first."
        
        combatant_id = await self.db.add_combatant(
            combat['id'], 'enemy', 0, name, hp, hp, init_bonus, is_player=False
        )
        
        return f"Added {name} to combat (HP: {hp}, ID: {combatant_id})"
    
    async def _roll_initiative(self, context: Dict) -> str:
        """Roll initiative for all combatants"""
        channel_id = context.get('channel_id')
        
        combat = await self.db.get_active_combat(channel_id)
        if not combat:
            return "Error: No active combat."
        
        combatants = await self.db.get_combatants(combat['id'])
        results = []
        
        for c in combatants:
            roll = self.dice.roll(f"1d20+{c['initiative']}")
            # Update initiative in database
            async with self.db.db_path as conn:
                pass  # Would update here
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
        
        combat = await self.db.get_active_combat(channel_id)
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
        
        combat = await self.db.get_active_combat(channel_id)
        if not combat:
            return "No active combat."
        
        combatants = await self.db.get_combatants(combat['id'])
        
        lines = [f"**Combat Status** (Round {combat['round_number']})"]
        for c in combatants:
            hp_bar = "█" * int(c['current_hp'] / c['max_hp'] * 10) + "░" * (10 - int(c['current_hp'] / c['max_hp'] * 10))
            status = " ".join([f"[{e['effect']}]" for e in c['status_effects']])
            dead = "💀" if c['current_hp'] <= 0 else ""
            marker = "🎮" if c['is_player'] else "👹"
            lines.append(f"{dead}{marker} {c['name']}: {hp_bar} {c['current_hp']}/{c['max_hp']} {status}")
        
        return "\n".join(lines)
    
    async def _end_combat(self, context: Dict, args: Dict) -> str:
        """End combat encounter"""
        channel_id = context.get('channel_id')
        outcome = args.get('outcome', 'victory')
        xp_reward = args.get('xp_reward', 0)
        
        combat = await self.db.get_active_combat(channel_id)
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
        char = await self.db.get_active_character(user_id, guild_id)
        
        await self.db.log_dice_roll(
            user_id, guild_id, 'general', dice, result['rolls'],
            result['modifier'], result['total'],
            char['id'] if char else None, purpose
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
        combat = await self.db.get_active_combat(channel_id)
        if not combat:
            return "Error: No active combat for attack roll."
        
        combatants = await self.db.get_combatants(combat['id'])
        attacker = next((c for c in combatants if c['id'] == attacker_id), None)
        target = next((c for c in combatants if c['id'] == target_id), None)
        
        if not attacker or not target:
            return "Error: Invalid attacker or target."
        
        # Roll to hit
        attack_roll = self.dice.roll(f"1d20+{attack_bonus}")
        target_ac = 10  # Default AC, could be stored in stats
        
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
        session = await self.db.get_active_session(guild_id)
        
        quest_id = await self.db.create_quest(
            guild_id=guild_id,
            title=args.get('title'),
            description=args.get('description'),
            objectives=args.get('objectives', []),
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
        session = await self.db.get_active_session(guild_id)
        
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
        guild_id = context.get('guild_id')
        session = await self.db.get_active_session(guild_id)
        
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
        guild_id = context.get('guild_id')
        session = await self.db.get_active_session(guild_id)
        
        if not session:
            return "No active session to log story."
        
        entry_type = args.get('entry_type', 'narration')
        content = args.get('content')
        
        await self.db.add_story_entry(session['id'], entry_type, content)
        return f"📖 Story logged: [{entry_type}]"
    
    async def _get_story_log(self, context: Dict, args: Dict) -> str:
        """Get story log"""
        guild_id = context.get('guild_id')
        session = await self.db.get_active_session(guild_id)
        
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
        import json
        import os
        
        char_id = args.get('character_id')
        spell_id = args.get('spell_id')
        slot_level = args.get('slot_level')
        target = args.get('target', 'target')
        
        if not char_id or not spell_id:
            return "Error: character_id and spell_id required"
        
        # Load spell data
        spells_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'game_data', 'spells.json')
        try:
            with open(spells_file, 'r', encoding='utf-8') as f:
                spells_data = json.load(f)
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
                    damage_dice = f"{damage_dice}+{upcast_levels}d{match.group(1)}"
            
            roll_result = self.dice.roll(damage_dice)
            damage_type = spell.get('damage_type', 'magical')
            result_parts.append(f"💥 **{roll_result['total']}** {damage_type} damage!")
            result_parts.append(f"🎲 Rolled {damage_dice}: {roll_result['rolls']}")
            
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
                    healing_dice = f"{healing_dice}+{upcast_levels}d{match.group(1)}"
            
            roll_result = self.dice.roll(healing_dice)
            result_parts.append(f"💚 **{roll_result['total']}** HP healed!")
            result_parts.append(f"🎲 Rolled {healing_dice}: {roll_result['rolls']}")
        
        # Handle effects
        elif spell.get('effect'):
            result_parts.append(f"✨ Effect: {spell['effect']}")
        
        # Show spell description snippet
        if spell.get('description'):
            result_parts.append(f"*{spell['description'][:150]}...*" if len(spell.get('description', '')) > 150 else f"*{spell['description']}*")
        
        return "\n".join(result_parts)
    
    async def _use_ability(self, args: Dict) -> str:
        """Use a class ability"""
        import json
        import os
        
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
        classes_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'game_data', 'classes.json')
        try:
            with open(classes_file, 'r', encoding='utf-8') as f:
                classes_data = json.load(f)
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
