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
async def test_finalize_campaign_persists_user_edited_preview_content(db):
    api_module.db = db

    payload = api_module.CampaignFinalize(
        guild_id=67890,
        dm_user_id=12345,
        name="Edited Campaign",
        description="Edited browser review content.",
        world_setting={
            "theme": "fantasy",
            "name": "Starfall Reach",
            "description": "A rewritten world description.",
            "history": "Ages of skyfire altered the realm.",
            "current_state": "Uneasy peace between city-states.",
        },
        locations=[
            {
                "id": "loc_harbor",
                "name": "Glassharbor",
                "type": "city",
                "description": "A glittering trade port.",
                "danger_level": 2,
                "points_of_interest": ["Sun Docks"],
                "connections": [],
            }
        ],
        npcs=[
            {
                "id": "npc_warden",
                "name": "Warden Sel",
                "type": "ally",
                "description": "Harbor master and fixer.",
                "personality": "Calm and incisive",
                "goals": "Keep the port stable",
                "location_id": "loc_harbor",
            }
        ],
        factions=[{"id": "faction_merchants", "name": "The Meridian League", "description": "A coalition of trade houses."}],
        quest_hooks=[
            {
                "id": "quest_signal",
                "title": "The Silent Beacon",
                "description": "Investigate why the sea beacon went dark.",
                "difficulty": "hard",
                "quest_giver_id": "npc_warden",
            }
        ],
        starting_scenario="The party arrives as emergency bells ring across Glassharbor.",
        generation_settings={"world_theme": "fantasy"},
    )

    result = await api_module.finalize_campaign(payload)

    session = await db.get_session(result["session_id"])
    assert session["name"] == "Edited Campaign"
    assert session["description"] == "Edited browser review content."

    game_state = await db.get_game_state(result["session_id"])
    assert game_state["current_scene"] == "The party arrives as emergency bells ring across Glassharbor."
    assert game_state["current_location"] == "Glassharbor"

    location = await db.get_location(game_state["current_location_id"])
    assert location["location_type"] == "city"
    assert location["danger_level"] == 2

    npcs = await db.get_npcs_by_session(result["session_id"])
    assert npcs[0]["name"] == "Warden Sel"
    assert npcs[0]["location"] == "Glassharbor"

    quests = await db.get_quests(session_id=result["session_id"])
    assert quests[0]["title"] == "The Silent Beacon"
    assert quests[0]["difficulty"] == "hard"


@pytest.mark.asyncio
async def test_finalize_campaign_preserves_links_after_client_side_additions(db):
    api_module.db = db

    payload = api_module.CampaignFinalize(
        guild_id=67890,
        dm_user_id=12345,
        name="Linked Campaign",
        description="Client-side additions should keep links.",
        world_setting={"theme": "fantasy", "name": "Linked Realm"},
        locations=[
            {
                "id": "loc_keep",
                "name": "Old Keep",
                "type": "fortress",
                "description": "A crumbling keep.",
                "danger_level": 3,
                "connections": [{"target_id": "loc_woods", "direction": "east", "travel_time": 1, "bidirectional": True}],
            },
            {
                "id": "loc_woods",
                "name": "Mistwoods",
                "type": "wilderness",
                "description": "Fog-shrouded trees.",
                "danger_level": 2,
                "connections": [],
            },
        ],
        npcs=[
            {
                "id": "npc_ranger",
                "name": "Tarin",
                "type": "ally",
                "description": "A scout from the woods.",
                "location_id": "loc_woods",
            }
        ],
        factions=[],
        quest_hooks=[
            {
                "id": "quest_path",
                "name": "Trail of Cinders",
                "description": "Follow the ash trail into the Mistwoods.",
                "quest_giver_id": "npc_ranger",
            }
        ],
        starting_scenario="Smoke rises from the keep.",
        generation_settings={"world_theme": "fantasy"},
    )

    result = await api_module.finalize_campaign(payload)

    game_state = await db.get_game_state(result["session_id"])
    keep_id = game_state["current_location_id"]
    nearby = await db.get_nearby_locations(keep_id)
    assert len(nearby) == 1
    assert nearby[0]["name"] == "Mistwoods"

    npcs = await db.get_npcs_by_session(result["session_id"])
    assert npcs[0]["location"] == "Mistwoods"
    assert npcs[0]["location_id"] is not None

    quests = await db.get_quests(session_id=result["session_id"])
    assert quests[0]["title"] == "Trail of Cinders"
    assert quests[0]["quest_giver_npc_id"] == npcs[0]["id"]


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


@pytest.mark.asyncio
async def test_snapshot_api_create_load_delete_round_trip(db, sample_character_stats):
    api_module.db = db

    session_id = await db.create_session(
        guild_id=67890,
        name="Snapshot API Session",
        dm_user_id=12345,
        description="Snapshot API test",
    )
    await db.update_session(session_id, status="active", world_theme="fantasy", content_pack_id="fantasy_core")
    location_id = await db.create_location(
        guild_id=67890,
        session_id=session_id,
        created_by=12345,
        name="Oakheart",
        description="Town center",
        location_type="town",
    )
    char_id = await db.create_character(
        user_id=12345,
        guild_id=67890,
        name="Aria",
        race="human",
        char_class="warrior",
        stats=sample_character_stats,
        session_id=session_id,
    )
    await db.join_session(session_id, user_id=12345, character_id=char_id)
    await db.save_game_state(
        session_id,
        current_scene="Snapshot scene",
        current_location="Oakheart",
        current_location_id=location_id,
        dm_notes="Original snapshot state",
        turn_count=2,
        game_data={"active_content_pack_id": "fantasy_core"},
    )

    created = await api_module.create_snapshot(
        api_module.SnapshotCreate(
            session_id=session_id,
            name="Checkpoint",
            created_by=12345,
            description="Manual checkpoint",
        )
    )
    snapshot_id = created["id"]

    await db.save_game_state(
        session_id,
        current_scene="Mutated scene",
        current_location="Elsewhere",
        current_location_id=None,
        dm_notes="Mutated",
        turn_count=0,
        game_data={},
    )

    snapshots = await api_module.list_snapshots(session_id)
    assert any(snapshot["id"] == snapshot_id for snapshot in snapshots["snapshots"])

    loaded = await api_module.load_snapshot(snapshot_id)
    assert loaded["success"] is True

    restored_state = await db.get_game_state(session_id)
    assert restored_state["current_scene"] == "Snapshot scene"
    assert restored_state["current_location"] == "Oakheart"
    assert restored_state["turn_count"] == 2

    deleted = await api_module.delete_snapshot(snapshot_id)
    assert deleted["message"] == "Snapshot deleted"

    snapshots_after_delete = await api_module.list_snapshots(session_id)
    assert all(snapshot["id"] != snapshot_id for snapshot in snapshots_after_delete["snapshots"])
