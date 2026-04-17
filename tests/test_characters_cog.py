from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.cogs.characters import Characters


@pytest.mark.asyncio
async def test_character_create_delegates_to_canonical_interview_with_channel_context(mock_interaction):
    game_master = SimpleNamespace(start_character_interview_for_session=AsyncMock())
    bot = SimpleNamespace(db=SimpleNamespace(), get_cog=lambda name: game_master if name == 'GameMaster' else None)
    cog = Characters(bot)

    await Characters.create_character.callback(cog, mock_interaction)

    game_master.start_character_interview_for_session.assert_awaited_once_with(
        mock_interaction.user,
        mock_interaction.guild,
        channel_id=11111,
    )
    mock_interaction.response.send_message.assert_awaited_once()
    assert mock_interaction.response.send_message.await_args.kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_character_create_surfaces_error_when_game_master_missing(mock_interaction):
    bot = SimpleNamespace(db=SimpleNamespace(), get_cog=lambda name: None)
    cog = Characters(bot)

    await Characters.create_character.callback(cog, mock_interaction)

    mock_interaction.response.send_message.assert_awaited_once()
    kwargs = mock_interaction.response.send_message.await_args.kwargs
    assert kwargs["ephemeral"] is True
    assert "GameMaster cog is not loaded" in mock_interaction.response.send_message.await_args.args[0]
