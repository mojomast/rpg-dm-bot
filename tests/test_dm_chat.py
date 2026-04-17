"""Focused tests for DM chat helpers."""

from types import SimpleNamespace

import pytest

from src.chat_handler import ChatHandler
from src.cogs.dm_chat import DMChat


class DummyTarget:
    def __init__(self):
        self.messages = []

    async def send(self, content, **kwargs):
        self.messages.append((content, kwargs))


def make_dm_chat_bot_stub():
    return SimpleNamespace(
        db=None,
        llm=None,
        tools=None,
        prompts=SimpleNamespace(get_dm_system_prompt=lambda: "prompt"),
        tool_schemas=SimpleNamespace(get_all_schemas=lambda: []),
    )


class TestDMChatHelpers:
    def test_extract_response_options(self):
        cog = DMChat(make_dm_chat_bot_stub())

        options = cog.extract_response_options(
            "1. Open the door\n2) Search the room\n3. Talk to the guard"
        )

        assert options == ["Open the door", "Search the room", "Talk to the guard"]

    def test_clear_all_guild_histories_filters_by_guild(self):
        cog = DMChat(make_dm_chat_bot_stub())
        cog.start_new_session(channel_id=10, session_id=1, guild_id=100)
        cog.start_new_session(channel_id=20, session_id=2, guild_id=200)

        cog.clear_all_guild_histories(100)

        assert (100, 10) not in cog.histories
        assert (200, 20) in cog.histories

    @pytest.mark.asyncio
    async def test_send_chunked_attaches_view_to_last_message(self):
        from src.utils import send_chunked

        target = DummyTarget()
        view = object()

        await send_chunked(target, "a" * 4100, view=view, max_len=2000)

        assert len(target.messages) == 3
        assert target.messages[0][1] == {}
        assert target.messages[1][1] == {}
        assert target.messages[2][1] == {"view": view}


class StubChatContextDb:
    async def get_active_character(self, user_id, guild_id):
        return None

    async def get_session(self, session_id):
        return {"id": session_id, "guild_id": 123, "name": "Test Session", "description": "Test adventure"}

    async def get_session_players(self, session_id):
        return []

    async def get_game_state(self, session_id):
        return None

    async def get_active_events(self, session_id):
        return []

    async def get_active_combat(self, guild_id=None, channel_id=None):
        return None

    async def get_active_combat_by_session(self, session_id):
        return {"id": 77, "current_turn": 2}

    async def get_combat_participants(self, encounter_id):
        return [{"character_id": 99, "current_hp": 14, "initiative": 12}]

    async def get_character(self, character_id):
        return {"id": character_id, "name": "Aria", "hp": 14, "max_hp": 20}


class TestChatHandlerContext:
    @pytest.mark.asyncio
    async def test_get_game_context_uses_session_combat_when_channel_missing(self):
        handler = ChatHandler(
            StubChatContextDb(),
            llm=None,
            prompts=SimpleNamespace(get_dm_system_prompt=lambda: "prompt"),
            tool_schemas=SimpleNamespace(get_all_schemas=lambda: []),
            tools=None,
        )

        context = await handler.get_game_context(guild_id=123, user_id=456, channel_id=0, session_id=10)

        assert "ACTIVE COMBAT:" in context
        assert "Turn: 2" in context
        assert "Aria: 14 HP, Initiative 12" in context

    @pytest.mark.asyncio
    async def test_process_batched_messages_includes_all_batch_characters(self):
        class StubBatchDb(StubChatContextDb):
            async def get_character(self, character_id):
                characters = {
                    1: {"id": 1, "name": "Aria", "level": 3, "race": "Elf", "char_class": "Rogue", "hp": 18, "max_hp": 22, "gold": 10, "strength": 10, "dexterity": 16, "constitution": 12, "intelligence": 11, "wisdom": 13, "charisma": 14},
                    2: {"id": 2, "name": "Borin", "level": 3, "race": "Dwarf", "char_class": "Cleric", "hp": 24, "max_hp": 24, "gold": 8, "strength": 14, "dexterity": 9, "constitution": 16, "intelligence": 10, "wisdom": 15, "charisma": 11},
                }
                return characters.get(character_id)

            async def get_active_combat_by_session(self, session_id):
                return None

        llm_messages = {}

        class StubLlm:
            async def chat_with_tools(self, messages, tools):
                llm_messages["messages"] = messages
                return {"content": "The party acts.", "tool_calls": []}

        handler = ChatHandler(
            StubBatchDb(),
            llm=StubLlm(),
            prompts=SimpleNamespace(get_dm_system_prompt=lambda: "prompt"),
            tool_schemas=SimpleNamespace(get_all_schemas=lambda: []),
            tools=SimpleNamespace(),
        )

        await handler.process_batched_messages(
            guild_id=123,
            channel_id=456,
            messages=[
                {"user_id": 10, "display_name": "Alice", "character_name": "Aria", "character_id": 1, "content": "I scout ahead."},
                {"user_id": 20, "display_name": "Bob", "character_name": "Borin", "character_id": 2, "content": "I guard the rear."},
            ],
            session_id=10,
        )

        system_prompt = llm_messages["messages"][0]["content"]
        assert "Alice is playing Aria" in system_prompt
        assert "Bob is playing Borin" in system_prompt
