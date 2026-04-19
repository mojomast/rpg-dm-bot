"""Focused tests for combat cog helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.cogs.combat import Combat, CombatItemView, CombatView, TargetSelectView, resolve_attack


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


@pytest.mark.asyncio
async def test_combat_item_use_rejects_when_not_players_turn(db, db_with_character):
    db_from_fixture, char_id = db_with_character
    assert db is db_from_fixture

    encounter_id = await db.create_combat(67890, 11111)
    await db.add_item(char_id, "mana_potion", "Mana Potion", "consumable", 1, properties={})
    player_participant = await db.add_combatant(encounter_id, "character", char_id, "Aria", 20, 20, 2, is_player=True)
    enemy_participant = await db.add_combatant(encounter_id, "enemy", 999, "Goblin", 10, 10, 3, is_player=False)
    await db.set_initiative_order(encounter_id, [enemy_participant, player_participant])
    await db.set_current_turn(encounter_id, 0)

    item = (await db.get_inventory(char_id))[0]
    interaction = SimpleNamespace(
        data={"values": [str(item['id'])]},
        guild=SimpleNamespace(id=67890),
        channel=SimpleNamespace(id=11111),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(db=db)
    view = CombatItemView(bot, encounter_id, await db.get_character(char_id), [item], {"consumables": [{"id": "mana_potion", "effect": {"type": "restore_mana", "value": 5}}]})

    await view.item_selected(interaction)

    interaction.response.send_message.assert_awaited_once_with("Not your turn!", ephemeral=True)


@pytest.mark.asyncio
async def test_failed_flee_consumes_turn(db, db_with_character, monkeypatch):
    db_from_fixture, char_id = db_with_character
    assert db is db_from_fixture

    encounter_id = await db.create_combat(67890, 11111)
    player_participant = await db.add_combatant(encounter_id, "character", char_id, "Aria", 20, 20, 2, is_player=True)
    enemy_participant = await db.add_combatant(encounter_id, "enemy", 999, "Goblin", 10, 10, 3, is_player=False)
    await db.set_initiative_order(encounter_id, [player_participant, enemy_participant])
    await db.set_current_turn(encounter_id, 0)

    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=67890),
        channel=SimpleNamespace(id=11111),
        user=SimpleNamespace(id=12345),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(db=db)
    view = CombatView(bot, encounter_id, 12345)
    monkeypatch.setattr("src.cogs.combat.random.randint", lambda a, b: 1)
    view._auto_advance_enemy_turns = AsyncMock()

    await CombatView.flee_button(view, interaction, None)

    current = await db.get_current_combatant(encounter_id)
    assert current['participant_type'] == 'enemy'


@pytest.mark.asyncio
async def test_target_select_uses_existing_combat_cog_for_auto_advance(db, db_with_character, monkeypatch):
    db_from_fixture, char_id = db_with_character
    assert db is db_from_fixture

    encounter_id = await db.create_combat(67890, 11111)
    player_participant = await db.add_combatant(encounter_id, "character", char_id, "Aria", 20, 20, 2, is_player=True)
    enemy_participant = await db.add_combatant(encounter_id, "enemy", 999, "Goblin", 10, 10, 0, is_player=False)
    await db.set_initiative_order(encounter_id, [player_participant, enemy_participant])
    await db.set_current_turn(encounter_id, 0)

    cog = SimpleNamespace(_auto_advance_enemy_turns=AsyncMock())
    bot = SimpleNamespace(db=db, get_cog=lambda name: cog if name == 'Combat' else None)
    interaction = SimpleNamespace(
        data={"values": [str(enemy_participant)]},
        guild=SimpleNamespace(id=67890),
        channel=SimpleNamespace(id=11111),
        user=SimpleNamespace(id=12345),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr("src.cogs.combat.random.randint", lambda a, b: 20 if b == 20 else 6)
    view = TargetSelectView(bot, encounter_id, [{"id": enemy_participant, "name": "Goblin", "current_hp": 10, "max_hp": 10}], "attack")

    await view.target_selected(interaction)

    cog._auto_advance_enemy_turns.assert_awaited_once()


@pytest.mark.asyncio
async def test_combat_item_use_uses_existing_combat_cog_for_auto_advance(db, db_with_character):
    db_from_fixture, char_id = db_with_character
    assert db is db_from_fixture

    encounter_id = await db.create_combat(67890, 11111)
    await db.add_item(char_id, "mana_potion", "Mana Potion", "consumable", 1, properties={})
    player_participant = await db.add_combatant(encounter_id, "character", char_id, "Aria", 20, 20, 2, is_player=True)
    enemy_participant = await db.add_combatant(encounter_id, "enemy", 999, "Goblin", 10, 10, 3, is_player=False)
    await db.set_initiative_order(encounter_id, [player_participant, enemy_participant])
    await db.set_current_turn(encounter_id, 0)
    await db.update_character(char_id, mana=0, max_mana=10)

    cog = SimpleNamespace(_auto_advance_enemy_turns=AsyncMock())
    bot = SimpleNamespace(db=db, get_cog=lambda name: cog if name == 'Combat' else None)
    item = (await db.get_inventory(char_id))[0]
    interaction = SimpleNamespace(
        data={"values": [str(item['id'])]},
        guild=SimpleNamespace(id=67890),
        channel=SimpleNamespace(id=11111),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    view = CombatItemView(bot, encounter_id, await db.get_character(char_id), [item], {"consumables": [{"id": "mana_potion", "effect": {"type": "restore_mana", "value": 5}}]})

    await view.item_selected(interaction)

    cog._auto_advance_enemy_turns.assert_awaited_once()


@pytest.mark.asyncio
async def test_next_turn_uses_refreshed_combat_for_auto_advance(db):
    encounter_id = await db.create_combat(67890, 11111)
    await db.add_combatant(encounter_id, "enemy", 999, "Goblin", 10, 10, 3, is_player=False)
    await db.set_initiative_order(encounter_id, [1])
    await db.set_current_turn(encounter_id, 0)

    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=67890),
        channel=SimpleNamespace(id=11111),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(db=db)
    cog = Combat(bot)
    cog._auto_advance_enemy_turns = AsyncMock()

    await Combat.next_turn.callback(cog, interaction)

    cog._auto_advance_enemy_turns.assert_awaited_once()


@pytest.mark.asyncio
async def test_persistent_game_actions_view_contains_only_static_info_buttons():
    from src.cogs.dm_chat import GameActionsView, InfoButton, PlayerActionButton

    view = GameActionsView(cog=None, options=None, timeout=None)

    assert all(isinstance(item, InfoButton) for item in view.children)
    assert not any(isinstance(item, PlayerActionButton) for item in view.children)
    assert [item.custom_id for item in view.children] == [
        "info_character",
        "info_quest",
        "info_location",
        "info_inventory",
        "info_party",
    ]
