"""
RPG DM Bot - Tool Schemas
Centralized location for all LLM tool definitions (function calling).
These tools allow the AI DM to manage the game mechanically.
"""

from typing import List, Dict, Any


# =============================================================================
# CHARACTER TOOLS
# =============================================================================

GET_CHARACTER_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_character_info",
        "description": "Get detailed information about a player's character including stats, HP, inventory summary, and active effects.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID. If not provided, uses the active character of the current user."
                },
                "user_id": {
                    "type": "string",
                    "description": "The Discord user ID to get the active character for."
                }
            },
            "required": []
        }
    }
}

UPDATE_CHARACTER_HP_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_character_hp",
        "description": "Modify a character's HP (positive for healing, negative for damage).",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                },
                "hp_change": {
                    "type": "integer",
                    "description": "Amount to change HP (positive = heal, negative = damage)"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the HP change (e.g., 'goblin attack', 'healing potion')"
                }
            },
            "required": ["character_id", "hp_change"]
        }
    }
}

ADD_EXPERIENCE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "add_experience",
        "description": "Award experience points to a character. May trigger level up.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                },
                "xp": {
                    "type": "integer",
                    "description": "Amount of XP to award"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the XP (e.g., 'defeated goblins', 'completed quest')"
                }
            },
            "required": ["character_id", "xp"]
        }
    }
}

UPDATE_CHARACTER_STATS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_character_stats",
        "description": "Modify character stats (strength, dexterity, etc.) or resources (mana).",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                },
                "stat_changes": {
                    "type": "object",
                    "description": "Object with stat names as keys and change amounts as values (e.g., {'mana': -5, 'strength': 1})"
                }
            },
            "required": ["character_id", "stat_changes"]
        }
    }
}


# =============================================================================
# INVENTORY TOOLS
# =============================================================================

GIVE_ITEM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "give_item",
        "description": "Give an item to a character's inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                },
                "item_id": {
                    "type": "string",
                    "description": "Unique identifier for the item (e.g., 'sword_iron', 'potion_health')"
                },
                "item_name": {
                    "type": "string",
                    "description": "Display name of the item"
                },
                "item_type": {
                    "type": "string",
                    "enum": ["weapon", "armor", "accessory", "consumable", "material", "quest", "misc"],
                    "description": "Type of item"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of items to give (default 1)"
                },
                "properties": {
                    "type": "object",
                    "description": "Item properties (e.g., {'damage': '1d8', 'bonus_strength': 2})"
                }
            },
            "required": ["character_id", "item_id", "item_name", "item_type"]
        }
    }
}

REMOVE_ITEM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "remove_item",
        "description": "Remove an item from a character's inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "inventory_id": {
                    "type": "integer",
                    "description": "The inventory entry ID"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number to remove (default 1)"
                }
            },
            "required": ["inventory_id"]
        }
    }
}

GET_INVENTORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_inventory",
        "description": "Get a character's full inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                }
            },
            "required": ["character_id"]
        }
    }
}

GIVE_GOLD_SCHEMA = {
    "type": "function",
    "function": {
        "name": "give_gold",
        "description": "Give gold to a character.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                },
                "amount": {
                    "type": "integer",
                    "description": "Amount of gold to give"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the gold (e.g., 'loot from chest', 'quest reward')"
                }
            },
            "required": ["character_id", "amount"]
        }
    }
}

TAKE_GOLD_SCHEMA = {
    "type": "function",
    "function": {
        "name": "take_gold",
        "description": "Remove gold from a character (for purchases, theft, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                },
                "amount": {
                    "type": "integer",
                    "description": "Amount of gold to remove"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for removal (e.g., 'purchased sword', 'inn stay')"
                }
            },
            "required": ["character_id", "amount"]
        }
    }
}


# =============================================================================
# COMBAT TOOLS
# =============================================================================

START_COMBAT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "start_combat",
        "description": "Initialize a new combat encounter in the current channel.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Brief description of the combat scenario"
                }
            },
            "required": []
        }
    }
}

ADD_ENEMY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "add_enemy",
        "description": "Add an enemy combatant to the current combat.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the enemy (e.g., 'Goblin Warrior', 'Dragon')"
                },
                "hp": {
                    "type": "integer",
                    "description": "Enemy's hit points"
                },
                "initiative_bonus": {
                    "type": "integer",
                    "description": "Bonus to initiative roll (default 0)"
                },
                "stats": {
                    "type": "object",
                    "description": "Enemy stats (e.g., {'ac': 15, 'attack_bonus': 5, 'damage': '1d8+3'})"
                }
            },
            "required": ["name", "hp"]
        }
    }
}

ROLL_INITIATIVE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "roll_initiative",
        "description": "Roll initiative for all combatants and set turn order.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

DEAL_DAMAGE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "deal_damage",
        "description": "Deal damage to a combatant in the current combat.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_id": {
                    "type": "integer",
                    "description": "The combat participant ID to damage"
                },
                "damage": {
                    "type": "integer",
                    "description": "Amount of damage to deal"
                },
                "damage_type": {
                    "type": "string",
                    "description": "Type of damage (e.g., 'slashing', 'fire', 'psychic')"
                }
            },
            "required": ["target_id", "damage"]
        }
    }
}

HEAL_COMBATANT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "heal_combatant",
        "description": "Heal a combatant in the current combat.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_id": {
                    "type": "integer",
                    "description": "The combat participant ID to heal"
                },
                "healing": {
                    "type": "integer",
                    "description": "Amount of HP to restore"
                }
            },
            "required": ["target_id", "healing"]
        }
    }
}

APPLY_STATUS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "apply_status",
        "description": "Apply a status effect to a combatant.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_id": {
                    "type": "integer",
                    "description": "The combat participant ID"
                },
                "effect": {
                    "type": "string",
                    "description": "Status effect name (e.g., 'poisoned', 'stunned', 'blessed')"
                },
                "duration": {
                    "type": "integer",
                    "description": "Duration in rounds (-1 for permanent until removed)"
                }
            },
            "required": ["target_id", "effect"]
        }
    }
}

NEXT_TURN_SCHEMA = {
    "type": "function",
    "function": {
        "name": "next_turn",
        "description": "Advance to the next combatant's turn.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

GET_COMBAT_STATUS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_combat_status",
        "description": "Get the current state of combat (HP, turn order, status effects).",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

END_COMBAT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "end_combat",
        "description": "End the current combat encounter.",
        "parameters": {
            "type": "object",
            "properties": {
                "outcome": {
                    "type": "string",
                    "enum": ["victory", "defeat", "fled", "negotiated"],
                    "description": "How the combat ended"
                },
                "xp_reward": {
                    "type": "integer",
                    "description": "XP to award to each surviving player character"
                }
            },
            "required": []
        }
    }
}


# =============================================================================
# DICE ROLLING TOOLS
# =============================================================================

ROLL_DICE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "roll_dice",
        "description": "Roll dice with optional modifiers. Returns the result.",
        "parameters": {
            "type": "object",
            "properties": {
                "dice": {
                    "type": "string",
                    "description": "Dice expression (e.g., '1d20', '2d6+3', '4d6kh3' for keep highest 3)"
                },
                "purpose": {
                    "type": "string",
                    "description": "What the roll is for (e.g., 'attack roll', 'perception check')"
                },
                "advantage": {
                    "type": "boolean",
                    "description": "Roll with advantage (roll twice, keep higher)"
                },
                "disadvantage": {
                    "type": "boolean",
                    "description": "Roll with disadvantage (roll twice, keep lower)"
                }
            },
            "required": ["dice"]
        }
    }
}

ROLL_ATTACK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "roll_attack",
        "description": "Roll an attack against a target, including hit determination and damage.",
        "parameters": {
            "type": "object",
            "properties": {
                "attacker_id": {
                    "type": "integer",
                    "description": "Combat participant ID of the attacker"
                },
                "target_id": {
                    "type": "integer",
                    "description": "Combat participant ID of the target"
                },
                "attack_bonus": {
                    "type": "integer",
                    "description": "Bonus to add to the attack roll"
                },
                "damage_dice": {
                    "type": "string",
                    "description": "Damage dice expression (e.g., '1d8+3')"
                },
                "damage_type": {
                    "type": "string",
                    "description": "Type of damage"
                }
            },
            "required": ["attacker_id", "target_id", "damage_dice"]
        }
    }
}

ROLL_SAVE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "roll_save",
        "description": "Roll a saving throw for a character.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character making the save"
                },
                "save_type": {
                    "type": "string",
                    "enum": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
                    "description": "Type of saving throw"
                },
                "dc": {
                    "type": "integer",
                    "description": "Difficulty class to beat"
                },
                "reason": {
                    "type": "string",
                    "description": "What the save is against"
                }
            },
            "required": ["character_id", "save_type", "dc"]
        }
    }
}

ROLL_SKILL_CHECK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "roll_skill_check",
        "description": "Roll a skill check for a character.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character making the check"
                },
                "skill": {
                    "type": "string",
                    "description": "Skill name (e.g., 'perception', 'stealth', 'persuasion')"
                },
                "dc": {
                    "type": "integer",
                    "description": "Difficulty class to beat"
                },
                "stat": {
                    "type": "string",
                    "enum": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
                    "description": "Stat to use for the check"
                }
            },
            "required": ["character_id", "skill", "dc", "stat"]
        }
    }
}


# =============================================================================
# QUEST TOOLS
# =============================================================================

CREATE_QUEST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_quest",
        "description": "Create a new quest with objectives and rewards.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Quest title"
                },
                "description": {
                    "type": "string",
                    "description": "Quest description/hook"
                },
                "objectives": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "optional": {"type": "boolean"}
                        }
                    },
                    "description": "List of quest objectives"
                },
                "rewards": {
                    "type": "object",
                    "properties": {
                        "xp": {"type": "integer"},
                        "gold": {"type": "integer"},
                        "items": {"type": "array", "items": {"type": "object"}}
                    },
                    "description": "Rewards for completing the quest"
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard", "deadly"],
                    "description": "Quest difficulty"
                },
                "dm_plan": {
                    "type": "string",
                    "description": "DM's private notes and plan for running this quest"
                }
            },
            "required": ["title", "description", "objectives"]
        }
    }
}

UPDATE_QUEST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_quest",
        "description": "Update an existing quest's details.",
        "parameters": {
            "type": "object",
            "properties": {
                "quest_id": {
                    "type": "integer",
                    "description": "The quest ID to update"
                },
                "title": {"type": "string"},
                "description": {"type": "string"},
                "objectives": {"type": "array", "items": {"type": "object"}},
                "rewards": {"type": "object"},
                "dm_plan": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["available", "active", "completed", "failed"]
                }
            },
            "required": ["quest_id"]
        }
    }
}

COMPLETE_OBJECTIVE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "complete_objective",
        "description": "Mark a quest objective as completed for a character.",
        "parameters": {
            "type": "object",
            "properties": {
                "quest_id": {
                    "type": "integer",
                    "description": "The quest ID"
                },
                "character_id": {
                    "type": "integer",
                    "description": "The character completing the objective"
                },
                "objective_index": {
                    "type": "integer",
                    "description": "Index of the objective to complete (0-based)"
                }
            },
            "required": ["quest_id", "character_id", "objective_index"]
        }
    }
}

GIVE_QUEST_REWARDS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "give_quest_rewards",
        "description": "Mark a quest as complete and distribute rewards to a character.",
        "parameters": {
            "type": "object",
            "properties": {
                "quest_id": {
                    "type": "integer",
                    "description": "The quest ID"
                },
                "character_id": {
                    "type": "integer",
                    "description": "The character receiving rewards"
                }
            },
            "required": ["quest_id", "character_id"]
        }
    }
}

GET_QUESTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_quests",
        "description": "Get available or active quests.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "Get quests for a specific character"
                },
                "status": {
                    "type": "string",
                    "enum": ["available", "active", "completed", "all"],
                    "description": "Filter by quest status"
                }
            },
            "required": []
        }
    }
}


# =============================================================================
# NPC TOOLS
# =============================================================================

GET_NPC_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_npc_info",
        "description": "Get information about an NPC for roleplay purposes.",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {
                    "type": "integer",
                    "description": "The NPC's ID"
                },
                "character_id": {
                    "type": "integer",
                    "description": "The character interacting (to get relationship)"
                }
            },
            "required": ["npc_id"]
        }
    }
}

CREATE_NPC_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_npc",
        "description": "Create a new NPC on the fly.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "NPC's name"
                },
                "description": {
                    "type": "string",
                    "description": "Physical description"
                },
                "personality": {
                    "type": "string",
                    "description": "Personality traits and mannerisms"
                },
                "npc_type": {
                    "type": "string",
                    "enum": ["friendly", "neutral", "hostile", "merchant", "quest_giver"],
                    "description": "NPC disposition"
                },
                "location": {
                    "type": "string",
                    "description": "Where the NPC is found"
                },
                "is_merchant": {
                    "type": "boolean",
                    "description": "Whether the NPC sells items"
                },
                "merchant_inventory": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Items for sale if merchant"
                }
            },
            "required": ["name", "description", "personality"]
        }
    }
}

UPDATE_NPC_RELATIONSHIP_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_npc_relationship",
        "description": "Change the relationship between an NPC and character.",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {
                    "type": "integer",
                    "description": "The NPC's ID"
                },
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                },
                "reputation_change": {
                    "type": "integer",
                    "description": "Amount to change reputation (positive or negative)"
                },
                "notes": {
                    "type": "string",
                    "description": "Notes about the interaction"
                }
            },
            "required": ["npc_id", "character_id", "reputation_change"]
        }
    }
}

GET_NPCS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_npcs",
        "description": "Get NPCs, optionally filtered by location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Filter NPCs by location"
                }
            },
            "required": []
        }
    }
}


# =============================================================================
# SESSION/PARTY TOOLS
# =============================================================================

GET_PARTY_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_party_info",
        "description": "Get information about all party members in the current session.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

ADD_STORY_ENTRY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "add_story_entry",
        "description": "Add an entry to the campaign's story log.",
        "parameters": {
            "type": "object",
            "properties": {
                "entry_type": {
                    "type": "string",
                    "enum": ["narration", "combat", "dialogue", "discovery", "milestone"],
                    "description": "Type of story entry"
                },
                "content": {
                    "type": "string",
                    "description": "The story content to log"
                }
            },
            "required": ["entry_type", "content"]
        }
    }
}

GET_STORY_LOG_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_story_log",
        "description": "Get recent entries from the campaign's story log.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of entries to retrieve (default 10)"
                }
            },
            "required": []
        }
    }
}


# =============================================================================
# MEMORY TOOLS
# =============================================================================

SAVE_MEMORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "save_memory",
        "description": "Save a memory about a player for future reference.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Memory key (e.g., 'preferred_playstyle', 'character_goals')"
                },
                "value": {
                    "type": "string",
                    "description": "The memory content"
                },
                "context": {
                    "type": "string",
                    "description": "Context about when/why this was noted"
                }
            },
            "required": ["key", "value"]
        }
    }
}

GET_PLAYER_MEMORIES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_player_memories",
        "description": "Get all memories stored about a player.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The Discord user ID (optional, defaults to current user)"
                }
            },
            "required": []
        }
    }
}


# =============================================================================
# COLLECT ALL SCHEMAS
# =============================================================================

TOOLS_SCHEMA = [
    # Character
    GET_CHARACTER_INFO_SCHEMA,
    UPDATE_CHARACTER_HP_SCHEMA,
    ADD_EXPERIENCE_SCHEMA,
    UPDATE_CHARACTER_STATS_SCHEMA,
    # Inventory
    GIVE_ITEM_SCHEMA,
    REMOVE_ITEM_SCHEMA,
    GET_INVENTORY_SCHEMA,
    GIVE_GOLD_SCHEMA,
    TAKE_GOLD_SCHEMA,
    # Combat
    START_COMBAT_SCHEMA,
    ADD_ENEMY_SCHEMA,
    ROLL_INITIATIVE_SCHEMA,
    DEAL_DAMAGE_SCHEMA,
    HEAL_COMBATANT_SCHEMA,
    APPLY_STATUS_SCHEMA,
    NEXT_TURN_SCHEMA,
    GET_COMBAT_STATUS_SCHEMA,
    END_COMBAT_SCHEMA,
    # Dice
    ROLL_DICE_SCHEMA,
    ROLL_ATTACK_SCHEMA,
    ROLL_SAVE_SCHEMA,
    ROLL_SKILL_CHECK_SCHEMA,
    # Quest
    CREATE_QUEST_SCHEMA,
    UPDATE_QUEST_SCHEMA,
    COMPLETE_OBJECTIVE_SCHEMA,
    GIVE_QUEST_REWARDS_SCHEMA,
    GET_QUESTS_SCHEMA,
    # NPC
    GET_NPC_INFO_SCHEMA,
    CREATE_NPC_SCHEMA,
    UPDATE_NPC_RELATIONSHIP_SCHEMA,
    GET_NPCS_SCHEMA,
    # Session
    GET_PARTY_INFO_SCHEMA,
    ADD_STORY_ENTRY_SCHEMA,
    GET_STORY_LOG_SCHEMA,
    # Memory
    SAVE_MEMORY_SCHEMA,
    GET_PLAYER_MEMORIES_SCHEMA,
]


def get_tool_names() -> list[str]:
    """Get list of all tool names"""
    return [tool["function"]["name"] for tool in TOOLS_SCHEMA]


class ToolSchemas:
    """Convenient class for accessing tool schemas"""
    
    def __init__(self):
        self.all_schemas = TOOLS_SCHEMA
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for LLM function calling"""
        return self.all_schemas
    
    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        return get_tool_names()
    
    def get_schema_by_name(self, name: str) -> Dict[str, Any]:
        """Get a specific tool schema by name"""
        for schema in self.all_schemas:
            if schema["function"]["name"] == name:
                return schema
        return None
    
    def get_schemas_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tool schemas by category (character, combat, inventory, etc.)"""
        categories = {
            "character": [GET_CHARACTER_INFO_SCHEMA, UPDATE_CHARACTER_HP_SCHEMA, 
                         ADD_EXPERIENCE_SCHEMA, UPDATE_CHARACTER_STATS_SCHEMA],
            "inventory": [GIVE_ITEM_SCHEMA, REMOVE_ITEM_SCHEMA, GET_INVENTORY_SCHEMA,
                         GIVE_GOLD_SCHEMA, TAKE_GOLD_SCHEMA],
            "combat": [START_COMBAT_SCHEMA, ADD_ENEMY_SCHEMA, ROLL_INITIATIVE_SCHEMA,
                      DEAL_DAMAGE_SCHEMA, HEAL_COMBATANT_SCHEMA, APPLY_STATUS_SCHEMA,
                      NEXT_TURN_SCHEMA, GET_COMBAT_STATUS_SCHEMA, END_COMBAT_SCHEMA],
            "dice": [ROLL_DICE_SCHEMA, ROLL_ATTACK_SCHEMA, ROLL_SAVE_SCHEMA, 
                    ROLL_SKILL_CHECK_SCHEMA],
            "quest": [CREATE_QUEST_SCHEMA, UPDATE_QUEST_SCHEMA, COMPLETE_OBJECTIVE_SCHEMA,
                     GIVE_QUEST_REWARDS_SCHEMA, GET_QUESTS_SCHEMA],
            "npc": [GET_NPC_INFO_SCHEMA, CREATE_NPC_SCHEMA, UPDATE_NPC_RELATIONSHIP_SCHEMA,
                   GET_NPCS_SCHEMA],
            "session": [GET_PARTY_INFO_SCHEMA, ADD_STORY_ENTRY_SCHEMA, GET_STORY_LOG_SCHEMA],
            "memory": [SAVE_MEMORY_SCHEMA, GET_PLAYER_MEMORIES_SCHEMA]
        }
        return categories.get(category.lower(), [])
