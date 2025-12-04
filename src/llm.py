"""RPG DM Bot - LLM Integration via Requesty.ai
Uses OpenAI-compatible API for AI Dungeon Master features
"""

import aiohttp
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.prompts import build_dm_system_prompt

logger = logging.getLogger('rpg.llm')
logger.setLevel(logging.DEBUG)


@dataclass
class LLMResponse:
    content: str
    memories_to_save: List[Dict[str, str]]
    usage: Dict[str, int]
    tool_calls: Optional[List[Dict]] = None


class LLMClient:
    """Requesty.ai LLM client for AI Dungeon Master"""
    
    BASE_URL = "https://router.requesty.ai/v1"
    
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.session: Optional[aiohttp.ClientSession] = None
        self._api_lock = asyncio.Lock()
    
    async def ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _api_call(self, payload: dict) -> dict:
        """Make an API call with proper error handling"""
        await self.ensure_session()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.debug("=" * 60)
        logger.debug("LLM API REQUEST")
        logger.debug(f"Model: {payload.get('model')}")
        logger.debug(f"Message count: {len(payload.get('messages', []))}")
        logger.debug("=" * 60)
        
        async with self._api_lock:
            try:
                async with self.session.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"LLM API error {response.status}: {error_text}")
                        raise Exception(f"LLM API error {response.status}: {error_text}")
                    
                    result = await response.json()
                    logger.debug(f"Response received: {result.get('usage', {})}")
                    return result
                    
            except asyncio.TimeoutError:
                logger.error("LLM API timeout")
                raise Exception("LLM request timed out")
            except Exception as e:
                logger.error(f"LLM API error: {e}")
                raise
    
    async def dm_chat(
        self,
        user_message: str,
        session_context: Dict[str, Any] = None,
        party_info: List[Dict] = None,
        active_quest: Dict = None,
        combat_state: Dict = None,
        user_memories: Dict[str, Any] = None,
        user_name: str = "Adventurer",
        custom_instructions: str = None,
        conversation_context: List[Dict[str, str]] = None,
        tools: List[Dict] = None
    ) -> LLMResponse:
        """
        Generate a DM response to a player message.
        
        Args:
            user_message: The player's message
            session_context: Current campaign/session info
            party_info: List of party members
            active_quest: Currently active quest
            combat_state: Current combat state if any
            user_memories: Memories about the player
            user_name: Player's display name
            custom_instructions: Custom DM style
            conversation_context: Recent conversation history
            tools: Available tools for the LLM
            
        Returns:
            LLMResponse with content and any tool calls
        """
        # Build system prompt
        system_prompt = build_dm_system_prompt(
            session_context=session_context,
            party_info=party_info,
            active_quest=active_quest,
            combat_state=combat_state,
            user_memories=user_memories,
            custom_instructions=custom_instructions
        )
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation context
        if conversation_context:
            for msg in conversation_context:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": f"[{user_name}]: {user_message}"
        })
        
        # Build payload
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.8,  # Higher for more creative DM responses
            "max_tokens": 1000,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        # Make API call
        result = await self._api_call(payload)
        
        # Parse response
        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls")
        
        # Parse memories from response
        memories_to_save = self._extract_memories(content)
        if memories_to_save:
            # Remove JSON block from content
            content = self._remove_memory_json(content)
        
        return LLMResponse(
            content=content,
            memories_to_save=memories_to_save,
            usage=result.get("usage", {}),
            tool_calls=tool_calls
        )
    
    async def dm_chat_with_tool_results(
        self,
        user_message: str,
        assistant_tool_calls: List[Dict],
        tool_results: List[Dict],
        session_context: Dict[str, Any] = None,
        party_info: List[Dict] = None,
        active_quest: Dict = None,
        combat_state: Dict = None,
        user_memories: Dict[str, Any] = None,
        user_name: str = "Adventurer",
        custom_instructions: str = None,
        conversation_context: List[Dict[str, str]] = None,
        tools: List[Dict] = None,
        all_tool_history: List[Dict] = None
    ) -> LLMResponse:
        """Continue conversation after tool execution"""
        
        # Build system prompt
        system_prompt = build_dm_system_prompt(
            session_context=session_context,
            party_info=party_info,
            active_quest=active_quest,
            combat_state=combat_state,
            user_memories=user_memories,
            custom_instructions=custom_instructions
        )
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation context
        if conversation_context:
            for msg in conversation_context:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": f"[{user_name}]: {user_message}"
        })
        
        # Add all tool history
        if all_tool_history:
            for round_data in all_tool_history:
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": round_data["tool_calls"]
                })
                # Add tool results
                for result in round_data["results"]:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "name": result["name"],
                        "content": result["result"]
                    })
        else:
            # Single round of tool calls
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": assistant_tool_calls
            })
            for result in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": result["tool_call_id"],
                    "name": result["name"],
                    "content": result["result"]
                })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 1000,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        result = await self._api_call(payload)
        
        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls")
        
        memories_to_save = self._extract_memories(content)
        if memories_to_save:
            content = self._remove_memory_json(content)
        
        return LLMResponse(
            content=content,
            memories_to_save=memories_to_save,
            usage=result.get("usage", {}),
            tool_calls=tool_calls
        )
    
    async def generate_npc_dialogue(
        self,
        npc: Dict[str, Any],
        character: Dict[str, Any],
        relationship: Dict[str, Any],
        player_message: str,
        context: str = None
    ) -> str:
        """Generate NPC dialogue response"""
        from src.prompts import build_npc_dialogue_prompt
        
        system_prompt = build_npc_dialogue_prompt(npc, character, relationship, context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": player_message}
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.9,
            "max_tokens": 500,
        }
        
        result = await self._api_call(payload)
        
        choice = result.get("choices", [{}])[0]
        return choice.get("message", {}).get("content", "...")
    
    async def narrate_combat_action(
        self,
        action: str,
        attacker: Dict[str, Any],
        defender: Dict[str, Any],
        roll_result: Dict[str, Any],
        damage: int = None
    ) -> str:
        """Generate dramatic combat narration"""
        from src.prompts import build_combat_narration_prompt
        
        system_prompt = build_combat_narration_prompt(
            action, attacker, defender, roll_result, damage
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Narrate this action."}
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.9,
            "max_tokens": 200,
        }
        
        result = await self._api_call(payload)
        
        choice = result.get("choices", [{}])[0]
        return choice.get("message", {}).get("content", "The attack resolves...")
    
    async def describe_scene(
        self,
        location: str,
        details: Dict[str, Any] = None,
        npcs_present: List[Dict] = None,
        party: List[Dict] = None,
        mood: str = "neutral"
    ) -> str:
        """Generate a scene description"""
        from src.prompts import build_scene_prompt
        
        system_prompt = build_scene_prompt(location, details, npcs_present, party, mood)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Describe this scene."}
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 300,
        }
        
        result = await self._api_call(payload)
        
        choice = result.get("choices", [{}])[0]
        return choice.get("message", {}).get("content", "You arrive at the location...")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500
    ) -> str:
        """Simple chat endpoint without tool support"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": max_tokens,
        }
        
        result = await self._api_call(payload)
        choice = result.get("choices", [{}])[0]
        return choice.get("message", {}).get("content", "")
    
    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """Chat with tool calling support - returns dict with content and tool_calls"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": max_tokens,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        result = await self._api_call(payload)
        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        
        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls", [])
        }
    
    def _extract_memories(self, content: str) -> List[Dict[str, str]]:
        """Extract memory JSON from response content"""
        import re
        
        pattern = r'```json\s*(\{[^`]*"memories"[^`]*\})\s*```'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            try:
                data = json.loads(match.group(1))
                return data.get("memories", [])
            except json.JSONDecodeError:
                pass
        
        return []
    
    def _remove_memory_json(self, content: str) -> str:
        """Remove memory JSON block from content"""
        import re
        
        pattern = r'```json\s*\{[^`]*"memories"[^`]*\}\s*```'
        return re.sub(pattern, '', content, flags=re.DOTALL).strip()
