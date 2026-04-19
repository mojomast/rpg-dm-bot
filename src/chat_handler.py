"""
RPG DM Bot - Shared chat handler.
Reusable DM orchestration for Discord and web chat.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.mechanics_tracker import new_tracker
from src.prompts import PROACTIVE_DM_GUIDELINES, SLASH_COMMAND_CONTEXT

logger = logging.getLogger("rpg.chat_handler")

MAX_TOOL_ROUNDS = 5


@dataclass
class ChatActor:
    user_id: int
    display_name: str
    character_name: Optional[str] = None
    character_id: Optional[int] = None


class ChatHandler:
    """Shared DM chat orchestration for Discord and web."""

    def __init__(self, db, llm, prompts, tool_schemas, tools):
        self.db = db
        self.llm = llm
        self.prompts = prompts
        self.tool_schemas = tool_schemas
        self.tools = tools

    async def resolve_session(self, guild_id: int, session_id: Optional[int] = None, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Resolve the active session for the current context."""
        if session_id:
            session = await self.db.get_session(session_id)
            if session and session.get("guild_id") == guild_id:
                return session
            return None

        if user_id:
            user_session = await self.db.get_user_active_session(guild_id, user_id)
            if user_session:
                return user_session

        session = await self.db.get_active_session(guild_id)
        if session and session.get("guild_id") == guild_id:
            return session
        return None

    def build_full_response(self, response_text: str, mechanics_text: str = "") -> str:
        return f"{mechanics_text}\n{response_text}" if mechanics_text else response_text

    def extract_response_options(self, response_text: str) -> List[str]:
        if not response_text:
            return []
        options = [match.group(1).strip() for match in re.finditer(r"^\s*[1-3][.)]\s*(.+)", response_text, re.MULTILINE)]
        if options:
            return options
        return [match.group(1).strip() for match in re.finditer(r"^\s*[A-C][.)]\s*(.+)", response_text, re.MULTILINE)]

    async def build_batch_character_context(self, messages: List[Dict[str, Any]]) -> str:
        """Build a character summary for every player acting in a batch."""
        context_lines: List[str] = []
        seen_character_ids: set[int] = set()

        for message in messages:
            character_id = message.get("character_id")
            if not character_id or character_id in seen_character_ids:
                continue

            seen_character_ids.add(character_id)
            char = await self.db.get_character(character_id)
            if not char:
                continue

            char_class = char.get("char_class") or char.get("class", "Unknown")
            context_lines.append(
                f"- {message['display_name']} is playing {char['name']} (character_id={char['id']}, user_id={message['user_id']}): Level {char['level']} {char['race']} {char_class}, HP {char['hp']}/{char['max_hp']}"
            )

        if not context_lines:
            return ""

        return "\nBATCH PLAYER CHARACTERS:\n" + "\n".join(context_lines)

    async def get_game_context(
        self,
        guild_id: int,
        user_id: int,
        channel_id: int,
        session_id: Optional[int] = None,
        character_id: Optional[int] = None,
        include_character_context: bool = True,
    ) -> str:
        """Build context about the current game state."""
        context_parts: List[str] = []
        current_location = None

        char = None
        if include_character_context:
            char = await self.db.get_character(character_id) if character_id else await self.db.get_active_character(user_id, guild_id)
        if char:
            char_class = char.get("char_class") or char.get("class", "Unknown")
            context_parts.append(
                f"""
PLAYER CHARACTER:
- Name: {char['name']}
- Class: {char_class} | Race: {char['race']}
- Level: {char['level']} | XP: {char.get('xp', char.get('experience', 0))}
- HP: {char['hp']}/{char['max_hp']}
- Stats: STR {char['strength']}, DEX {char['dexterity']}, CON {char['constitution']}, INT {char['intelligence']}, WIS {char['wisdom']}, CHA {char['charisma']}
- Gold: {char['gold']}"""
            )

            if char.get("backstory"):
                context_parts.append(f"- Backstory: {char['backstory']}")

            if char.get("current_location_id"):
                char_location = await self.db.get_location(char["current_location_id"])
                if char_location:
                    context_parts.append(f"- Current Location: {char_location['name']}")

        session = await self.resolve_session(guild_id, session_id=session_id, user_id=user_id)

        if session:
            context_parts.append(
                f"""
ACTIVE SESSION: {session['name']}
Game Description: {session.get('description', 'An adventure awaits!')}"""
            )

            players = await self.db.get_session_players(session["id"])
            if players:
                context_parts.append("\nPARTY MEMBERS:")
                for player in players:
                    if not player.get("character_id"):
                        continue
                    party_char = await self.db.get_character(player["character_id"])
                    if not party_char:
                        continue
                    pc_class = party_char.get("char_class") or party_char.get("class", "Unknown")
                    context_parts.append(f"- {party_char['name']}: Level {party_char['level']} {party_char['race']} {pc_class}")
                    context_parts.append(f"  HP: {party_char['hp']}/{party_char['max_hp']}")
                    if party_char.get("backstory"):
                        context_parts.append(f"  Backstory: {party_char['backstory'][:500]}...")

            game_state = await self.db.get_game_state(session["id"])
            if game_state:
                if game_state.get("current_scene"):
                    context_parts.append(f"\nCURRENT SCENE: {game_state['current_scene']}")
                if game_state.get("current_location_id"):
                    current_location = await self.db.get_location(game_state["current_location_id"])
                if current_location:
                    context_parts.append(f"CURRENT LOCATION: {current_location['name']}")
                elif game_state.get("current_location"):
                    context_parts.append(f"CURRENT LOCATION: {game_state['current_location']}")
                if game_state.get("dm_notes"):
                    context_parts.append(f"DM NOTES: {game_state['dm_notes']}")

            if current_location:
                loc_details = [f"\nLOCATION DETAILS ({current_location['name']}):"]
                loc_details.append(f"- Type: {current_location.get('location_type', 'generic')}")
                loc_details.append(f"- Description: {current_location.get('description', 'Unknown')}")
                if current_location.get("current_weather"):
                    loc_details.append(f"- Weather: {current_location['current_weather']}")
                if current_location.get("danger_level", 0) > 0:
                    danger = current_location["danger_level"]
                    danger_text = "Low" if danger < 3 else "Moderate" if danger < 5 else "High" if danger < 8 else "Deadly"
                    loc_details.append(f"- Danger Level: {danger_text}")
                if current_location.get("points_of_interest"):
                    poi = current_location["points_of_interest"]
                    if isinstance(poi, list):
                        loc_details.append(f"- Points of Interest: {', '.join(poi)}")
                context_parts.extend(loc_details)

                npcs_at_location = await self.db.get_npcs_at_location(current_location["id"])
                if npcs_at_location:
                    context_parts.append("\nNPCS AT THIS LOCATION:")
                    for npc in npcs_at_location[:5]:
                        merchant = " (Merchant)" if npc.get("is_merchant") else ""
                        context_parts.append(f"- {npc['name']}{merchant} ({npc.get('npc_type', 'neutral')})")
                        if npc.get("personality"):
                            context_parts.append(f"  Personality: {npc['personality'][:100]}...")

                nearby = await self.db.get_nearby_locations(current_location["id"])
                if nearby:
                    context_parts.append("\nNEARBY LOCATIONS (EXITS):")
                    for loc in nearby[:5]:
                        direction = f" ({loc.get('direction', 'path')})" if loc.get("direction") else ""
                        context_parts.append(f"- {loc.get('to_name', loc.get('name', 'Unknown'))}{direction}")

                story_items = await self.db.get_story_items_at_location(current_location["id"])
                if story_items:
                    context_parts.append("\nSTORY ITEMS HERE:")
                    for item in story_items[:5]:
                        discovered = "(Discovered)" if item.get("is_discovered") else "(Hidden)"
                        context_parts.append(f"- {item['name']} {discovered}: {item.get('description', '')[:60]}...")

            active_events = await self.db.get_active_events(session["id"])
            if active_events:
                context_parts.append("\nACTIVE STORY EVENTS:")
                for event in active_events[:3]:
                    context_parts.append(f"- {event['name']} ({event.get('event_type', 'unknown')})")
                    if event.get("description"):
                        context_parts.append(f"  {event['description'][:100]}...")

            if session.get("current_quest_id"):
                quest = await self.db.get_quest(session["current_quest_id"])
                if quest:
                    stages = await self.db.get_quest_stages(quest["id"])
                    stage_info = await self.db.get_quest_current_stage(quest["id"], character_id)
                    current_stage = stage_info.get("stage")
                    context_parts.append(
                        f"""
CURRENT QUEST: {quest['title']}
Description: {quest['description']}
Difficulty: {quest['difficulty']}
Stage: {stage_info['index'] + 1}/{stage_info['total']}"""
                    )
                    if current_stage:
                        context_parts.append(
                            f"""
CURRENT STAGE: {current_stage['title']}
{current_stage['description']}"""
                        )

        if channel_id:
            combat = await self.db.get_active_combat(guild_id, channel_id)
        elif session and session.get("id"):
            combat = await self.db.get_active_combat_by_session(session["id"])
        else:
            combat = None
        if combat:
            participants = await self.db.get_combat_participants(combat["id"])
            context_parts.append("\nACTIVE COMBAT:")
            context_parts.append(f"Turn: {combat['current_turn']}")
            context_parts.append("Combatants:")
            for participant in participants:
                if not participant.get("character_id"):
                    continue
                char_info = await self.db.get_character(participant["character_id"])
                if char_info:
                    context_parts.append(
                        f"- {char_info['name']}: {participant['current_hp']} HP, Initiative {participant['initiative']}"
                    )

        hints = list(SLASH_COMMAND_CONTEXT["always_available"])
        if combat:
            hints.extend(SLASH_COMMAND_CONTEXT["in_combat"])
        else:
            hints.extend(SLASH_COMMAND_CONTEXT["no_combat"])
            if current_location and current_location.get("location_type") in {"town", "city", "village"}:
                hints.extend(SLASH_COMMAND_CONTEXT["in_town"])

        context_parts.append("\nAVAILABLE PLAYER COMMANDS (mention relevant ones naturally when helpful):")
        context_parts.extend(f"- {hint}" for hint in hints)

        return "\n".join(context_parts) if context_parts else "No active game context."

    def build_system_prompt(self, game_context: str, include_multiplayer: bool = False) -> str:
        sections = [self.prompts.get_dm_system_prompt(), PROACTIVE_DM_GUIDELINES]
        if include_multiplayer:
            sections.append(
                """
**MULTI-PLAYER HANDLING:**
Multiple players may act simultaneously. Handle each player's action in sequence:
1. Acknowledge each player's declared action by name
2. Roll any needed checks FOR THE SPECIFIC PLAYER taking that action
3. Describe the results for each player
4. If players are doing different things, describe each separately but in the same scene
5. Keep all players in the same location unless they explicitly split up
6. End with a prompt that addresses the whole party
7. For any player-specific tool call, include the acting player's `character_id` from the batch roster whenever possible
8. If a player-specific tool call cannot include `character_id`, include `actor_name` matching the batch roster exactly

IMPORTANT: Each player's action is prefixed with their name. Make sure you address each player's action!
"""
            )
        sections.append(
            f"""
CURRENT GAME STATE:
{game_context}

TOOLS AVAILABLE:
You have access to tools for managing the game. Use them when players want to:
- Create/modify characters
- Manage inventory and items
- Roll dice for checks and combat
- Control NPCs and dialogue
- Manage quests and progression
- Run combat encounters

Always use dice rolls for skill checks and combat. Make the game interactive and engaging.

CRITICAL:
- Always end your response with a prompt for player action. Keep the game moving!
{'- Address ALL player actions in your response, not just one!\n- Use get_character_info if you need to know who a player is playing\n' if include_multiplayer else ''}"""
        )
        return "\n\n".join(sections)

    def _match_batch_actor_by_name(self, batch_actors: List[Dict[str, Any]], actor_name: Any) -> Optional[Dict[str, Any]]:
        normalized_name = str(actor_name or "").strip().lower()
        if not normalized_name:
            return None

        for actor in batch_actors:
            if str(actor.get("character_name") or "").strip().lower() == normalized_name:
                return actor
            if str(actor.get("display_name") or "").strip().lower() == normalized_name:
                return actor
        return None

    async def _resolve_tool_context(self, base_context: Dict[str, Any], tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve the acting player context for a tool call in multiplayer turns."""
        tool_context = dict(base_context)
        batch_actors = tool_context.get("batch_actors") or []
        if not batch_actors:
            return tool_context

        actor = None
        character_id = tool_args.get("character_id")
        user_id = tool_args.get("user_id") or tool_args.get("actor_user_id")
        actor_name = tool_args.get("actor_name") or tool_args.get("character_name") or tool_args.get("player_name")

        if character_id is not None:
            try:
                character_id = int(character_id)
            except (TypeError, ValueError):
                character_id = None
            if character_id is not None:
                actor = next((entry for entry in batch_actors if entry.get("character_id") == character_id), None)
                if not actor:
                    char = await self.db.get_character(character_id)
                    if char:
                        actor = {
                            "user_id": char.get("user_id"),
                            "character_id": char.get("id"),
                            "character_name": char.get("name"),
                        }
        elif user_id is not None:
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                user_id = None
            if user_id is not None:
                actor = next((entry for entry in batch_actors if entry.get("user_id") == user_id), None)
        elif actor_name:
            actor = self._match_batch_actor_by_name(batch_actors, actor_name)
        elif len(batch_actors) == 1:
            actor = batch_actors[0]

        if actor:
            if actor.get("user_id") is not None:
                tool_context["user_id"] = actor["user_id"]
            if actor.get("character_id") is not None:
                tool_context["character_id"] = actor["character_id"]
            if actor.get("character_name"):
                tool_context["character_name"] = actor["character_name"]

        return tool_context

    async def _run_tool_loop(self, messages: List[Dict[str, Any]], context: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
        response_text = ""
        tool_results: List[Dict[str, Any]] = []

        for _ in range(MAX_TOOL_ROUNDS):
            try:
                response = await self.llm.chat_with_tools(
                    messages=messages,
                    tools=self.tool_schemas.get_all_schemas(),
                )

                tool_calls = response.get("tool_calls", [])
                content = response.get("content", "")

                if not tool_calls:
                    response_text = content.strip()
                    break

                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                })

                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    try:
                        tool_args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.info("Executing tool: %s with args: %s", tool_name, tool_args)
                    tool_context = await self._resolve_tool_context(context, tool_args)
                    tool_result = await self.tools.execute_tool(tool_name, tool_args, tool_context)
                    normalized_result, tool_message = self._normalize_tool_result(tool_result)
                    if normalized_result.get("success") is False or normalized_result.get("error"):
                        logger.warning("[TOOL RESULT] name=%s result=%s", tool_name, normalized_result)
                    tool_results.append({
                        "tool_name": tool_name,
                        "args": tool_args,
                        "result": normalized_result,
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_message,
                    })
            except Exception as exc:
                logger.error("Error in DM chat: %s", exc, exc_info=True)
                response_text = f"*The Dungeon Master pauses, gathering their thoughts...* (Error: {str(exc)[:100]})"
                break

        if not response_text:
            logger.warning("MAX_TOOL_ROUNDS (%d) exhausted without a final text response.", MAX_TOOL_ROUNDS)
            if tool_results:
                last_result = tool_results[-1].get("result")
                if isinstance(last_result, dict):
                    response_text = (
                        last_result.get("message")
                        or last_result.get("result")
                        or last_result.get("error")
                        or ""
                    )
                elif isinstance(last_result, str):
                    response_text = last_result.strip()
            if not response_text:
                response_text = "*The Dungeon Master hesitates, but the action still resolves.*"

        return response_text or "*The Dungeon Master remains silent.*", tool_results

    def _normalize_tool_result(self, tool_result: Any) -> tuple[Dict[str, Any], str]:
        if isinstance(tool_result, dict):
            message = (
                tool_result.get("message")
                or tool_result.get("result")
                or tool_result.get("error")
                or json.dumps(tool_result)
            )
            return tool_result, json.dumps(tool_result)

        if isinstance(tool_result, str):
            stripped = tool_result.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict):
                        parsed.setdefault("message", parsed.get("result") or parsed.get("error") or stripped)
                        return parsed, stripped
                except json.JSONDecodeError:
                    pass
            return {"success": not stripped.startswith("Error:"), "message": stripped}, stripped

        text = str(tool_result)
        return {"success": True, "message": text}, text

    async def process_single_message(
        self,
        guild_id: int,
        channel_id: int,
        actor: ChatActor,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        tracker = new_tracker()

        resolved_session = await self.resolve_session(guild_id, session_id=session_id, user_id=actor.user_id)
        resolved_session_id = resolved_session["id"] if resolved_session else None
        game_context = await self.get_game_context(
            guild_id,
            actor.user_id,
            channel_id,
            resolved_session_id,
            character_id=actor.character_id,
        )

        char = await self.db.get_character(actor.character_id) if actor.character_id else await self.db.get_active_character(actor.user_id, guild_id)
        char_name = actor.character_name or (char["name"] if char else actor.display_name)
        user_turn = {"role": "user", "content": f"[{actor.display_name}] ({char_name}): {user_message}"}

        messages = [
            {"role": "system", "content": self.build_system_prompt(game_context)},
            *(history or []),
            user_turn,
        ]
        context = {
            "guild_id": guild_id,
            "user_id": actor.user_id,
            "channel_id": channel_id,
            "session_id": resolved_session_id,
            "character_id": actor.character_id,
        }

        response_text, tool_results = await self._run_tool_loop(messages, context)
        mechanics_text = tracker.format_all() if tracker.has_mechanics() else ""

        return {
            "response": response_text,
            "mechanics_text": mechanics_text,
            "tool_results": tool_results,
            "session_id": resolved_session_id,
            "user_message": user_turn,
            "assistant_message": {"role": "assistant", "content": response_text},
        }

    async def process_batched_messages(
        self,
        guild_id: int,
        channel_id: int,
        messages: List[Dict[str, Any]],
        history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not messages:
            return {
                "response": "*The Dungeon Master waits for your actions.*",
                "mechanics_text": "",
                "tool_results": [],
                "session_id": session_id,
            }

        tracker = new_tracker()
        first_message = messages[0]
        first_user_id = first_message["user_id"]
        first_character_id = first_message.get("character_id")
        resolved_session = await self.resolve_session(guild_id, session_id=session_id, user_id=first_user_id)
        resolved_session_id = resolved_session["id"] if resolved_session else None

        game_context = await self.get_game_context(
            guild_id,
            first_user_id,
            channel_id,
            resolved_session_id,
            character_id=first_character_id,
            include_character_context=False,
        )
        game_context += await self.build_batch_character_context(messages)

        batch_actors = [
            {
                "user_id": message["user_id"],
                "display_name": message["display_name"],
                "character_name": message.get("character_name"),
                "character_id": message.get("character_id"),
            }
            for message in messages
        ]

        player_actions = "\n".join(
            [f"**{msg['display_name']}** ({msg['character_name']}): {msg['content']}" for msg in messages]
        )
        batched_turn = {"role": "user", "content": f"[PLAYER ACTIONS THIS TURN]\n{player_actions}"}
        llm_messages = [
            {"role": "system", "content": self.build_system_prompt(game_context, include_multiplayer=True)},
            *(history or []),
            batched_turn,
        ]
        context = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "session_id": resolved_session_id,
            "batch_actors": batch_actors,
        }
        if len(batch_actors) == 1:
            context["user_id"] = first_user_id
            context["character_id"] = first_character_id

        response_text, tool_results = await self._run_tool_loop(llm_messages, context)
        mechanics_text = tracker.format_all() if tracker.has_mechanics() else ""

        return {
            "response": response_text,
            "mechanics_text": mechanics_text,
            "tool_results": tool_results,
            "session_id": resolved_session_id,
            "user_message": batched_turn,
            "assistant_message": {"role": "assistant", "content": response_text},
        }
