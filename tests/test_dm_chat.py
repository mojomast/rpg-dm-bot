"""Focused tests for DM chat helpers."""

from types import SimpleNamespace

import pytest

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
