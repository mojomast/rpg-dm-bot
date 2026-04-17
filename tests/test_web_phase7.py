"""Regression tests for campaign finalization and browser chat continuity."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import web.api as api_module
from src.chat_web_identity import web_user_id_from_uuid


@pytest.mark.asyncio
async def test_finalize_campaign_persists_playable_session_state(db):
    api_module.db = db

    payload = api_module.CampaignFinalize(
        guild_id=67890,
        dm_user_id=12345,
        name="Playable Campaign",
        description="A finalized campaign ready for browser play.",
        world_setting={"theme": "fantasy", "name": "Mythreach"},
        locations=[
            {
                "id": "loc_town",
                "name": "Oakheart",
                "type": "town",
                "description": "A trading town.",
                "danger_level": 1,
                "points_of_interest": ["Market Square", "Old Keep"],
                "connections": [
                    {
                        "target_id": "loc_forest",
                        "direction": "north",
                        "travel_time": 2,
                        "bidirectional": True,
                    }
                ],
            },
            {
                "id": "loc_forest",
                "name": "Whisperwood",
                "type": "wilderness",
                "description": "Dark pines and old ruins.",
                "danger_level": 3,
                "points_of_interest": ["Moon Shrine"],
                "connections": [],
            },
        ],
        npcs=[],
        factions=[],
        quest_hooks=[],
        starting_scenario="The road leads into Oakheart.",
        generation_settings={"world_theme": "fantasy"},
    )

    result = await api_module.finalize_campaign(payload)

    session = await db.get_session(result["session_id"])
    assert session["status"] == "active"
    assert session["world_theme"] == "fantasy"
    assert session["content_pack_id"] == "fantasy_core"

    game_state = await db.get_game_state(result["session_id"])
    assert game_state["current_location"] == "Oakheart"
    assert game_state["current_location_id"] is not None
    dm_notes = json.loads(game_state["dm_notes"])
    assert dm_notes["active_content_pack_id"] == "fantasy_core"

    starting_location = await db.get_location(game_state["current_location_id"])
    assert starting_location["name"] == "Oakheart"
    assert "Market Square" in json.loads(starting_location["points_of_interest"])

    nearby = await db.get_nearby_locations(game_state["current_location_id"])
    assert len(nearby) == 1
    assert nearby[0]["name"] == "Whisperwood"
    assert nearby[0]["direction"] == "north"


@pytest.mark.asyncio
async def test_chat_bootstrap_and_chat_validate_session_bound_character(db):
    api_module.db = db
    api_module.chat_handler = SimpleNamespace(
        process_single_message=AsyncMock(
            return_value={
                "response": "The DM answers.",
                "mechanics_text": "",
                "tool_results": [],
                "user_message": {"content": "hello"},
                "assistant_message": {"content": "The DM answers."},
            }
        ),
        extract_response_options=lambda _response: [],
    )

    session_id = await db.create_session(
        guild_id=67890,
        name="Browser Session",
        dm_user_id=12345,
        description="Browser continuity test",
    )
    await db.update_session(session_id, status="active", world_theme="fantasy", content_pack_id="fantasy_core")

    location_id = await db.create_location(
        guild_id=67890,
        session_id=session_id,
        created_by=12345,
        name="Rivergate",
        description="The party staging ground.",
        location_type="town",
        points_of_interest=["Docks"],
    )
    await db.save_game_state(
        session_id,
        current_scene="The party arrives.",
        current_location="Rivergate",
        current_location_id=location_id,
        game_data={"active_content_pack_id": "fantasy_core"},
    )

    char_id = await db.create_character(
        user_id=12345,
        guild_id=67890,
        name="Aria",
        race="human",
        char_class="warrior",
        stats={
            "strength": 14,
            "dexterity": 12,
            "constitution": 13,
            "intelligence": 10,
            "wisdom": 11,
            "charisma": 9,
        },
        session_id=session_id,
    )
    await db.join_session(session_id, user_id=12345, character_id=char_id)

    other_char_id = await db.create_character(
        user_id=54321,
        guild_id=67890,
        name="Outsider",
        race="elf",
        char_class="mage",
        stats={
            "strength": 8,
            "dexterity": 12,
            "constitution": 10,
            "intelligence": 15,
            "wisdom": 12,
            "charisma": 10,
        },
    )

    identity = "11111111-1111-4111-8111-111111111111"
    await db.create_web_identity(identity, "hashed-ip")
    web_user_id = web_user_id_from_uuid(identity)
    synthetic_channel_id = web_user_id_from_uuid(f"web-session:{session_id}:user:{identity}")
    await db.save_message(web_user_id, 67890, synthetic_channel_id, "assistant", "Welcome back.", session_id=session_id)

    bootstrap = await api_module.get_chat_bootstrap(session_id=session_id, character_id=char_id, x_web_identity=identity)

    assert bootstrap.session["id"] == session_id
    assert bootstrap.available_characters[0]["character_id"] == char_id
    assert bootstrap.game_state["current_location_id"] == location_id
    assert bootstrap.location["name"] == "Rivergate"
    assert bootstrap.recent_messages[-1]["content"] == "Welcome back."

    with pytest.raises(api_module.HTTPException) as invalid_bootstrap:
        await api_module.get_chat_bootstrap(session_id=session_id, character_id=other_char_id, x_web_identity=identity)
    assert invalid_bootstrap.value.status_code == 400

    request = api_module.ChatRequest(session_id=session_id, character_id=char_id, message="hello")
    response = await api_module.chat_with_dm.__wrapped__(
        http_request=SimpleNamespace(headers={}),
        request=request,
        x_web_identity=identity,
    )
    assert response.session_id == session_id
    assert response.response == "The DM answers."

    with pytest.raises(api_module.HTTPException) as invalid_chat:
        await api_module.chat_with_dm.__wrapped__(
            http_request=SimpleNamespace(headers={}),
            request=api_module.ChatRequest(session_id=session_id, character_id=other_char_id, message="hello"),
            x_web_identity=identity,
        )
    assert invalid_chat.value.status_code == 400


@pytest.mark.asyncio
async def test_create_browser_character_attaches_to_session(db):
    api_module.db = db

    session_id = await db.create_session(
        guild_id=67890,
        name="Fresh Browser Session",
        dm_user_id=12345,
        description="Fresh onboarding test",
    )
    await db.update_session(session_id, status="active", world_theme="fantasy", content_pack_id="fantasy_core")

    identity = "22222222-2222-4222-8222-222222222222"
    await db.create_web_identity(identity, "hashed-ip")
    web_user_id = web_user_id_from_uuid(identity)

    response = await api_module.create_browser_character(
        character=api_module.BrowserCharacterCreate(
            session_id=session_id,
            name="Mira",
            race="human",
            char_class="warrior",
            backstory="A caravan guard looking for work.",
        ),
        x_web_identity=identity,
    )

    assert response["character"]["name"] == "Mira"
    assert response["character"]["session_id"] == session_id

    participants = await db.get_session_participants(session_id)
    assert len(participants) == 1
    assert participants[0]["user_id"] == web_user_id
    assert participants[0]["character_id"] == response["character"]["id"]

    with pytest.raises(api_module.HTTPException) as duplicate:
        await api_module.create_browser_character(
            character=api_module.BrowserCharacterCreate(
                session_id=session_id,
                name="Second Hero",
                race="elf",
                char_class="mage",
            ),
            x_web_identity=identity,
        )
    assert duplicate.value.status_code == 400
