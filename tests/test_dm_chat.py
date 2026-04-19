"""Focused tests for DM chat helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import src.cogs.dm_chat as dm_chat_module
from src.chat_handler import ChatHandler
from src.cogs.dm_chat import DMChat
from src.utils import resolve_runtime_session


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

    @pytest.mark.asyncio
    async def test_hydrate_history_from_db_populates_cold_cache(self):
        bot = make_dm_chat_bot_stub()
        bot.db = SimpleNamespace(
            get_recent_messages_by_session=AsyncMock(return_value=[
                {"role": "user", "content": "Hello there"},
                {"role": "assistant", "content": "Welcome back"},
            ])
        )
        cog = DMChat(bot)

        history = await cog.hydrate_history_from_db(67890, 11111, 7, 12345)

        assert history == [
            {"role": "user", "content": "Hello there"},
            {"role": "assistant", "content": "Welcome back"},
        ]

    @pytest.mark.asyncio
    async def test_process_dm_input_persists_messages_to_db(self):
        original_allowed = dm_chat_module.is_allowed_bot_channel
        dm_chat_module.is_allowed_bot_channel = lambda _channel_id: True
        bot = make_dm_chat_bot_stub()
        bot.db = SimpleNamespace(
            bind_session_channel=AsyncMock(),
            get_session_by_channel=AsyncMock(return_value={"id": 7}),
            get_active_character=AsyncMock(return_value={"id": 101, "name": "Aria"}),
            save_message=AsyncMock(),
            get_recent_messages_by_session=AsyncMock(return_value=[]),
        )
        cog = DMChat(bot)
        cog.chat_handler = SimpleNamespace(
            process_single_message=AsyncMock(return_value={
                "response": "The DM responds.",
                "mechanics_text": "",
                "session_id": 7,
                "user_message": {"role": "user", "content": "hello"},
                "assistant_message": {"role": "assistant", "content": "The DM responds."},
            }),
        )

        guild = SimpleNamespace(id=67890)
        channel = SimpleNamespace(id=11111)
        author = SimpleNamespace(id=12345, display_name="Alice")

        try:
            response, mechanics = await cog.process_dm_input(channel, guild, author, "hello")
        finally:
            dm_chat_module.is_allowed_bot_channel = original_allowed

        assert response == "The DM responds."
        assert mechanics == ""
        assert bot.db.save_message.await_count == 2


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
        assert "character_id=1" in system_prompt
        assert "character_id=2" in system_prompt

    @pytest.mark.asyncio
    async def test_process_batched_messages_routes_tools_to_character_id_actor(self):
        class StubBatchDb(StubChatContextDb):
            async def get_character(self, character_id):
                characters = {
                    1: {"id": 1, "user_id": 10, "name": "Aria", "level": 3, "race": "Elf", "char_class": "Rogue", "hp": 18, "max_hp": 22, "gold": 10, "strength": 10, "dexterity": 16, "constitution": 12, "intelligence": 11, "wisdom": 13, "charisma": 14},
                    2: {"id": 2, "user_id": 20, "name": "Borin", "level": 3, "race": "Dwarf", "char_class": "Cleric", "hp": 24, "max_hp": 24, "gold": 8, "strength": 14, "dexterity": 9, "constitution": 16, "intelligence": 10, "wisdom": 15, "charisma": 11},
                }
                return characters.get(character_id)

            async def get_active_combat_by_session(self, session_id):
                return None

        seen_contexts = []

        class StubTools:
            async def execute_tool(self, tool_name, tool_args, context):
                seen_contexts.append((tool_name, tool_args, dict(context)))
                return "ok"

        class StubLlm:
            def __init__(self):
                self.calls = 0

            async def chat_with_tools(self, messages, tools):
                self.calls += 1
                if self.calls == 1:
                    return {
                        "content": "Resolving actions.",
                        "tool_calls": [{
                            "id": "call_1",
                            "function": {"name": "get_character_info", "arguments": '{"character_id": 2}'},
                        }],
                    }
                return {"content": "Done.", "tool_calls": []}

        handler = ChatHandler(
            StubBatchDb(),
            llm=StubLlm(),
            prompts=SimpleNamespace(get_dm_system_prompt=lambda: "prompt"),
            tool_schemas=SimpleNamespace(get_all_schemas=lambda: []),
            tools=StubTools(),
        )

        await handler.process_batched_messages(
            guild_id=123,
            channel_id=456,
            messages=[
                {"user_id": 10, "display_name": "Alice", "character_name": "Aria", "character_id": 1, "content": "I scout ahead."},
                {"user_id": 20, "display_name": "Bob", "character_name": "Borin", "character_id": 2, "content": "I cast a prayer."},
            ],
            session_id=10,
        )

        assert seen_contexts[0][2]["character_id"] == 2
        assert seen_contexts[0][2]["user_id"] == 20


class TestRuntimeSessionHelpers:
    @pytest.mark.asyncio
    async def test_resolve_runtime_session_prefers_character_session_id(self):
        db = SimpleNamespace(
            get_session=AsyncMock(return_value={"id": 12, "content_pack_id": "fantasy_core"}),
            get_session_by_channel=AsyncMock(),
            get_user_active_session=AsyncMock(),
            get_active_session=AsyncMock(),
        )

        session = await resolve_runtime_session(
            db,
            guild_id=67890,
            user_id=12345,
            channel_id=11111,
            character={"id": 77, "session_id": 12},
        )

        assert session["id"] == 12
        db.get_session.assert_awaited_once_with(12)
        db.get_session_by_channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_batched_messages_routes_tools_by_actor_name_fallback(self):
        class StubBatchDb(StubChatContextDb):
            async def get_character(self, character_id):
                characters = {
                    1: {"id": 1, "user_id": 10, "name": "Aria", "level": 3, "race": "Elf", "char_class": "Rogue", "hp": 18, "max_hp": 22, "gold": 10, "strength": 10, "dexterity": 16, "constitution": 12, "intelligence": 11, "wisdom": 13, "charisma": 14},
                    2: {"id": 2, "user_id": 20, "name": "Borin", "level": 3, "race": "Dwarf", "char_class": "Cleric", "hp": 24, "max_hp": 24, "gold": 8, "strength": 14, "dexterity": 9, "constitution": 16, "intelligence": 10, "wisdom": 15, "charisma": 11},
                }
                return characters.get(character_id)

            async def get_active_combat_by_session(self, session_id):
                return None

        seen_contexts = []

        class StubTools:
            async def execute_tool(self, tool_name, tool_args, context):
                seen_contexts.append((tool_name, tool_args, dict(context)))
                return "ok"

        class StubLlm:
            def __init__(self):
                self.calls = 0

            async def chat_with_tools(self, messages, tools):
                self.calls += 1
                if self.calls == 1:
                    return {
                        "content": "Resolving actions.",
                        "tool_calls": [{
                            "id": "call_1",
                            "function": {"name": "get_character_info", "arguments": '{"actor_name": "Borin"}'},
                        }],
                    }
                return {"content": "Done.", "tool_calls": []}

        handler = ChatHandler(
            StubBatchDb(),
            llm=StubLlm(),
            prompts=SimpleNamespace(get_dm_system_prompt=lambda: "prompt"),
            tool_schemas=SimpleNamespace(get_all_schemas=lambda: []),
            tools=StubTools(),
        )

        await handler.process_batched_messages(
            guild_id=123,
            channel_id=456,
            messages=[
                {"user_id": 10, "display_name": "Alice", "character_name": "Aria", "character_id": 1, "content": "I scout ahead."},
                {"user_id": 20, "display_name": "Bob", "character_name": "Borin", "character_id": 2, "content": "I cast a prayer."},
            ],
            session_id=10,
        )

        assert seen_contexts[0][2]["character_id"] == 2
        assert seen_contexts[0][2]["user_id"] == 20
