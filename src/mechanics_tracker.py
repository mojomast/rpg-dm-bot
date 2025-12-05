"""
RPG DM Bot - Mechanics Tracker
Tracks dice rolls, skill checks, combat actions, and other game mechanics
for styled display in Discord messages.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class MechanicType(Enum):
    DICE_ROLL = "dice_roll"
    SKILL_CHECK = "skill_check"
    SAVING_THROW = "saving_throw"
    ATTACK_ROLL = "attack_roll"
    DAMAGE_ROLL = "damage_roll"
    ITEM_GAINED = "item_gained"
    ITEM_LOST = "item_lost"
    GOLD_CHANGE = "gold_change"
    XP_GAINED = "xp_gained"
    LEVEL_UP = "level_up"
    HP_CHANGE = "hp_change"
    STATUS_EFFECT = "status_effect"
    QUEST_UPDATE = "quest_update"
    LOCATION_CHANGE = "location_change"
    NPC_INTERACTION = "npc_interaction"


@dataclass
class GameMechanic:
    """A single game mechanic event"""
    type: MechanicType
    character_name: str
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    success: Optional[bool] = None
    
    def to_discord_format(self) -> str:
        """Format this mechanic for Discord display"""
        if self.type == MechanicType.DICE_ROLL:
            return self._format_dice_roll()
        elif self.type == MechanicType.SKILL_CHECK:
            return self._format_skill_check()
        elif self.type == MechanicType.SAVING_THROW:
            return self._format_saving_throw()
        elif self.type == MechanicType.ATTACK_ROLL:
            return self._format_attack_roll()
        elif self.type == MechanicType.DAMAGE_ROLL:
            return self._format_damage_roll()
        elif self.type == MechanicType.ITEM_GAINED:
            return self._format_item_gained()
        elif self.type == MechanicType.ITEM_LOST:
            return self._format_item_lost()
        elif self.type == MechanicType.GOLD_CHANGE:
            return self._format_gold_change()
        elif self.type == MechanicType.XP_GAINED:
            return self._format_xp_gained()
        elif self.type == MechanicType.LEVEL_UP:
            return self._format_level_up()
        elif self.type == MechanicType.HP_CHANGE:
            return self._format_hp_change()
        elif self.type == MechanicType.STATUS_EFFECT:
            return self._format_status_effect()
        elif self.type == MechanicType.QUEST_UPDATE:
            return self._format_quest_update()
        elif self.type == MechanicType.LOCATION_CHANGE:
            return self._format_location_change()
        elif self.type == MechanicType.NPC_INTERACTION:
            return self._format_npc_interaction()
        return self.description
    
    def _format_dice_roll(self) -> str:
        dice = self.details.get('dice', '?')
        rolls = self.details.get('rolls', [])
        modifier = self.details.get('modifier', 0)
        total = self.details.get('total', 0)
        is_crit = self.details.get('critical', False)
        is_fumble = self.details.get('fumble', False)
        
        rolls_str = ', '.join(str(r) for r in rolls) if rolls else '?'
        mod_str = f" + {modifier}" if modifier > 0 else f" - {abs(modifier)}" if modifier < 0 else ""
        
        result = f"🎲 **{self.character_name}** rolled `{dice}`: [{rolls_str}]{mod_str} = **{total}**"
        if is_crit:
            result += " 💥 **CRITICAL!**"
        elif is_fumble:
            result += " 💀 **FUMBLE!**"
        return result
    
    def _format_skill_check(self) -> str:
        skill = self.details.get('skill', 'Unknown')
        stat = self.details.get('stat', '')
        dc = self.details.get('dc', 0)
        roll = self.details.get('roll', 0)
        modifier = self.details.get('modifier', 0)
        total = self.details.get('total', 0)
        is_crit = self.details.get('critical', False)
        is_fumble = self.details.get('fumble', False)
        
        stat_str = f" ({stat.upper()})" if stat else ""
        mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)
        
        result_icon = "✅" if self.success else "❌"
        result_text = "SUCCESS" if self.success else "FAILED"
        
        line = f"🎯 **{skill.title()} Check{stat_str}** — {self.character_name}\n"
        line += f"   `d20` [{roll}] {mod_str} = **{total}** vs DC **{dc}** → {result_icon} {result_text}"
        
        if is_crit:
            line += " 💥"
        elif is_fumble:
            line += " 💀"
        
        return line
    
    def _format_saving_throw(self) -> str:
        save_type = self.details.get('save_type', 'Unknown')
        dc = self.details.get('dc', 0)
        roll = self.details.get('roll', 0)
        modifier = self.details.get('modifier', 0)
        total = self.details.get('total', 0)
        reason = self.details.get('reason', '')
        
        mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)
        result_icon = "✅" if self.success else "❌"
        result_text = "SAVED" if self.success else "FAILED"
        reason_str = f" ({reason})" if reason else ""
        
        line = f"🛡️ **{save_type.upper()} Save{reason_str}** — {self.character_name}\n"
        line += f"   `d20` [{roll}] {mod_str} = **{total}** vs DC **{dc}** → {result_icon} {result_text}"
        
        return line
    
    def _format_attack_roll(self) -> str:
        target = self.details.get('target', 'Unknown')
        weapon = self.details.get('weapon', 'attack')
        ac = self.details.get('ac', 0)
        roll = self.details.get('roll', 0)
        modifier = self.details.get('modifier', 0)
        total = self.details.get('total', 0)
        is_crit = self.details.get('critical', False)
        is_fumble = self.details.get('fumble', False)
        
        mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)
        result_icon = "⚔️" if self.success else "🛡️"
        result_text = "HIT" if self.success else "MISS"
        
        if is_crit:
            result_text = "CRITICAL HIT"
            result_icon = "💥"
        elif is_fumble:
            result_text = "CRITICAL MISS"
            result_icon = "💀"
        
        line = f"⚔️ **Attack Roll** — {self.character_name} → {target}\n"
        line += f"   `d20` [{roll}] {mod_str} = **{total}** vs AC **{ac}** → {result_icon} **{result_text}**"
        
        return line
    
    def _format_damage_roll(self) -> str:
        damage = self.details.get('damage', 0)
        damage_type = self.details.get('damage_type', 'damage')
        target = self.details.get('target', 'Unknown')
        dice = self.details.get('dice', '')
        rolls = self.details.get('rolls', [])
        is_crit = self.details.get('critical', False)
        
        rolls_str = f" [{', '.join(str(r) for r in rolls)}]" if rolls else ""
        crit_str = " (×2 CRIT!)" if is_crit else ""
        
        line = f"💢 **{damage} {damage_type} damage** to {target}{crit_str}"
        if dice:
            line += f"\n   `{dice}`{rolls_str}"
        
        return line
    
    def _format_item_gained(self) -> str:
        item_name = self.details.get('item_name', 'Unknown Item')
        quantity = self.details.get('quantity', 1)
        qty_str = f" ×{quantity}" if quantity > 1 else ""
        return f"📦 **{self.character_name}** obtained: **{item_name}**{qty_str}"
    
    def _format_item_lost(self) -> str:
        item_name = self.details.get('item_name', 'Unknown Item')
        quantity = self.details.get('quantity', 1)
        qty_str = f" ×{quantity}" if quantity > 1 else ""
        return f"📤 **{self.character_name}** lost: **{item_name}**{qty_str}"
    
    def _format_gold_change(self) -> str:
        amount = self.details.get('amount', 0)
        new_total = self.details.get('new_total', 0)
        if amount >= 0:
            return f"💰 **{self.character_name}** gained **{amount} gold** (Total: {new_total})"
        else:
            return f"💸 **{self.character_name}** spent **{abs(amount)} gold** (Total: {new_total})"
    
    def _format_xp_gained(self) -> str:
        xp = self.details.get('xp', 0)
        new_total = self.details.get('new_total', 0)
        source = self.details.get('source', '')
        source_str = f" from {source}" if source else ""
        return f"⭐ **{self.character_name}** gained **{xp} XP**{source_str} (Total: {new_total})"
    
    def _format_level_up(self) -> str:
        new_level = self.details.get('new_level', 0)
        return f"🎉 **LEVEL UP!** {self.character_name} is now **Level {new_level}**!"
    
    def _format_hp_change(self) -> str:
        amount = self.details.get('amount', 0)
        current_hp = self.details.get('current_hp', 0)
        max_hp = self.details.get('max_hp', 0)
        source = self.details.get('source', '')
        
        if amount >= 0:
            return f"💚 **{self.character_name}** healed **{amount} HP** ({current_hp}/{max_hp})"
        else:
            source_str = f" from {source}" if source else ""
            return f"💔 **{self.character_name}** took **{abs(amount)} damage**{source_str} ({current_hp}/{max_hp})"
    
    def _format_status_effect(self) -> str:
        effect = self.details.get('effect', 'Unknown')
        action = self.details.get('action', 'applied')  # 'applied' or 'removed'
        duration = self.details.get('duration', 0)
        
        if action == 'applied':
            dur_str = f" for {duration} rounds" if duration else ""
            return f"✨ **{self.character_name}** gained status: **{effect}**{dur_str}"
        else:
            return f"🔄 **{self.character_name}** lost status: **{effect}**"
    
    def _format_quest_update(self) -> str:
        quest_name = self.details.get('quest_name', 'Unknown Quest')
        update_type = self.details.get('update_type', 'progress')
        
        if update_type == 'started':
            return f"📜 **New Quest Started:** {quest_name}"
        elif update_type == 'completed':
            return f"🏆 **Quest Completed:** {quest_name}"
        elif update_type == 'objective':
            objective = self.details.get('objective', '')
            return f"✅ **Objective Complete:** {objective}"
        else:
            return f"📋 **Quest Update:** {quest_name}"
    
    def _format_location_change(self) -> str:
        new_location = self.details.get('new_location', 'Unknown')
        return f"🗺️ **{self.character_name}** moved to: **{new_location}**"
    
    def _format_npc_interaction(self) -> str:
        npc_name = self.details.get('npc_name', 'Unknown')
        interaction = self.details.get('interaction', 'interacted with')
        return f"👤 **{self.character_name}** {interaction} **{npc_name}**"


class MechanicsTracker:
    """Tracks game mechanics during a response generation for display"""
    
    def __init__(self):
        self.mechanics: List[GameMechanic] = []
    
    def clear(self):
        """Clear all tracked mechanics"""
        self.mechanics = []
    
    def add(self, mechanic: GameMechanic):
        """Add a mechanic to track"""
        self.mechanics.append(mechanic)
    
    def add_dice_roll(self, character_name: str, dice: str, rolls: List[int], 
                      modifier: int = 0, total: int = 0, critical: bool = False, 
                      fumble: bool = False):
        """Track a dice roll"""
        self.add(GameMechanic(
            type=MechanicType.DICE_ROLL,
            character_name=character_name,
            description=f"{character_name} rolled {dice}",
            details={
                'dice': dice,
                'rolls': rolls,
                'modifier': modifier,
                'total': total,
                'critical': critical,
                'fumble': fumble
            }
        ))
    
    def add_skill_check(self, character_name: str, skill: str, stat: str, dc: int,
                        roll: int, modifier: int, total: int, success: bool,
                        critical: bool = False, fumble: bool = False):
        """Track a skill check"""
        self.add(GameMechanic(
            type=MechanicType.SKILL_CHECK,
            character_name=character_name,
            description=f"{character_name} {skill} check",
            success=success,
            details={
                'skill': skill,
                'stat': stat,
                'dc': dc,
                'roll': roll,
                'modifier': modifier,
                'total': total,
                'critical': critical,
                'fumble': fumble
            }
        ))
    
    def add_saving_throw(self, character_name: str, save_type: str, dc: int,
                         roll: int, modifier: int, total: int, success: bool,
                         reason: str = ""):
        """Track a saving throw"""
        self.add(GameMechanic(
            type=MechanicType.SAVING_THROW,
            character_name=character_name,
            description=f"{character_name} {save_type} save",
            success=success,
            details={
                'save_type': save_type,
                'dc': dc,
                'roll': roll,
                'modifier': modifier,
                'total': total,
                'reason': reason
            }
        ))
    
    def add_attack(self, character_name: str, target: str, weapon: str, ac: int,
                   roll: int, modifier: int, total: int, hit: bool,
                   critical: bool = False, fumble: bool = False):
        """Track an attack roll"""
        self.add(GameMechanic(
            type=MechanicType.ATTACK_ROLL,
            character_name=character_name,
            description=f"{character_name} attacks {target}",
            success=hit,
            details={
                'target': target,
                'weapon': weapon,
                'ac': ac,
                'roll': roll,
                'modifier': modifier,
                'total': total,
                'critical': critical,
                'fumble': fumble
            }
        ))
    
    def add_damage(self, character_name: str, target: str, damage: int, 
                   damage_type: str = "damage", dice: str = "", rolls: List[int] = None,
                   critical: bool = False):
        """Track damage dealt"""
        self.add(GameMechanic(
            type=MechanicType.DAMAGE_ROLL,
            character_name=character_name,
            description=f"{damage} damage to {target}",
            details={
                'damage': damage,
                'damage_type': damage_type,
                'target': target,
                'dice': dice,
                'rolls': rolls or [],
                'critical': critical
            }
        ))
    
    def add_item_gained(self, character_name: str, item_name: str, quantity: int = 1):
        """Track item obtained"""
        self.add(GameMechanic(
            type=MechanicType.ITEM_GAINED,
            character_name=character_name,
            description=f"{character_name} gained {item_name}",
            details={'item_name': item_name, 'quantity': quantity}
        ))
    
    def add_item_lost(self, character_name: str, item_name: str, quantity: int = 1):
        """Track item lost/used"""
        self.add(GameMechanic(
            type=MechanicType.ITEM_LOST,
            character_name=character_name,
            description=f"{character_name} lost {item_name}",
            details={'item_name': item_name, 'quantity': quantity}
        ))
    
    def add_gold_change(self, character_name: str, amount: int, new_total: int):
        """Track gold gained/spent"""
        self.add(GameMechanic(
            type=MechanicType.GOLD_CHANGE,
            character_name=character_name,
            description=f"{character_name} {'gained' if amount >= 0 else 'spent'} {abs(amount)} gold",
            details={'amount': amount, 'new_total': new_total}
        ))
    
    def add_xp_gained(self, character_name: str, xp: int, new_total: int, source: str = ""):
        """Track XP gained"""
        self.add(GameMechanic(
            type=MechanicType.XP_GAINED,
            character_name=character_name,
            description=f"{character_name} gained {xp} XP",
            details={'xp': xp, 'new_total': new_total, 'source': source}
        ))
    
    def add_level_up(self, character_name: str, new_level: int):
        """Track level up"""
        self.add(GameMechanic(
            type=MechanicType.LEVEL_UP,
            character_name=character_name,
            description=f"{character_name} reached level {new_level}",
            details={'new_level': new_level}
        ))
    
    def add_hp_change(self, character_name: str, amount: int, current_hp: int, 
                      max_hp: int, source: str = ""):
        """Track HP change (healing or damage)"""
        self.add(GameMechanic(
            type=MechanicType.HP_CHANGE,
            character_name=character_name,
            description=f"{character_name} HP changed by {amount}",
            details={
                'amount': amount,
                'current_hp': current_hp,
                'max_hp': max_hp,
                'source': source
            }
        ))
    
    def add_status_effect(self, character_name: str, effect: str, 
                          action: str = 'applied', duration: int = 0):
        """Track status effect applied/removed"""
        self.add(GameMechanic(
            type=MechanicType.STATUS_EFFECT,
            character_name=character_name,
            description=f"{effect} {action} to {character_name}",
            details={'effect': effect, 'action': action, 'duration': duration}
        ))
    
    def add_quest_update(self, character_name: str, quest_name: str, 
                         update_type: str, objective: str = ""):
        """Track quest updates"""
        self.add(GameMechanic(
            type=MechanicType.QUEST_UPDATE,
            character_name=character_name,
            description=f"Quest update: {quest_name}",
            details={
                'quest_name': quest_name,
                'update_type': update_type,
                'objective': objective
            }
        ))
    
    def add_location_change(self, character_name: str, new_location: str):
        """Track location change"""
        self.add(GameMechanic(
            type=MechanicType.LOCATION_CHANGE,
            character_name=character_name,
            description=f"{character_name} moved to {new_location}",
            details={'new_location': new_location}
        ))
    
    def format_all(self) -> str:
        """Format all tracked mechanics into a styled Discord block"""
        if not self.mechanics:
            return ""
        
        lines = []
        lines.append("```ansi")
        lines.append("\u001b[1;33m━━━━━━━━━━ GAME MECHANICS ━━━━━━━━━━\u001b[0m")
        lines.append("```")
        
        for mechanic in self.mechanics:
            lines.append(mechanic.to_discord_format())
        
        lines.append("")  # Empty line for spacing
        
        return "\n".join(lines)
    
    def format_compact(self) -> str:
        """Format mechanics in a more compact style"""
        if not self.mechanics:
            return ""
        
        lines = ["**⚙️ Mechanics:**"]
        for mechanic in self.mechanics:
            lines.append(f"  • {mechanic.to_discord_format()}")
        
        return "\n".join(lines)
    
    def has_mechanics(self) -> bool:
        """Check if any mechanics were tracked"""
        return len(self.mechanics) > 0
    
    def to_dict(self) -> List[Dict]:
        """Export mechanics as a list of dicts"""
        return [
            {
                'type': m.type.value,
                'character': m.character_name,
                'description': m.description,
                'success': m.success,
                'details': m.details
            }
            for m in self.mechanics
        ]


# Global tracker instance (will be reset per message processing)
_current_tracker: Optional[MechanicsTracker] = None


def get_tracker() -> MechanicsTracker:
    """Get the current mechanics tracker"""
    global _current_tracker
    if _current_tracker is None:
        _current_tracker = MechanicsTracker()
    return _current_tracker


def new_tracker() -> MechanicsTracker:
    """Create a new mechanics tracker and set it as current"""
    global _current_tracker
    _current_tracker = MechanicsTracker()
    return _current_tracker


def clear_tracker():
    """Clear the current tracker"""
    global _current_tracker
    if _current_tracker:
        _current_tracker.clear()
