"""Focused regression tests for Phase 7 slash-command/runtime hardening."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cogs.dm_chat import DMChat
from src.cogs.game_master import EquipmentShopView
from src.cogs.skills import Skills


@pytest.mark.asyncio
async def test_dm_chat_resolve_session_rejects_other_guild():
    db = SimpleNamespace(get_session=AsyncMock(return_value={"id": 7, "guild_id": 999}))
    cog = DMChat(SimpleNamespace(db=db, llm=None, tools=None))
    cog.get_active_session_id = AsyncMock(return_value=7)

    session = await cog.resolve_session(guild_id=123, user_id=1, channel_id=2)

    assert session is None


@pytest.mark.asyncio
async def test_skills_command_accepts_char_class_field(mock_interaction):
    db = SimpleNamespace(
        get_active_character=AsyncMock(
            return_value={"id": 1, "name": "Aria", "char_class": "warrior"}
        ),
        get_skill_points=AsyncMock(return_value={"available": 2, "spent": 0}),
        has_skill=AsyncMock(return_value=False),
    )
    bot = SimpleNamespace(db=db)
    cog = Skills(bot)

    await Skills.view_skills.callback(cog, mock_interaction)

    mock_interaction.response.send_message.assert_awaited_once()
    kwargs = mock_interaction.response.send_message.await_args.kwargs
    assert kwargs["ephemeral"] is True
    assert kwargs["embed"].title == "🌳 Warrior Skills Skill Tree"


@pytest.mark.asyncio
async def test_equipment_shop_finish_shopping_uses_remaining_gold():
    game_master = SimpleNamespace(
        active_interviews={
            123: {
                "shopping": {
                    "gold": 70,
                    "cart": [{"name": "Sword", "price": 30, "quantity": 1}],
                    "purchased": [],
                }
            }
        },
        complete_shopping=AsyncMock(),
        complete_character_interview=AsyncMock(),
    )
    interaction = MagicMock()
    interaction.user.id = 123
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()

    view = EquipmentShopView(game_master, user_id=123, guild_id=456, gold=70)

    await EquipmentShopView.finish_shopping(view, interaction, None)

    game_master.complete_shopping.assert_awaited_once_with(
        123,
        456,
        [{"name": "Sword", "price": 30, "quantity": 1}],
        70,
    )
