"""Regression tests for canonical lifecycle resume delegation."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cogs.game_master import GameMaster
from src.cogs.game_master import SessionManageView
from src.cogs.combat import Combat
from src.cogs.game_persistence import GamePersistence
from src.cogs.sessions import Sessions
from src.cogs.spells import Spells


@pytest.mark.asyncio
async def test_resume_game_without_session_id_delegates_to_sessions_cog(mock_interaction):
    sessions_cog = SimpleNamespace(resume_session=SimpleNamespace(callback=AsyncMock()))
    db = SimpleNamespace(
        get_sessions=AsyncMock(return_value=[{"id": 42, "guild_id": 67890, "dm_user_id": 12345, "status": "paused"}]),
    )
    bot = SimpleNamespace(db=db, llm=None, get_cog=lambda name: sessions_cog if name == 'Sessions' else None)
    cog = GamePersistence(bot)

    await GamePersistence.resume_game.callback(cog, mock_interaction, None)

    sessions_cog.resume_session.callback.assert_awaited_once_with(sessions_cog, mock_interaction, 42)
    mock_interaction.response.defer.assert_not_awaited()


@pytest.mark.asyncio
async def test_begin_game_resume_preserves_saved_location_state():
    db = SimpleNamespace(
        get_session=AsyncMock(return_value={
            "id": 7,
            "guild_id": 67890,
            "dm_user_id": 12345,
            "name": "Resumable Campaign",
            "description": "Adventure continues",
        }),
        get_session_players=AsyncMock(return_value=[{"character_id": 101}]),
        get_character=AsyncMock(return_value={
            "id": 101,
            "name": "Aria",
            "level": 2,
            "race": "Elf",
            "char_class": "Rogue",
            "backstory": "Scout of the north road",
        }),
        update_session=AsyncMock(),
        get_game_state=AsyncMock(return_value={
            "current_scene": "At the ruins",
            "current_location": "Rivergate",
            "current_location_id": 55,
        }),
        save_game_state=AsyncMock(),
    )
    llm = AsyncMock()
    llm.chat = AsyncMock(return_value="Previously on...")
    dm_chat = SimpleNamespace(bind_session_channel=AsyncMock())
    bot = SimpleNamespace(
        db=db,
        llm=llm,
        prompts=SimpleNamespace(get_game_start_prompt=lambda **kwargs: "prompt"),
        get_cog=lambda name: dm_chat if name == 'DMChat' else None,
    )
    cog = GameMaster(bot)
    interaction = MagicMock()
    interaction.guild = MagicMock()
    interaction.guild.id = 67890
    interaction.guild.get_member.return_value = None
    interaction.user = MagicMock()
    interaction.user.id = 12345
    interaction.channel = MagicMock()
    interaction.channel.id = 999
    interaction.response = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    await cog.begin_game(interaction, 7, resume=True)

    save_kwargs = db.save_game_state.await_args.kwargs
    assert save_kwargs["session_id"] == 7
    assert save_kwargs["current_scene"] == "At the ruins"
    assert save_kwargs["current_location"] == "Rivergate"
    assert save_kwargs["current_location_id"] == 55


@pytest.mark.asyncio
async def test_game_begin_command_delegates_to_sessions_cog(mock_interaction):
    sessions_cog = SimpleNamespace(start_session=SimpleNamespace(callback=AsyncMock()))
    bot = SimpleNamespace(db=None, llm=None, get_cog=lambda name: sessions_cog if name == 'Sessions' else None)
    cog = GameMaster(bot)

    await GameMaster.begin_game_cmd.callback(cog, mock_interaction, 77)

    sessions_cog.start_session.callback.assert_awaited_once_with(sessions_cog, mock_interaction, 77)


@pytest.mark.asyncio
async def test_game_pause_command_delegates_to_sessions_cog(mock_interaction):
    sessions_cog = SimpleNamespace(pause_session=SimpleNamespace(callback=AsyncMock()))
    bot = SimpleNamespace(db=None, llm=None, get_cog=lambda name: sessions_cog if name == 'Sessions' else None)
    cog = GameMaster(bot)

    await GameMaster.pause_game.callback(cog, mock_interaction, 88)

    sessions_cog.pause_session.callback.assert_awaited_once_with(sessions_cog, mock_interaction, 88)


@pytest.mark.asyncio
async def test_game_status_command_delegates_to_sessions_cog(mock_interaction):
    sessions_cog = SimpleNamespace(send_session_status=AsyncMock())
    bot = SimpleNamespace(db=None, llm=None, get_cog=lambda name: sessions_cog if name == 'Sessions' else None)
    cog = GameMaster(bot)

    await GameMaster.game_status.callback(cog, mock_interaction, 99)

    sessions_cog.send_session_status.assert_awaited_once_with(mock_interaction, 99)


@pytest.mark.asyncio
async def test_game_end_command_delegates_to_sessions_cog(mock_interaction):
    sessions_cog = SimpleNamespace(end_session_lifecycle=AsyncMock())
    bot = SimpleNamespace(db=None, llm=None, get_cog=lambda name: sessions_cog if name == 'Sessions' else None)
    cog = GameMaster(bot)

    await GameMaster.end_game.callback(cog, mock_interaction, 101)

    sessions_cog.end_session_lifecycle.assert_awaited_once_with(mock_interaction, 101)


@pytest.mark.asyncio
async def test_sessions_status_uses_canonical_session_listing(mock_interaction):
    db = SimpleNamespace(
        get_sessions=AsyncMock(return_value=[{
            "id": 5,
            "name": "Canon Session",
            "status": "active",
            "dm_user_id": 12345,
            "max_players": 4,
        }]),
        get_session_players=AsyncMock(return_value=[]),
        get_character=AsyncMock(),
    )
    bot = SimpleNamespace(db=db, get_cog=lambda _name: None)
    cog = Sessions(bot)

    await cog.send_session_status(mock_interaction, None)

    mock_interaction.response.send_message.assert_awaited_once()
    embed = mock_interaction.response.send_message.await_args.kwargs["embed"]
    assert embed.title == "🎲 Session Status"


@pytest.mark.asyncio
async def test_session_management_pause_button_delegates_to_sessions_cog(mock_interaction):
    sessions_cog = SimpleNamespace(pause_session=SimpleNamespace(callback=AsyncMock()))
    bot = SimpleNamespace(get_cog=lambda name: sessions_cog if name == 'Sessions' else None, db=SimpleNamespace())
    game_master = SimpleNamespace(bot=bot)
    view = SessionManageView(game_master, {"id": 22, "name": "Bound Session", "dm_user_id": 12345})

    await view.pause_game.callback(mock_interaction)

    sessions_cog.pause_session.callback.assert_awaited_once_with(sessions_cog, mock_interaction, 22)


@pytest.mark.asyncio
async def test_session_management_reset_history_persists_channel_binding(mock_interaction):
    dm_chat = SimpleNamespace(bind_session_channel=AsyncMock())
    bot = SimpleNamespace(get_cog=lambda name: dm_chat if name == 'DMChat' else None)
    game_master = SimpleNamespace(bot=bot)
    view = SessionManageView(game_master, {"id": 33, "name": "Bound Session", "dm_user_id": 12345})

    await view.reset_history.callback(mock_interaction)

    dm_chat.bind_session_channel.assert_awaited_once_with(67890, 11111, 33, set_primary=False)


@pytest.mark.asyncio
async def test_resume_game_without_session_id_prefers_channel_bound_paused_session(mock_interaction):
    sessions_cog = SimpleNamespace(resume_session=SimpleNamespace(callback=AsyncMock()))
    db = SimpleNamespace(
        get_session_by_channel=AsyncMock(return_value={"id": 77, "guild_id": 67890, "dm_user_id": 12345, "status": "paused"}),
    )
    bot = SimpleNamespace(db=db, llm=None, get_cog=lambda name: sessions_cog if name == 'Sessions' else None)
    cog = GamePersistence(bot)

    await GamePersistence.resume_game.callback(cog, mock_interaction, None)

    db.get_session_by_channel.assert_awaited_once_with(67890, 11111, statuses=['paused', 'inactive'])
    sessions_cog.resume_session.callback.assert_awaited_once_with(sessions_cog, mock_interaction, 77)


@pytest.mark.asyncio
async def test_current_quest_prefers_channel_bound_active_session(mock_interaction):
    db = SimpleNamespace(
        get_session_by_channel=AsyncMock(return_value={"id": 9, "name": "Bound Session", "current_quest_id": 55}),
        get_quest=AsyncMock(return_value={
            "id": 55,
            "title": "Bound Quest",
            "description": "In the right session",
            "difficulty": "medium",
            "status": "active",
            "objectives": [],
            "rewards": {},
        }),
    )
    bot = SimpleNamespace(db=db, llm=None)
    cog = GamePersistence(bot)

    await GamePersistence.current_quest.callback(cog, mock_interaction)

    db.get_session_by_channel.assert_awaited_once_with(67890, 11111, statuses=['active'])
    db.get_quest.assert_awaited_once_with(55)
    mock_interaction.response.send_message.assert_awaited_once()
    embed = mock_interaction.response.send_message.await_args.kwargs["embed"]
    assert embed.title == "📜 Bound Quest"


@pytest.mark.asyncio
async def test_story_auto_logging_prefers_channel_bound_session(mock_message):
    db = SimpleNamespace(
        get_session_by_channel=AsyncMock(return_value={"id": 91, "name": "Bound Session"}),
        add_story_entry=AsyncMock(),
    )
    bot = SimpleNamespace(db=db, user=SimpleNamespace(id=999))
    cog = GamePersistence(bot)

    mock_message.author.id = 999
    mock_message.content = "The goblin attacks and deals damage to the ranger."

    await cog.on_message(mock_message)

    db.get_session_by_channel.assert_awaited_once_with(67890, 11111, statuses=['active'])
    db.add_story_entry.assert_awaited_once()
    assert db.add_story_entry.await_args.kwargs["session_id"] == 91
    assert db.add_story_entry.await_args.kwargs["entry_type"] == "combat"


@pytest.mark.asyncio
async def test_combat_start_prefers_channel_bound_session(mock_interaction):
    db = SimpleNamespace(
        get_active_combat=AsyncMock(return_value=None),
        get_session_by_channel=AsyncMock(return_value={"id": 44}),
        get_user_active_session=AsyncMock(return_value=None),
        get_active_session=AsyncMock(return_value={"id": 12}),
        create_combat=AsyncMock(return_value=303),
        get_active_character=AsyncMock(return_value=None),
    )
    bot = SimpleNamespace(db=db)
    cog = Combat(bot)

    await Combat.start_combat.callback(cog, mock_interaction)

    db.get_session_by_channel.assert_awaited_once_with(67890, 11111, statuses=['active', 'paused', 'inactive'])
    db.create_combat.assert_awaited_once_with(guild_id=67890, channel_id=11111, session_id=44)


@pytest.mark.asyncio
async def test_start_character_interview_for_session_loads_pack_content(mock_interaction):
    dm_channel = SimpleNamespace(send=AsyncMock())
    user = SimpleNamespace(id=12345, create_dm=AsyncMock(return_value=dm_channel))
    guild = SimpleNamespace(id=67890, name="Pack Guild")
    db = SimpleNamespace(
        get_session=AsyncMock(return_value={"id": 88, "guild_id": 67890, "content_pack_id": "fantasy_core"}),
    )
    bot = SimpleNamespace(db=db, llm=None, prompts=SimpleNamespace())
    cog = GameMaster(bot)

    await cog.start_character_interview_for_session(user, guild, session_id=88)

    interview = cog.active_interviews[12345]
    assert interview["session_id"] == 88
    assert interview["content_pack_id"] == "fantasy_core"
    assert "warrior" in interview["content"]["classes"]["classes"]
    assert "human" in interview["content"]["races"]["races"]
    assert "class_kits" in interview["content"]["starter_kits"]
    assert dm_channel.send.await_count >= 2


@pytest.mark.asyncio
async def test_complete_character_interview_binds_session_and_provisions_gold_and_spells():
    db = SimpleNamespace(
        create_character=AsyncMock(return_value=501),
        get_character=AsyncMock(return_value={
            "id": 501,
            "name": "Lyra",
            "race": "Human",
            "char_class": "Mage",
            "level": 1,
            "hp": 6,
            "max_hp": 6,
            "backstory": "A curious scholar",
            "strength": 8,
            "dexterity": 12,
            "constitution": 10,
            "intelligence": 15,
            "wisdom": 13,
            "charisma": 14,
        }),
        add_item=AsyncMock(),
        update_gold=AsyncMock(),
        add_session_player=AsyncMock(),
        learn_spell=AsyncMock(),
        get_character_spells=AsyncMock(return_value=[]),
        get_equipped_items=AsyncMock(return_value=[]),
        get_inventory=AsyncMock(return_value=[]),
        set_spell_slots=AsyncMock(),
    )
    bot = SimpleNamespace(db=db, llm=None, prompts=SimpleNamespace())
    cog = GameMaster(bot)
    dm_channel = SimpleNamespace(send=AsyncMock())
    content = cog._load_interview_content({"content_pack_id": "fantasy_core"})
    cog.active_interviews[12345] = {
        "guild_id": 67890,
        "session_id": 88,
        "content_pack_id": "fantasy_core",
        "dm_channel": dm_channel,
        "responses": {
            "name": "Lyra",
            "race": "Human",
            "char_class": "Mage",
            "backstory": "A curious scholar",
        },
        "equipment": {
            "items": [{"id": "robe_mage", "name": "Mage's Robe", "type": "armor", "equipped": True}],
            "gold": 20,
        },
        "content": content,
    }

    await cog.complete_character_interview(12345)

    db.create_character.assert_awaited_once()
    assert db.create_character.await_args.kwargs["session_id"] == 88
    db.update_gold.assert_awaited_once_with(501, 20)
    db.add_session_player.assert_awaited_once_with(88, 501)
    assert db.learn_spell.await_count >= 1
    dm_channel.send.assert_awaited_once()
    assert 12345 not in cog.active_interviews


@pytest.mark.asyncio
async def test_spell_info_uses_channel_bound_content_pack(mock_interaction):
    db = SimpleNamespace(
        get_session_by_channel=AsyncMock(return_value={"id": 44, "content_pack_id": "fantasy_core"}),
        get_user_active_session=AsyncMock(return_value=None),
        get_active_session=AsyncMock(return_value=None),
    )
    bot = SimpleNamespace(db=db)
    cog = Spells(bot)

    await Spells.spell_info.callback(cog, mock_interaction, "fire bolt")

    db.get_session_by_channel.assert_awaited_once_with(67890, 11111, statuses=['active', 'paused', 'inactive'])
    mock_interaction.response.send_message.assert_awaited_once()
    embed = mock_interaction.response.send_message.await_args.kwargs["embed"]
    assert embed.title == "📖 Fire Bolt"


@pytest.mark.asyncio
async def test_spell_learn_uses_character_session_pack(mock_interaction):
    character = {
        "id": 501,
        "user_id": 12345,
        "session_id": 88,
        "name": "Lyra",
        "char_class": "Mage",
        "level": 1,
    }
    db = SimpleNamespace(
        get_active_character=AsyncMock(return_value=character),
        get_session=AsyncMock(return_value={"id": 88, "content_pack_id": "fantasy_core"}),
        get_character_spells=AsyncMock(return_value=[]),
    )
    bot = SimpleNamespace(db=db)
    cog = Spells(bot)

    await Spells.learn_spell.callback(cog, mock_interaction)

    db.get_session.assert_awaited_once_with(88)
    mock_interaction.response.send_message.assert_awaited_once()
    kwargs = mock_interaction.response.send_message.await_args.kwargs
    embed = kwargs["embed"]
    assert embed.title == "📚 Learn a New Spell"
    assert kwargs["view"] is not None
