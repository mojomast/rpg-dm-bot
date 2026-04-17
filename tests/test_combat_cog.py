"""Focused tests for combat cog helpers."""

import pytest

from src.cogs.combat import resolve_attack


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
