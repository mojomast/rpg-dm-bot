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
