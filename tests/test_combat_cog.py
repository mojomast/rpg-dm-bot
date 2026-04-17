"""Focused tests for combat cog helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.cogs.combat import Combat, resolve_attack


@pytest.mark.asyncio
async def test_resolve_attack_applies_defending_ac_bonus(db, db_with_character, monkeypatch):
    db_from_fixture, char_id = db_with_character
    assert db is db_from_fixture

    encounter_id = await db.create_combat(67890, 11111)
    attacker = await db.get_character(char_id)
    target_id = await db.add_combatant(encounter_id, "enemy", 1, "Goblin", 10, 10, 0, is_player=False)
    await db.add_status_effect(target_id, "defending", duration=1)

    combatant = next(c for c in await db.get_combatants(encounter_id) if c['id'] == target_id)

    rolls = iter([8, 4])
    monkeypatch.setattr("src.cogs.combat.random.randint", lambda a, b: next(rolls))

    result = await resolve_attack(db, attacker, combatant)

    assert result['target_ac'] == 12
    assert result['hit'] is False


@pytest.mark.asyncio
async def test_resolve_attack_uses_persisted_combatant_armor_class(db, db_with_character, monkeypatch):
    db_from_fixture, char_id = db_with_character
    assert db is db_from_fixture

    encounter_id = await db.create_combat(67890, 11111)
    attacker = await db.get_character(char_id)
    target_id = await db.add_combatant(
        encounter_id,
        "enemy",
        1,
        "Goblin",
        10,
        10,
        0,
        is_player=False,
        armor_class=15,
        combat_stats={"ac": 15},
    )

    combatant = next(c for c in await db.get_combatants(encounter_id) if c['id'] == target_id)

    rolls = iter([11, 4])
    monkeypatch.setattr("src.cogs.combat.random.randint", lambda a, b: next(rolls))

    result = await resolve_attack(db, attacker, combatant)

    assert result['target_ac'] == 15
    assert result['hit'] is False


@pytest.mark.asyncio
async def test_start_combat_adds_session_party_members_not_just_initiator(db):
    session_id = await db.create_session(67890, "Test Campaign", 12345)
    stats_one = {"strength": 16, "dexterity": 14, "constitution": 15, "intelligence": 10, "wisdom": 12, "charisma": 8}
    stats_two = {"strength": 12, "dexterity": 10, "constitution": 14, "intelligence": 10, "wisdom": 15, "charisma": 11}
    char_one = await db.create_character(12345, 67890, "Aria", "human", "warrior", stats_one, session_id=session_id)
    char_two = await db.create_character(54321, 67890, "Borin", "dwarf", "cleric", stats_two, session_id=session_id)
    await db.add_session_player(session_id, char_one)
    await db.add_session_player(session_id, char_two)
    await db.bind_session_channel(session_id, 11111, set_primary=True)

    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=67890),
        channel=SimpleNamespace(id=11111),
        user=SimpleNamespace(id=12345),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(db=db)
    cog = Combat(bot)

    await Combat.start_combat.callback(cog, interaction)

    combat = await db.get_active_combat(67890, 11111)
    combatants = await db.get_combatants(combat['id'])
    names = {combatant['name'] for combatant in combatants}
    assert names == {"Aria", "Borin"}


@pytest.mark.asyncio
async def test_join_combat_uses_db_character_ac_snapshot(db, db_with_character):
    db_from_fixture, char_id = db_with_character
    assert db is db_from_fixture

    encounter_id = await db.create_combat(67890, 11111)
    await db.add_item(char_id, "armor_chain", "Chain Mail", "armor", is_equipped=True, slot="body", properties={"ac_base": 16, "max_dex_bonus": 0})
    await db.add_item(char_id, "shield_wooden", "Wooden Shield", "armor", is_equipped=True, slot="off_hand", properties={"ac_bonus": 2})

    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=67890),
        channel=SimpleNamespace(id=11111),
        user=SimpleNamespace(id=12345),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(db=db)
    cog = Combat(bot)

    await Combat.join_combat.callback(cog, interaction)

    combatant = (await db.get_combatants(encounter_id))[0]
    assert combatant['armor_class'] == 18
    assert combatant['combat_stats']['ac'] == 18
    assert combatant['combat_stats']['armor_class'] == 18


@pytest.mark.asyncio
async def test_spawn_enemy_uses_canonical_enemy_normalization(db):
    encounter_id = await db.create_combat(67890, 11111)

    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=67890),
        channel=SimpleNamespace(id=11111),
        user=SimpleNamespace(id=12345),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(db=db)
    cog = Combat(bot)

    await Combat.spawn_enemy.callback(cog, interaction, "Goblin", 7, 1)

    enemy = next(c for c in await db.get_combatants(encounter_id) if c['participant_type'] == 'enemy')
    assert enemy['armor_class'] == 10
    assert enemy['combat_stats']['ac'] == 10
    assert enemy['combat_stats']['armor_class'] == 10
