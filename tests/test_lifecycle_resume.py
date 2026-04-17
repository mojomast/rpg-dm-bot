"""Regression tests for canonical lifecycle resume delegation."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cogs.game_master import GameMaster
from src.cogs.game_master import SessionManageView
from src.cogs.game_persistence import GamePersistence
from src.cogs.sessions import Sessions


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
