from __future__ import annotations

from tactics_game import config
from tactics_game.engine import ai, progression, queries, resolution
from tactics_game.models.ability import Ability
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Grid, Position
from tactics_game.models.hero import Hero

_DEFAULT_ATTRIBUTES = Attributes(might=1, focus=1, resolve=1, agility=1)


def _make_hero(
    name: str,
    position: Position,
    current_hp: int = 20,
    max_hp: int = 20,
    attributes: Attributes = _DEFAULT_ATTRIBUTES,
    is_player_controlled: bool = True,
) -> Hero:
    return Hero(
        name=name,
        attributes=attributes,
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=max_hp,
        current_hp=current_hp,
        position=position,
        is_player_controlled=is_player_controlled,
    )


def _grid() -> Grid:
    return Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)


def _ability(name: str, abilities: list[Ability]) -> Ability:
    return next(a for a in abilities if a.name == name)


# --- occupied_positions ---


def test_occupied_positions_excludes_actor_and_dead_heroes() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    ally = _make_hero("Ally", Position(1, 0))
    dead_enemy = _make_hero("Dead", Position(2, 0), current_hp=0, is_player_controlled=False)
    living_enemy = _make_hero("Enemy", Position(3, 0), is_player_controlled=False)

    occupied = queries.occupied_positions(actor, [actor, ally], [dead_enemy, living_enemy])

    assert occupied == {ally.position, living_enemy.position}


# --- reachable_destinations ---


def test_reachable_destinations_includes_own_tile_and_respects_bounds() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    grid = _grid()

    reachable = queries.reachable_destinations(actor, [actor], [], grid)

    assert actor.position in reachable
    assert all(grid.in_bounds(position) for position in reachable)
    # Corner with MOVEMENT_RANGE=3 on an open board: no negative coordinates
    # ever appear, since the grid boundary prunes them.
    assert all(position.x >= 0 and position.y >= 0 for position in reachable)


def test_reachable_destinations_excludes_occupied_tiles() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    blocker = _make_hero("Blocker", Position(1, 0), is_player_controlled=False)
    grid = _grid()

    reachable = queries.reachable_destinations(actor, [actor], [blocker], grid)

    assert blocker.position not in reachable


def test_reachable_destinations_finds_a_route_a_straight_walk_would_miss() -> None:
    # A hero blocking the direct path along the x-axis: a naive greedy,
    # single-path walk toward (2, 0) would stop dead at (0, 0) since its
    # first step is immediately blocked. A real flood-fill still finds
    # tiles reachable by detouring through open tiles within movement range.
    actor = _make_hero("Actor", Position(0, 0))
    blocker = _make_hero("Blocker", Position(1, 0), is_player_controlled=False)
    grid = _grid()

    reachable = queries.reachable_destinations(actor, [actor], [blocker], grid)

    # (0,0) -> (0,1) -> (1,1): 2 hops, well within MOVEMENT_RANGE=3, and
    # only reachable by stepping around the blocker.
    assert Position(1, 1) in reachable
    # (2,0) requires detouring all the way around the blocker (4 hops
    # minimum) which exceeds MOVEMENT_RANGE=3, so it's correctly excluded.
    assert Position(2, 0) not in reachable


# --- usable_abilities ---


def test_usable_abilities_excludes_ability_on_cooldown() -> None:
    hero = _make_hero("Hero", Position(0, 0))
    hero.cooldowns["Basic Mend"] = 2

    usable_names = {a.name for a in queries.usable_abilities(hero)}

    assert "Basic Mend" not in usable_names
    assert "Basic Strike" in usable_names


# --- valid_targets ---


def test_valid_targets_respects_min_and_max_range() -> None:
    caster = _make_hero("Caster", Position(0, 0))
    shot = _ability("Basic Shot", caster.abilities)  # min_range=2, range=4
    too_close = _make_hero("TooClose", Position(1, 0), is_player_controlled=False)
    in_range = _make_hero("InRange", Position(3, 0), is_player_controlled=False)
    too_far = _make_hero("TooFar", Position(5, 0), is_player_controlled=False)

    targets = queries.valid_targets(
        caster, shot, caster.position, [caster], [too_close, in_range, too_far]
    )

    assert targets == [in_range]


def test_valid_targets_uses_ally_pool_and_allows_self_for_ally_targeting() -> None:
    caster = _make_hero("Caster", Position(0, 0))
    mend = _ability("Basic Mend", caster.abilities)  # targets_ally, range=3
    ally = _make_hero("Ally", Position(1, 0))
    enemy = _make_hero("Enemy", Position(1, 0), is_player_controlled=False)

    targets = queries.valid_targets(caster, mend, caster.position, [caster, ally], [enemy])

    assert caster in targets
    assert ally in targets
    assert enemy not in targets


def test_valid_targets_excludes_dead_heroes() -> None:
    caster = _make_hero("Caster", Position(0, 0))
    strike = _ability("Basic Strike", caster.abilities)
    dead_enemy = _make_hero(
        "Dead", Position(1, 0), current_hp=0, is_player_controlled=False
    )

    targets = queries.valid_targets(caster, strike, caster.position, [caster], [dead_enemy])

    assert targets == []


def test_valid_targets_uses_hypothetical_position_not_actor_position() -> None:
    caster = _make_hero("Caster", Position(0, 0))
    strike = _ability("Basic Strike", caster.abilities)  # range=1
    enemy = _make_hero("Enemy", Position(5, 0), is_player_controlled=False)

    # Out of range from the caster's real position...
    assert queries.valid_targets(caster, strike, caster.position, [caster], [enemy]) == []
    # ...but in range from a hypothetical post-move position.
    assert queries.valid_targets(caster, strike, Position(4, 0), [caster], [enemy]) == [enemy]


# --- preview_ability_outcome ---


def test_preview_ability_outcome_does_not_mutate_caster_or_target() -> None:
    # A synthetic ability with a component that heals the caster — the
    # preview must scratch-copy the caster too, not just the target, or
    # "previewing" this option would actually apply the heal.
    component = resolution.EffectComponent(
        kind="heal",
        base=5,
        scaling=[resolution.ScalingTerm(attribute="resolve", multiplier=0)],
        verb="basks in victory, healing",
        applies_to="caster",
    )
    ability = Ability(
        name="Test Self-Heal Strike",
        range=1,
        targets_ally=False,
        effect=resolution.make_effect([component]),
    )
    caster = _make_hero("Caster", Position(0, 0), current_hp=10, max_hp=20)
    target = _make_hero(
        "Target", Position(1, 0), current_hp=10, max_hp=20, is_player_controlled=False
    )

    result = queries.preview_ability_outcome(caster, ability, target)

    assert result.healing == 5
    assert caster.current_hp == 10
    assert target.current_hp == 10


# --- acceptance criterion 1: AI and the query layer never disagree ---


def _assert_decision_is_legal(
    actor: Hero, allies: list[Hero], enemies: list[Hero], grid: Grid
) -> None:
    decision = ai.decide_turn(actor, allies, enemies, grid)

    if decision.destination is not None:
        assert decision.destination in queries.reachable_destinations(
            actor, allies, enemies, grid
        )

    if decision.ability_decision is not None:
        effective_position = decision.destination or actor.position
        ability = decision.ability_decision.ability
        target = decision.ability_decision.target
        assert ability in queries.usable_abilities(actor)
        assert target in queries.valid_targets(
            actor, ability, effective_position, allies, enemies
        )


def test_ai_decisions_are_always_legal_per_query_layer_open_field() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    enemy = _make_hero("Enemy", Position(5, 5), is_player_controlled=False)
    _assert_decision_is_legal(actor, [actor], [enemy], _grid())


def test_ai_decisions_are_always_legal_per_query_layer_ally_blocking_path() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    ally = _make_hero("Ally", Position(1, 0))
    enemy = _make_hero("Enemy", Position(5, 0), is_player_controlled=False)
    _assert_decision_is_legal(actor, [actor, ally], [enemy], _grid())


def test_ai_decisions_are_always_legal_per_query_layer_enemy_out_of_range() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    enemy = _make_hero("Enemy", Position(0, 11), is_player_controlled=False)
    _assert_decision_is_legal(actor, [actor], [enemy], _grid())


def test_ai_decisions_are_always_legal_per_query_layer_heal_on_cooldown() -> None:
    healer = _make_hero("Healer", Position(0, 0))
    healer.cooldowns["Basic Mend"] = 2
    injured_ally = _make_hero("Ally", Position(0, 2), current_hp=2, max_hp=20)
    enemy = _make_hero("Enemy", Position(5, 5), is_player_controlled=False)
    _assert_decision_is_legal(healer, [healer, injured_ally], [enemy], _grid())


def test_ai_decisions_are_always_legal_per_query_layer_injured_ally_in_range() -> None:
    healer = _make_hero("Healer", Position(0, 0))
    injured_ally = _make_hero("Ally", Position(0, 2), current_hp=2, max_hp=20)
    _assert_decision_is_legal(healer, [healer, injured_ally], [], _grid())
