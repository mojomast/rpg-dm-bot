"""Regression tests for canonical quest completion flow."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.cogs.quests import Quests


@pytest.mark.asyncio
async def test_complete_quest_command_distributes_rewards_to_session_participants(mock_interaction):
    db = SimpleNamespace(
        get_quest=AsyncMock(return_value={
            'id': 7,
            'title': 'Lost Relic',
            'status': 'in_progress',
            'session_id': 99,
            'rewards': {'xp': 50, 'gold': 100},
        }),
        get_session_participants=AsyncMock(return_value=[
            {'character_id': 101},
            {'character_id': 202},
        ]),
        complete_quest=AsyncMock(side_effect=[
            {'success': True, 'rewards': {'xp': 50, 'gold': 100}},
            {'success': True, 'rewards': {'xp': 50, 'gold': 100}},
        ]),
        get_character=AsyncMock(side_effect=[
            {'id': 101, 'name': 'Aria'},
            {'id': 202, 'name': 'Borin'},
        ]),
        update_quest=AsyncMock(),
    )
    cog = Quests(SimpleNamespace(db=db))

    await Quests.complete_quest.callback(cog, mock_interaction, 7)

    assert db.complete_quest.await_count == 2
    db.update_quest.assert_awaited_once()
    mock_interaction.response.send_message.assert_awaited_once()
    embed = mock_interaction.response.send_message.await_args.kwargs['embed']
    rewarded_field = next(field for field in embed.fields if field.name == 'Rewarded Characters')
    assert 'Aria' in rewarded_field.value
    assert 'Borin' in rewarded_field.value


@pytest.mark.asyncio
async def test_complete_quest_command_returns_early_when_already_completed(mock_interaction):
    db = SimpleNamespace(
        get_quest=AsyncMock(return_value={
            'id': 7,
            'title': 'Lost Relic',
            'status': 'completed',
            'session_id': 99,
            'rewards': {'xp': 50, 'gold': 100},
        }),
        get_session_participants=AsyncMock(),
        complete_quest=AsyncMock(),
        get_character=AsyncMock(),
        update_quest=AsyncMock(),
    )
    cog = Quests(SimpleNamespace(db=db))

    await Quests.complete_quest.callback(cog, mock_interaction, 7)

    db.get_session_participants.assert_not_called()
    db.complete_quest.assert_not_called()
    db.update_quest.assert_not_called()
    mock_interaction.response.send_message.assert_awaited_once()
    message = mock_interaction.response.send_message.await_args.args[0]
    assert 'already completed' in message
