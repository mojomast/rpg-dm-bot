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
# SPELL & ABILITY TOOLS
# =============================================================================

GET_CHARACTER_SPELLS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_character_spells",
        "description": "Get all spells known by a character, including cantrips and spell slots.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                },
                "prepared_only": {
                    "type": "boolean",
                    "description": "If true, only return prepared spells"
                }
            },
            "required": ["character_id"]
        }
    }
}

CAST_SPELL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "cast_spell",
        "description": "Cast a spell for a character. Handles spell slot usage, damage/healing rolls, and effects.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character casting the spell"
                },
                "spell_id": {
                    "type": "string",
                    "description": "The ID of the spell to cast (e.g., 'fireball', 'cure_wounds')"
                },
                "slot_level": {
                    "type": "integer",
                    "description": "The spell slot level to use (not needed for cantrips)"
                },
                "target": {
                    "type": "string",
                    "description": "Target of the spell (creature name, character name, or 'self')"
                }
            },
            "required": ["character_id", "spell_id"]
        }
    }
}

USE_ABILITY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "use_ability",
        "description": "Use a class ability or feature for a character. Tracks limited uses.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character using the ability"
                },
                "ability_id": {
                    "type": "string",
                    "description": "The ID of the ability (e.g., 'second_wind', 'action_surge', 'sneak_attack')"
                },
                "target": {
                    "type": "string",
                    "description": "Target of the ability if applicable"
                }
            },
            "required": ["character_id", "ability_id"]
        }
    }
}

GET_CHARACTER_ABILITIES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_character_abilities",
        "description": "Get all class abilities and features for a character.",
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

REST_CHARACTER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "rest_character",
        "description": "Have a character take a short or long rest to recover resources.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                },
                "rest_type": {
                    "type": "string",
                    "enum": ["short", "long"],
                    "description": "Type of rest - short (1 hour) or long (8 hours)"
                }
            },
            "required": ["character_id", "rest_type"]
        }
    }
}


# =============================================================================
# LOCATION TOOLS
# =============================================================================

CREATE_LOCATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_location",
        "description": "Create a new location in the world (town, dungeon, wilderness, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the location"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the location"
                },
                "location_type": {
                    "type": "string",
                    "enum": ["town", "city", "village", "dungeon", "wilderness", "landmark", "interior", "road", "generic"],
                    "description": "Type of location"
                },
                "points_of_interest": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Notable features or areas within this location"
                },
                "current_weather": {
                    "type": "string",
                    "description": "Current weather at the location"
                },
                "danger_level": {
                    "type": "integer",
                    "description": "Danger level 0-10 (0=safe, 10=deadly)"
                },
                "hidden_secrets": {
                    "type": "string",
                    "description": "DM-only notes about secrets at this location"
                }
            },
            "required": ["name", "description"]
        }
    }
}

GET_LOCATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_location",
        "description": "Get details about a specific location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "The location's ID"
                }
            },
            "required": ["location_id"]
        }
    }
}

GET_NEARBY_LOCATIONS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_nearby_locations",
        "description": "Get locations connected to the current location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "The location's ID to find connections from"
                }
            },
            "required": ["location_id"]
        }
    }
}

UPDATE_LOCATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_location",
        "description": "Update a location's properties (weather, NPCs present, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "The location's ID"
                },
                "description": {"type": "string"},
                "current_weather": {"type": "string"},
                "danger_level": {"type": "integer"},
                "points_of_interest": {"type": "array", "items": {"type": "string"}},
                "hidden_secrets": {"type": "string"}
            },
            "required": ["location_id"]
        }
    }
}

MOVE_PARTY_TO_LOCATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "move_party_to_location",
        "description": "Move the party to a new location, updating the game state.",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "The destination location's ID"
                },
                "travel_description": {
                    "type": "string",
                    "description": "Optional description of the journey"
                }
            },
            "required": ["location_id"]
        }
    }
}


# =============================================================================
# STORY ITEM TOOLS
# =============================================================================

CREATE_STORY_ITEM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_story_item",
        "description": "Create a narrative-important item (artifact, clue, key, letter, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the story item"
                },
                "description": {
                    "type": "string",
                    "description": "Physical description of the item"
                },
                "item_type": {
                    "type": "string",
                    "enum": ["artifact", "clue", "key", "mcguffin", "letter", "document", "personal_effect", "misc"],
                    "description": "Type of story item"
                },
                "lore": {
                    "type": "string",
                    "description": "History and backstory of the item"
                },
                "discovery_conditions": {
                    "type": "string",
                    "description": "How players can discover this item"
                },
                "dm_notes": {
                    "type": "string",
                    "description": "DM-only notes about the item's significance"
                }
            },
            "required": ["name", "description"]
        }
    }
}

REVEAL_STORY_ITEM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "reveal_story_item",
        "description": "Mark a story item as discovered by the party.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "The story item's ID"
                }
            },
            "required": ["item_id"]
        }
    }
}

TRANSFER_STORY_ITEM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "transfer_story_item",
        "description": "Transfer a story item to a new holder (character, NPC, or location).",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "The story item's ID"
                },
                "new_holder_id": {
                    "type": "integer",
                    "description": "ID of the new holder (character or NPC)"
                },
                "holder_type": {
                    "type": "string",
                    "enum": ["character", "npc", "location", "none"],
                    "description": "Type of the new holder"
                }
            },
            "required": ["item_id", "holder_type"]
        }
    }
}

GET_STORY_ITEMS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_story_items",
        "description": "Get story items, optionally filtered by holder or discovery status.",
        "parameters": {
            "type": "object",
            "properties": {
                "holder_id": {
                    "type": "integer",
                    "description": "Filter by holder ID"
                },
                "is_discovered": {
                    "type": "boolean",
                    "description": "Filter by discovery status"
                }
            },
            "required": []
        }
    }
}


# =============================================================================
# STORY EVENT TOOLS
# =============================================================================

CREATE_STORY_EVENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_story_event",
        "description": "Create a campaign event (main plot beat, side event, scheduled happening).",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the event"
                },
                "description": {
                    "type": "string",
                    "description": "Description of what happens"
                },
                "event_type": {
                    "type": "string",
                    "enum": ["main_plot", "side_event", "random", "scheduled"],
                    "description": "Type of story event"
                },
                "trigger_conditions": {
                    "type": "string",
                    "description": "Conditions that trigger this event"
                },
                "location_id": {
                    "type": "integer",
                    "description": "Location where the event occurs"
                },
                "dm_notes": {
                    "type": "string",
                    "description": "DM-only notes about running this event"
                }
            },
            "required": ["name", "description"]
        }
    }
}

TRIGGER_EVENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "trigger_event",
        "description": "Activate a pending story event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "integer",
                    "description": "The event's ID"
                }
            },
            "required": ["event_id"]
        }
    }
}

RESOLVE_EVENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "resolve_event",
        "description": "Complete a story event with its outcome.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "integer",
                    "description": "The event's ID"
                },
                "outcome": {
                    "type": "string",
                    "enum": ["success", "failure", "partial", "complicated"],
                    "description": "How the event was resolved"
                },
                "resolution_notes": {
                    "type": "string",
                    "description": "Notes about how the event concluded"
                }
            },
            "required": ["event_id", "outcome"]
        }
    }
}

GET_ACTIVE_EVENTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_active_events",
        "description": "Get all currently active story events.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


# =============================================================================
# CROSS-SYSTEM WIRING TOOLS
# These tools integrate multiple game systems for seamless gameplay
# =============================================================================

MOVE_CHARACTER_TO_LOCATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "move_character_to_location",
        "description": "Move a character to a new location. Updates character's position and can trigger location events. Returns who else is at that location.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character's ID"
                },
                "location_id": {
                    "type": "integer",
                    "description": "The target location's ID"
                }
            },
            "required": ["character_id", "location_id"]
        }
    }
}

GET_CHARACTERS_AT_LOCATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_characters_at_location",
        "description": "Get all characters currently at a specific location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "The location's ID"
                }
            },
            "required": ["location_id"]
        }
    }
}

GET_NPCS_AT_LOCATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_npcs_at_location",
        "description": "Get all NPCs currently at a specific location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "The location's ID"
                }
            },
            "required": ["location_id"]
        }
    }
}

EXPLORE_LOCATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "explore_location",
        "description": "Have a character explore their current location. Returns NPCs present, discoverable story items, active events at the location, and connected locations. Perfect for 'look around' or 'search area' actions.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character exploring"
                },
                "perception_roll": {
                    "type": "integer",
                    "description": "Optional perception roll result to determine what hidden things are found"
                }
            },
            "required": ["character_id"]
        }
    }
}

PICKUP_STORY_ITEM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "pickup_story_item",
        "description": "Have a character pick up a story item. Marks it as discovered, transfers ownership to the character, and logs the discovery event.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character picking up the item"
                },
                "item_id": {
                    "type": "integer",
                    "description": "The story item's ID"
                },
                "discovery_context": {
                    "type": "string",
                    "description": "How/where the item was found (e.g., 'hidden in the desk drawer')"
                }
            },
            "required": ["character_id", "item_id"]
        }
    }
}

DROP_STORY_ITEM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "drop_story_item",
        "description": "Have a character drop/leave a story item at the current location.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character dropping the item"
                },
                "item_id": {
                    "type": "integer",
                    "description": "The story item's ID"
                }
            },
            "required": ["character_id", "item_id"]
        }
    }
}

LONG_REST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "long_rest",
        "description": "Character takes a long rest (8 hours). Fully restores HP and mana, clears temporary status effects, advances time, and logs the rest in session history.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character resting"
                },
                "location_description": {
                    "type": "string",
                    "description": "Where the character is resting (e.g., 'at the tavern', 'in the forest camp')"
                },
                "interrupted": {
                    "type": "boolean",
                    "description": "Whether the rest was interrupted (partial recovery only)"
                }
            },
            "required": ["character_id"]
        }
    }
}

SHORT_REST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "short_rest",
        "description": "Character takes a short rest (1 hour). Restores some HP (25%) and mana (50%), advances time by 1 hour.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character resting"
                }
            },
            "required": ["character_id"]
        }
    }
}

END_COMBAT_WITH_REWARDS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "end_combat_with_rewards",
        "description": "End combat and automatically distribute XP and loot to all participating characters. Syncs combat damage back to character HP. Use this instead of end_combat when combat ends in victory.",
        "parameters": {
            "type": "object",
            "properties": {
                "combat_id": {
                    "type": "integer",
                    "description": "The combat encounter's ID"
                },
                "victory": {
                    "type": "boolean",
                    "description": "Whether the party won the combat"
                },
                "bonus_xp": {
                    "type": "integer",
                    "description": "Additional XP to award beyond enemy XP values"
                },
                "bonus_gold": {
                    "type": "integer",
                    "description": "Additional gold to distribute"
                },
                "loot_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "string"},
                            "item_name": {"type": "string"},
                            "item_type": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "properties": {"type": "object"}
                        }
                    },
                    "description": "Items dropped by enemies to distribute"
                }
            },
            "required": ["combat_id", "victory"]
        }
    }
}

COMPLETE_QUEST_WITH_REWARDS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "complete_quest_with_rewards",
        "description": "Complete a quest and automatically distribute rewards to all party members. Updates quest status and logs story event.",
        "parameters": {
            "type": "object",
            "properties": {
                "quest_id": {
                    "type": "integer",
                    "description": "The quest's ID"
                },
                "character_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Characters who participated in completing the quest"
                },
                "bonus_rewards": {
                    "type": "object",
                    "properties": {
                        "xp": {"type": "integer"},
                        "gold": {"type": "integer"}
                    },
                    "description": "Additional rewards beyond the quest's base rewards"
                }
            },
            "required": ["quest_id", "character_ids"]
        }
    }
}

GET_COMPREHENSIVE_SESSION_STATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_comprehensive_session_state",
        "description": "Get the complete state of a game session including party status, current location, active quests, NPCs present, active events, and recent story. Use this to get full context for decision-making.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "integer",
                    "description": "The session's ID"
                }
            },
            "required": ["session_id"]
        }
    }
}


# =============================================================================
# ENHANCED NPC TOOLS
# =============================================================================

GENERATE_NPC_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_npc",
        "description": "Generate a new NPC using templates and customization. Creates a unique, memorable character.",
        "parameters": {
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "enum": ["merchant", "guard", "scholar", "innkeeper", "noble", "criminal", "mystic", "peasant", "adventurer", "villain"],
                    "description": "Base template for the NPC"
                },
                "name": {
                    "type": "string",
                    "description": "Optional specific name for the NPC"
                },
                "location": {
                    "type": "string",
                    "description": "Where this NPC is found"
                },
                "purpose": {
                    "type": "string",
                    "description": "The NPC's narrative purpose"
                },
                "custom_traits": {
                    "type": "object",
                    "description": "Custom personality traits or features"
                }
            },
            "required": ["template"]
        }
    }
}

SET_NPC_SECRET_SCHEMA = {
    "type": "function",
    "function": {
        "name": "set_npc_secret",
        "description": "Set or update an NPC's hidden secret or motivation.",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {
                    "type": "integer",
                    "description": "The NPC's ID"
                },
                "secret": {
                    "type": "string",
                    "description": "The NPC's secret or hidden motivation"
                }
            },
            "required": ["npc_id", "secret"]
        }
    }
}


# =============================================================================
# NPC PARTY MEMBER TOOLS
# =============================================================================

ADD_NPC_TO_PARTY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "add_npc_to_party",
        "description": "Add an NPC as a companion/party member. They will travel with and assist the party in combat.",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {
                    "type": "integer",
                    "description": "The NPC's ID to add to party"
                },
                "party_role": {
                    "type": "string",
                    "enum": ["tank", "healer", "damage", "support", "utility", "guide"],
                    "description": "The NPC's role in the party"
                },
                "combat_stats": {
                    "type": "object",
                    "description": "Optional combat stats override: {hp, ac, attack_bonus, damage, abilities}",
                    "properties": {
                        "hp": {"type": "integer"},
                        "max_hp": {"type": "integer"},
                        "ac": {"type": "integer"},
                        "attack_bonus": {"type": "integer"},
                        "damage": {"type": "string"},
                        "abilities": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "required": ["npc_id"]
        }
    }
}

REMOVE_NPC_FROM_PARTY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "remove_npc_from_party",
        "description": "Remove an NPC companion from the party.",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {
                    "type": "integer",
                    "description": "The NPC's ID to remove"
                },
                "reason": {
                    "type": "string",
                    "description": "Why the NPC is leaving (for story purposes)"
                }
            },
            "required": ["npc_id"]
        }
    }
}

GET_PARTY_NPCS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_party_npcs",
        "description": "Get all NPC companions currently in the party.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

UPDATE_NPC_LOYALTY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_npc_loyalty",
        "description": "Change an NPC party member's loyalty based on party actions.",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {
                    "type": "integer",
                    "description": "The NPC's ID"
                },
                "loyalty_change": {
                    "type": "integer",
                    "description": "Amount to change loyalty (positive or negative, scale 0-100)"
                },
                "reason": {
                    "type": "string",
                    "description": "What caused the loyalty change"
                }
            },
            "required": ["npc_id", "loyalty_change"]
        }
    }
}

NPC_PARTY_ACTION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "npc_party_action",
        "description": "Have an NPC party member take an action (attack, use ability, help, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {
                    "type": "integer",
                    "description": "The NPC's ID"
                },
                "action_type": {
                    "type": "string",
                    "enum": ["attack", "defend", "heal", "support", "ability", "flee"],
                    "description": "Type of action"
                },
                "target": {
                    "type": "string",
                    "description": "Target of the action (enemy name or 'party' for support actions)"
                },
                "ability_name": {
                    "type": "string",
                    "description": "If action_type is 'ability', which ability to use"
                }
            },
            "required": ["npc_id", "action_type"]
        }
    }
}


# =============================================================================
# GENERATIVE AI WORLDBUILDING TOOLS
# =============================================================================

GENERATE_WORLD_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_world",
        "description": "Generate or expand the game world based on the campaign theme. Creates locations, factions, and lore.",
        "parameters": {
            "type": "object",
            "properties": {
                "theme": {
                    "type": "string",
                    "description": "The campaign theme/setting (e.g., 'Duke Nukem style alien invasion', 'dark fantasy')"
                },
                "scope": {
                    "type": "string",
                    "enum": ["region", "city", "dungeon", "full_world"],
                    "description": "How much world to generate"
                },
                "focus_elements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific elements to include (e.g., ['alien tech', 'neon cities', 'strip clubs'])"
                },
                "tone": {
                    "type": "string",
                    "enum": ["comedic", "serious", "grimdark", "heroic", "absurdist", "mixed"],
                    "description": "The tone of the generated content"
                }
            },
            "required": ["theme"]
        }
    }
}

GENERATE_KEY_NPCS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_key_npcs",
        "description": "Generate key NPCs for a campaign based on the setting and goals. Creates important characters like allies, rivals, and potential party members.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_theme": {
                    "type": "string",
                    "description": "The campaign theme/setting"
                },
                "goals": {
                    "type": "string",
                    "description": "The party's main goals or quest"
                },
                "npc_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["ally", "mentor", "rival", "villain", "quest_giver", "love_interest", "comic_relief", "mysterious_stranger", "key_figure"]
                    },
                    "description": "Types of NPCs to generate"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of NPCs to generate (default 3)"
                },
                "make_party_members": {
                    "type": "boolean",
                    "description": "If true, generate NPCs suitable for joining the party as companions"
                }
            },
            "required": ["campaign_theme"]
        }
    }
}

GENERATE_LOCATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_location",
        "description": "Generate a detailed location with points of interest, NPCs, and potential encounters.",
        "parameters": {
            "type": "object",
            "properties": {
                "location_type": {
                    "type": "string",
                    "enum": ["town", "city", "dungeon", "wilderness", "stronghold", "ruins", "tavern", "shop", "temple", "secret_base"],
                    "description": "Type of location to generate"
                },
                "theme": {
                    "type": "string",
                    "description": "Theme/style for the location (e.g., 'alien-infested warehouse')"
                },
                "purpose": {
                    "type": "string",
                    "description": "Narrative purpose of the location (e.g., 'where the party finds the alien artifact')"
                },
                "danger_level": {
                    "type": "string",
                    "enum": ["safe", "low", "medium", "high", "deadly"],
                    "description": "How dangerous the location is"
                },
                "generate_npcs": {
                    "type": "boolean",
                    "description": "Whether to generate NPCs for this location"
                },
                "generate_loot": {
                    "type": "boolean",
                    "description": "Whether to generate loot/items at this location"
                }
            },
            "required": ["location_type"]
        }
    }
}

GENERATE_QUEST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_quest",
        "description": "Generate a quest with objectives, rewards, and story hooks based on the current game state.",
        "parameters": {
            "type": "object",
            "properties": {
                "quest_type": {
                    "type": "string",
                    "enum": ["main", "side", "fetch", "kill", "escort", "mystery", "rescue", "exploration", "boss"],
                    "description": "Type of quest to generate"
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard", "epic"],
                    "description": "Quest difficulty"
                },
                "theme": {
                    "type": "string",
                    "description": "Theme/context for the quest"
                },
                "related_npc_id": {
                    "type": "integer",
                    "description": "Optional NPC who gives or is involved in the quest"
                },
                "location_id": {
                    "type": "integer",
                    "description": "Optional location where the quest takes place"
                },
                "auto_create": {
                    "type": "boolean",
                    "description": "If true, automatically create the quest in the database"
                }
            },
            "required": ["quest_type"]
        }
    }
}

GENERATE_ENCOUNTER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_encounter",
        "description": "Generate a combat or social encounter appropriate for the party.",
        "parameters": {
            "type": "object",
            "properties": {
                "encounter_type": {
                    "type": "string",
                    "enum": ["combat", "social", "puzzle", "trap", "boss", "ambush", "random"],
                    "description": "Type of encounter"
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard", "deadly"],
                    "description": "Encounter difficulty"
                },
                "theme": {
                    "type": "string",
                    "description": "Theme for the encounter (e.g., 'alien invaders', 'robot guards')"
                },
                "party_level": {
                    "type": "integer",
                    "description": "Average party level (auto-detected if not provided)"
                },
                "party_size": {
                    "type": "integer",
                    "description": "Number of party members (auto-detected if not provided)"
                },
                "auto_start_combat": {
                    "type": "boolean",
                    "description": "If true and encounter_type is 'combat', automatically start the combat"
                }
            },
            "required": ["encounter_type"]
        }
    }
}

GENERATE_BACKSTORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_backstory",
        "description": "Generate or expand a character's backstory, creating connections to the world.",
        "parameters": {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "integer",
                    "description": "The character to generate backstory for"
                },
                "hooks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Story hooks to incorporate (e.g., ['orphan', 'seeking revenge', 'hidden power'])"
                },
                "connection_to_plot": {
                    "type": "string",
                    "description": "How to connect the backstory to the main plot"
                },
                "depth": {
                    "type": "string",
                    "enum": ["brief", "moderate", "detailed"],
                    "description": "How detailed the backstory should be"
                }
            },
            "required": ["character_id"]
        }
    }
}

GENERATE_LOOT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_loot",
        "description": "Generate appropriate loot/rewards based on context.",
        "parameters": {
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Context for the loot (e.g., 'defeated alien boss', 'ancient treasure chest')"
                },
                "value_tier": {
                    "type": "string",
                    "enum": ["poor", "common", "uncommon", "rare", "epic", "legendary"],
                    "description": "Value/rarity tier of the loot"
                },
                "item_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["weapon", "armor", "consumable", "gold", "treasure", "key_item", "junk"]
                    },
                    "description": "Types of items to include"
                },
                "party_level": {
                    "type": "integer",
                    "description": "Party level for scaling (auto-detected if not provided)"
                },
                "auto_distribute": {
                    "type": "boolean",
                    "description": "If true, automatically give loot to party members"
                }
            },
            "required": ["context"]
        }
    }
}

INITIALIZE_CAMPAIGN_SCHEMA = {
    "type": "function",
    "function": {
        "name": "initialize_campaign",
        "description": "Initialize a new campaign by generating world, key NPCs, starting location, and initial quest hook all at once.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_name": {
                    "type": "string",
                    "description": "Name of the campaign"
                },
                "theme": {
                    "type": "string",
                    "description": "Campaign theme/setting (e.g., 'Duke Nukem style action, aliens invading a neon-lit city')"
                },
                "tone": {
                    "type": "string",
                    "enum": ["comedic", "serious", "grimdark", "heroic", "absurdist", "mixed"],
                    "description": "Overall tone of the campaign"
                },
                "starting_scenario": {
                    "type": "string",
                    "description": "Description of how the adventure begins"
                },
                "key_npcs_to_generate": {
                    "type": "integer",
                    "description": "Number of key NPCs to generate (default 3)"
                },
                "include_potential_ally": {
                    "type": "boolean",
                    "description": "If true, generate at least one NPC suitable for joining the party"
                }
            },
            "required": ["campaign_name", "theme"]
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
    END_COMBAT_WITH_REWARDS_SCHEMA,
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
    COMPLETE_QUEST_WITH_REWARDS_SCHEMA,
    GET_QUESTS_SCHEMA,
    # NPC
    GET_NPC_INFO_SCHEMA,
    CREATE_NPC_SCHEMA,
    UPDATE_NPC_RELATIONSHIP_SCHEMA,
    GET_NPCS_SCHEMA,
    GENERATE_NPC_SCHEMA,
    SET_NPC_SECRET_SCHEMA,
    # NPC Party Members
    ADD_NPC_TO_PARTY_SCHEMA,
    REMOVE_NPC_FROM_PARTY_SCHEMA,
    GET_PARTY_NPCS_SCHEMA,
    UPDATE_NPC_LOYALTY_SCHEMA,
    NPC_PARTY_ACTION_SCHEMA,
    # Session
    GET_PARTY_INFO_SCHEMA,
    ADD_STORY_ENTRY_SCHEMA,
    GET_STORY_LOG_SCHEMA,
    GET_COMPREHENSIVE_SESSION_STATE_SCHEMA,
    # Memory
    SAVE_MEMORY_SCHEMA,
    GET_PLAYER_MEMORIES_SCHEMA,
    # Spells & Abilities
    GET_CHARACTER_SPELLS_SCHEMA,
    CAST_SPELL_SCHEMA,
    USE_ABILITY_SCHEMA,
    GET_CHARACTER_ABILITIES_SCHEMA,
    REST_CHARACTER_SCHEMA,
    LONG_REST_SCHEMA,
    SHORT_REST_SCHEMA,
    # Locations
    CREATE_LOCATION_SCHEMA,
    GET_LOCATION_SCHEMA,
    GET_NEARBY_LOCATIONS_SCHEMA,
    UPDATE_LOCATION_SCHEMA,
    MOVE_PARTY_TO_LOCATION_SCHEMA,
    MOVE_CHARACTER_TO_LOCATION_SCHEMA,
    GET_CHARACTERS_AT_LOCATION_SCHEMA,
    GET_NPCS_AT_LOCATION_SCHEMA,
    EXPLORE_LOCATION_SCHEMA,
    # Story Items
    CREATE_STORY_ITEM_SCHEMA,
    REVEAL_STORY_ITEM_SCHEMA,
    TRANSFER_STORY_ITEM_SCHEMA,
    GET_STORY_ITEMS_SCHEMA,
    PICKUP_STORY_ITEM_SCHEMA,
    DROP_STORY_ITEM_SCHEMA,
    # Story Events
    CREATE_STORY_EVENT_SCHEMA,
    TRIGGER_EVENT_SCHEMA,
    RESOLVE_EVENT_SCHEMA,
    GET_ACTIVE_EVENTS_SCHEMA,
    # Generative AI / Worldbuilding
    GENERATE_WORLD_SCHEMA,
    GENERATE_KEY_NPCS_SCHEMA,
    GENERATE_LOCATION_SCHEMA,
    GENERATE_QUEST_SCHEMA,
    GENERATE_ENCOUNTER_SCHEMA,
    GENERATE_BACKSTORY_SCHEMA,
    GENERATE_LOOT_SCHEMA,
    INITIALIZE_CAMPAIGN_SCHEMA,
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
                      NEXT_TURN_SCHEMA, GET_COMBAT_STATUS_SCHEMA, END_COMBAT_SCHEMA,
                      END_COMBAT_WITH_REWARDS_SCHEMA],
            "dice": [ROLL_DICE_SCHEMA, ROLL_ATTACK_SCHEMA, ROLL_SAVE_SCHEMA, 
                    ROLL_SKILL_CHECK_SCHEMA],
            "quest": [CREATE_QUEST_SCHEMA, UPDATE_QUEST_SCHEMA, COMPLETE_OBJECTIVE_SCHEMA,
                     GIVE_QUEST_REWARDS_SCHEMA, COMPLETE_QUEST_WITH_REWARDS_SCHEMA, 
                     GET_QUESTS_SCHEMA],
            "npc": [GET_NPC_INFO_SCHEMA, CREATE_NPC_SCHEMA, UPDATE_NPC_RELATIONSHIP_SCHEMA,
                   GET_NPCS_SCHEMA, GENERATE_NPC_SCHEMA, SET_NPC_SECRET_SCHEMA,
                   ADD_NPC_TO_PARTY_SCHEMA, REMOVE_NPC_FROM_PARTY_SCHEMA,
                   GET_PARTY_NPCS_SCHEMA, UPDATE_NPC_LOYALTY_SCHEMA, NPC_PARTY_ACTION_SCHEMA],
            "session": [GET_PARTY_INFO_SCHEMA, ADD_STORY_ENTRY_SCHEMA, GET_STORY_LOG_SCHEMA,
                       GET_COMPREHENSIVE_SESSION_STATE_SCHEMA],
            "memory": [SAVE_MEMORY_SCHEMA, GET_PLAYER_MEMORIES_SCHEMA],
            "spells": [GET_CHARACTER_SPELLS_SCHEMA, CAST_SPELL_SCHEMA, USE_ABILITY_SCHEMA,
                      GET_CHARACTER_ABILITIES_SCHEMA, REST_CHARACTER_SCHEMA,
                      LONG_REST_SCHEMA, SHORT_REST_SCHEMA],
            "location": [CREATE_LOCATION_SCHEMA, GET_LOCATION_SCHEMA, 
                        GET_NEARBY_LOCATIONS_SCHEMA, UPDATE_LOCATION_SCHEMA,
                        MOVE_PARTY_TO_LOCATION_SCHEMA, MOVE_CHARACTER_TO_LOCATION_SCHEMA,
                        GET_CHARACTERS_AT_LOCATION_SCHEMA, GET_NPCS_AT_LOCATION_SCHEMA,
                        EXPLORE_LOCATION_SCHEMA],
            "story_item": [CREATE_STORY_ITEM_SCHEMA, REVEAL_STORY_ITEM_SCHEMA,
                          TRANSFER_STORY_ITEM_SCHEMA, GET_STORY_ITEMS_SCHEMA,
                          PICKUP_STORY_ITEM_SCHEMA, DROP_STORY_ITEM_SCHEMA],
            "story_event": [CREATE_STORY_EVENT_SCHEMA, TRIGGER_EVENT_SCHEMA,
                           RESOLVE_EVENT_SCHEMA, GET_ACTIVE_EVENTS_SCHEMA],
            "worldbuilding": [GENERATE_WORLD_SCHEMA, GENERATE_KEY_NPCS_SCHEMA,
                             GENERATE_LOCATION_SCHEMA, GENERATE_QUEST_SCHEMA,
                             GENERATE_ENCOUNTER_SCHEMA, GENERATE_BACKSTORY_SCHEMA,
                             GENERATE_LOOT_SCHEMA, INITIALIZE_CAMPAIGN_SCHEMA],
        }
        return categories.get(category.lower(), [])

