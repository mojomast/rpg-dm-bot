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


class TestDMChatHelpers:
    def test_extract_response_options(self):
        cog = DMChat(SimpleNamespace(db=None, llm=None, tools=None))

        options = cog.extract_response_options(
            "1. Open the door\n2) Search the room\n3. Talk to the guard"
        )

        assert options == ["Open the door", "Search the room", "Talk to the guard"]

    def test_clear_all_guild_histories_filters_by_guild(self):
        cog = DMChat(SimpleNamespace(db=None, llm=None, tools=None))
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
