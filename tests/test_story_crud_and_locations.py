"""Focused DB hardening tests for story CRUD and location traversal."""

import pytest


@pytest.mark.asyncio
async def test_story_item_crud_and_reveal_persist_location_state(db):
    session_id = await db.create_session(guild_id=67890, name="Story Item Session", dm_user_id=12345)
    location_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name="Vault")

    item_id = await db.create_story_item(
        guild_id=67890,
        session_id=session_id,
        name="Moon Key",
        created_by=12345,
        description="An engraved silver key.",
    )
    await db.update_story_item(item_id, location_id=location_id, discovered=True)
    await db.reveal_story_item(item_id)

    item = await db.get_story_item(item_id)
    items_at_location = await db.get_story_items_at_location(location_id)

    assert item["location_id"] == location_id
    assert item["is_discovered"] == 1
    assert items_at_location[0]["id"] == item_id


@pytest.mark.asyncio
async def test_story_event_trigger_and_resolve_persist_status_and_outcome(db):
    session_id = await db.create_session(guild_id=67890, name="Story Event Session", dm_user_id=12345)
    event_id = await db.create_story_event(
        guild_id=67890,
        session_id=session_id,
        name="Bridge Collapse",
        created_by=12345,
        description="The old bridge gives way.",
    )

    await db.trigger_event(event_id)
    triggered = await db.get_story_event(event_id)
    assert triggered["status"] == "triggered"
    assert triggered["triggered_at"] is not None

    await db.resolve_event(event_id, outcome="failure")
    resolved = await db.get_story_event(event_id)
    assert resolved["status"] == "resolved"
    assert resolved["resolution_outcome"] == "failure"
    assert resolved["resolved_at"] is not None


@pytest.mark.asyncio
async def test_adjacent_locations_follow_session_current_location(db):
    session_id = await db.create_session(guild_id=67890, name="Traversal Session", dm_user_id=12345)
    origin_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name="Gate")
    north_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name="North Road")
    east_id = await db.create_location(guild_id=67890, session_id=session_id, created_by=12345, name="East Road")

    await db.create_location_connection(origin_id, north_id, direction="north", travel_time=2)
    await db.create_location_connection(origin_id, east_id, direction="east", travel_time=1)
    await db.save_game_state(session_id, current_location="Gate", current_location_id=origin_id)

    adjacent = await db.get_adjacent_locations(session_id)
    names = {row["name"] for row in adjacent}
    directions = {row["direction"] for row in adjacent}

    assert names == {"North Road", "East Road"}
    assert directions == {"north", "east"}
