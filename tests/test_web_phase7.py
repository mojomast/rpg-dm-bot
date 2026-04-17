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
async def test_location_connections_endpoint_round_trips_connection_metadata(db):
    api_module.db = db

    session_id = await db.create_session(
        guild_id=67890,
        name="Connection Session",
        dm_user_id=12345,
    )
    origin_id = await db.create_location(
        guild_id=67890,
        session_id=session_id,
        created_by=12345,
        name="Stonecross",
        description="A crossroads town.",
    )
    destination_id = await db.create_location(
        guild_id=67890,
        session_id=session_id,
        created_by=12345,
        name="Barrow Fen",
        description="Wetlands and burial mounds.",
        location_type="wilderness",
    )

    await api_module.create_location_connection_legacy(
        from_id=origin_id,
        to_id=destination_id,
        direction='east',
        travel_time=3,
        hidden=False,
    )

    response = await api_module.get_location_connections(origin_id)

    assert len(response['connections']) == 1
    assert response['connections'][0]['id'] == destination_id
    assert response['connections'][0]['name'] == 'Barrow Fen'
    assert response['connections'][0]['direction'] == 'east'
    assert response['connections'][0]['travel_time'] == 3


@pytest.mark.asyncio
async def test_canonical_location_connections_crud_endpoints(db):
    api_module.db = db

    session_id = await db.create_session(guild_id=67890, name='Canonical Connections', dm_user_id=12345)
    origin_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name='Keep')
    target_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name='Roadhouse')

    create_payload = api_module.LocationConnectionCreate(
        from_location_id=origin_id,
        to_location_id=target_id,
        direction='west',
        travel_time=4,
        hidden=False,
        bidirectional=True,
    )
    created = await api_module.create_location_connection(create_payload)

    listing = await api_module.list_location_connections(location_id=origin_id)
    assert len(listing['connections']) == 1
    assert listing['connections'][0]['id'] == created['id']
    assert listing['connections'][0]['from_location_name'] == 'Keep'
    assert listing['connections'][0]['to_location_name'] == 'Roadhouse'

    update_payload = api_module.LocationConnectionUpdate(direction='south', hidden=True)
    await api_module.update_location_connection(created['id'], update_payload)
    updated = await db.get_location_connection(created['id'])
    assert updated['direction'] == 'south'
    assert updated['hidden'] == 1
    assert updated['to_location_id'] == target_id

    deleted = await api_module.delete_location_connection(created['id'])
    assert deleted['message'] == 'Location connection deleted'
    assert await db.get_location_connection(created['id']) is None


@pytest.mark.asyncio
async def test_canonical_location_connection_update_can_change_target(db):
    api_module.db = db

    session_id = await db.create_session(guild_id=67890, name='Connection Retarget', dm_user_id=12345)
    origin_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name='Bridge')
    old_target_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name='North Road')
    new_target_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name='South Road')

    created = await api_module.create_location_connection(api_module.LocationConnectionCreate(
        from_location_id=origin_id,
        to_location_id=old_target_id,
        direction='road',
    ))

    await api_module.update_location_connection(
        created['id'],
        api_module.LocationConnectionUpdate(to_location_id=new_target_id, travel_time=2),
    )

    updated = await db.get_location_connection(created['id'])
    assert updated['to_location_id'] == new_target_id
    assert updated['travel_time'] == 2


@pytest.mark.asyncio
async def test_npc_create_and_update_use_canonical_location_id(db):
    api_module.db = db

    session_id = await db.create_session(guild_id=67890, name='NPC Location Session', dm_user_id=12345)
    square_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name='Market Square')
    inn_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name='Copper Cup Inn')

    create_payload = api_module.NPCCreate(
        guild_id=67890,
        session_id=session_id,
        name='Mira',
        description='A broker of rumors.',
        personality='Measured',
        npc_type='neutral',
        location_id=square_id,
        created_by=12345,
    )
    created = await api_module.create_npc(create_payload)

    created_npc = await db.get_npc(created['id'])
    assert created_npc['location_id'] == square_id
    assert created_npc['location'] == 'Market Square'

    update_payload = api_module.NPCUpdate(location_id=inn_id)
    await api_module.update_npc(created['id'], update_payload)

    updated_npc = await db.get_npc(created['id'])
    assert updated_npc['location_id'] == inn_id
    assert updated_npc['location'] == 'Copper Cup Inn'


@pytest.mark.asyncio
async def test_spawn_monster_template_endpoint_adds_enemy_participants(db):
    api_module.db = db
    api_module.tools = api_module.ToolExecutor(db)

    session_id = await db.create_session(
        guild_id=67890,
        name='Monster Spawn Session',
        dm_user_id=12345,
        description='Template spawn test',
    )
    await db.update_session(session_id, status='active', content_pack_id='fantasy_core')
    combat_id = await db.create_combat(guild_id=67890, channel_id=555, session_id=session_id)

    result = await api_module.spawn_combat_template_enemy(
        combat_id,
        api_module.CombatMonsterSpawn(template_id='goblin', count=2),
    )

    assert len(result['combatant_ids']) == 2
    participants = await db.get_combatants(combat_id)
    enemies = [participant for participant in participants if participant['participant_type'] == 'enemy']
    assert len(enemies) == 2
    assert enemies[0]['armor_class'] == 12
    assert enemies[0]['combat_stats']['template_id'] == 'goblin'


@pytest.mark.asyncio
async def test_enemy_templates_endpoint_lists_content_pack_monsters():
    response = await api_module.get_enemy_templates()

    assert response['templates']
    goblin = next(template for template in response['templates'] if template['id'] == 'goblin')
    assert goblin['name'] == 'Goblin'
    assert goblin['ac'] == 12


@pytest.mark.asyncio
async def test_story_item_update_endpoint_accepts_canonical_fields_and_aliases(db):
    api_module.db = db

    item_id = await db.create_story_item(
        guild_id=67890,
        session_id=None,
        name='Frost Ledger',
        created_by=12345,
    )

    payload = api_module.StoryItemUpdate(
        name='Frost Ledger Revised',
        item_type='clue',
        discovery_conditions='Search the archive vault',
        dm_notes='Points toward the cult treasury.',
        discovered=True,
    )

    await api_module.update_story_item(item_id, payload)

    item = await db.get_story_item(item_id)
    assert item['name'] == 'Frost Ledger Revised'
    assert item['item_type'] == 'clue'
    assert item['discovery_conditions'] == 'Search the archive vault'
    assert item['dm_notes'] == 'Points toward the cult treasury.'
    assert item['is_discovered'] == 1


@pytest.mark.asyncio
async def test_story_event_update_and_resolve_endpoints_use_canonical_statuses(db):
    api_module.db = db

    event_id = await db.create_story_event(
        guild_id=67890,
        session_id=None,
        name='Bell Tower Fire',
        created_by=12345,
    )

    update_payload = api_module.StoryEventUpdate(
        event_type='main_plot',
        trigger_conditions='When the wardstones fail',
        dm_notes='Escalates the city arc.',
        status='active',
    )
    await api_module.update_story_event(event_id, update_payload)

    triggered = await db.get_story_event(event_id)
    assert triggered['event_type'] == 'main_plot'
    assert triggered['trigger_conditions'] == 'When the wardstones fail'
    assert triggered['dm_notes'] == 'Escalates the city arc.'
    assert triggered['status'] == 'triggered'

    await api_module.resolve_story_event(event_id, outcome='partial', notes='The fire spreads before containment.')

    resolved = await db.get_story_event(event_id)
    assert resolved['status'] == 'resolved'
    assert resolved['resolution_outcome'] == 'partial'
    assert resolved['dm_notes'] == 'The fire spreads before containment.'


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
