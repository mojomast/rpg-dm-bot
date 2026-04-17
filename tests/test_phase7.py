"""Focused regression tests for Phase 7 slash-command/runtime hardening."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cogs.dm_chat import DMChat
from src.cogs.inventory import Inventory
from src.cogs.game_master import EquipmentShopView
from src.cogs.combat import CombatView
from src.cogs.skills import Skills


@pytest.mark.asyncio
async def test_dm_chat_resolve_session_rejects_other_guild():
    db = SimpleNamespace(get_session=AsyncMock(return_value={"id": 7, "guild_id": 999}))
    cog = DMChat(SimpleNamespace(db=db, llm=None, prompts=None, tool_schemas=None, tools=None))
    cog.get_active_session_id = AsyncMock(return_value=7)

    session = await cog.resolve_session(guild_id=123, user_id=1, channel_id=2)

    assert session is None


@pytest.mark.asyncio
async def test_skills_command_accepts_char_class_field(mock_interaction):
    db = SimpleNamespace(
        get_active_character=AsyncMock(
            return_value={"id": 1, "name": "Aria", "char_class": "warrior", "session_id": 9}
        ),
        get_session=AsyncMock(return_value={"id": 9, "content_pack_id": "fantasy_core"}),
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
async def test_skill_info_uses_runtime_pack_content(mock_interaction):
    mock_interaction.guild_id = 67890
    db = SimpleNamespace(
        get_session_by_channel=AsyncMock(return_value={"id": 11, "content_pack_id": "fantasy_core"}),
        get_user_active_session=AsyncMock(return_value=None),
        get_active_session=AsyncMock(return_value=None),
    )
    bot = SimpleNamespace(db=db)
    cog = Skills(bot)

    await Skills.skill_info.callback(cog, mock_interaction, "Power Strike")

    db.get_session_by_channel.assert_awaited_once_with(67890, 11111, statuses=['active', 'paused', 'inactive'])
    kwargs = mock_interaction.response.send_message.await_args.kwargs
    assert kwargs["embed"].title.endswith("Power Strike")


@pytest.mark.asyncio
async def test_skill_name_autocomplete_uses_runtime_pack_content(mock_interaction):
    mock_interaction.guild_id = 67890
    db = SimpleNamespace(
        get_session_by_channel=AsyncMock(return_value={"id": 11, "content_pack_id": "fantasy_core"}),
        get_user_active_session=AsyncMock(return_value=None),
        get_active_session=AsyncMock(return_value=None),
    )
    bot = SimpleNamespace(db=db)
    cog = Skills(bot)

    choices = await cog.skill_name_autocomplete(mock_interaction, "power")

    assert any(choice.name == "Power Strike" for choice in choices)


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


@pytest.mark.asyncio
async def test_inventory_shop_uses_channel_bound_content_pack(mock_interaction):
    character = {"id": 1, "name": "Aria", "gold": 50, "session_id": 9}
    db = SimpleNamespace(
        get_active_character=AsyncMock(return_value=character),
        get_session=AsyncMock(return_value={"id": 9, "content_pack_id": "fantasy_core"}),
    )
    bot = SimpleNamespace(db=db)
    cog = Inventory(bot)

    custom_items = {
        "weapons": [{"id": "sun_blade", "name": "Sun Blade", "price": 25, "description": "Radiant edge", "type": "weapon", "rarity": "rare"}],
        "armor": [],
        "consumables": [],
        "accessories": [],
        "gear": [],
        "ammunition": [],
    }
    cog._get_item_content = AsyncMock(return_value=custom_items)

    await Inventory.shop.callback(cog, mock_interaction)

    cog._get_item_content.assert_awaited_once()
    kwargs = mock_interaction.response.send_message.await_args.kwargs
    assert kwargs["embed"].fields[0].name.startswith("🔵 Sun Blade")
    assert kwargs["view"].item_content["weapons"][0]["id"] == "sun_blade"


@pytest.mark.asyncio
async def test_inventory_quick_use_uses_character_session_pack_item_effects(mock_interaction):
    character = {"id": 1, "name": "Aria", "hp": 4, "max_hp": 12, "mana": 0, "max_mana": 5, "session_id": 9}
    item = {"id": 55, "item_id": "potion_special", "item_name": "Special Potion", "item_type": "consumable", "properties": {}, "quantity": 1}
    db = SimpleNamespace(
        get_active_character=AsyncMock(return_value=character),
        get_inventory=AsyncMock(return_value=[item]),
        get_character=AsyncMock(return_value=character),
        update_character=AsyncMock(),
        remove_item=AsyncMock(),
        get_session=AsyncMock(return_value={"id": 9, "content_pack_id": "fantasy_core"}),
    )
    bot = SimpleNamespace(db=db)
    cog = Inventory(bot)
    cog._get_item_content = AsyncMock(return_value={
        "weapons": [],
        "armor": [],
        "consumables": [{"id": "potion_special", "name": "Special Potion", "effect": {"type": "heal", "value": 7}}],
        "accessories": [],
        "gear": [],
        "ammunition": [],
    })

    await Inventory.quick_use.callback(cog, mock_interaction, "special")

    db.update_character.assert_awaited_once_with(1, hp=11)
    db.remove_item.assert_awaited_once_with(55, 1)
    kwargs = mock_interaction.response.send_message.await_args.kwargs
    assert "Restored **7** HP" in kwargs["embed"].description


@pytest.mark.asyncio
async def test_combat_item_button_uses_runtime_pack_item_effect(mock_interaction):
    character = {"id": 1, "name": "Aria", "hp": 5, "max_hp": 12, "mana": 0, "max_mana": 5, "session_id": 9}
    item = {"id": 77, "item_id": "battle_tonic", "item_name": "Battle Tonic", "item_type": "consumable", "quantity": 1}
    db = SimpleNamespace(
        get_active_character=AsyncMock(return_value=character),
        get_inventory=AsyncMock(return_value=[item]),
    )
    bot = SimpleNamespace(db=db)
    view = CombatView(bot, encounter_id=5, user_id=12345)
    view._get_item_content = AsyncMock(return_value={
        "weapons": [],
        "armor": [],
        "consumables": [{"id": "battle_tonic", "name": "Battle Tonic", "effect": {"type": "heal", "value": "1d4+1"}}],
        "accessories": [],
        "gear": [],
        "ammunition": [],
    })

    await CombatView.item_button(view, mock_interaction, None)

    view._get_item_content.assert_awaited_once()
    kwargs = mock_interaction.response.send_message.await_args.kwargs
    assert kwargs["view"].item_content["consumables"][0]["id"] == "battle_tonic"
