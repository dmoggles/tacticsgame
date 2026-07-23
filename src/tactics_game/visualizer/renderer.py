from __future__ import annotations

import pygame

from .. import config
from ..engine import class_track_library, telemetry
from ..engine.battle import Battle
from ..engine.hero_delta import HeroDelta
from ..engine.session import Session
from ..models.attributes import AttributeName
from ..models.grid import Grid, Position
from ..models.hero import Hero
from .between_battle_screen import BetweenBattleController, BetweenBattlePhase
from .player_input import InputPhase, PlayerTurnController

BACKGROUND_COLOR = (24, 24, 24)
SIDEBAR_COLOR = (16, 16, 16)
CARD_BACKGROUND_COLOR = (34, 34, 34)
GRID_LINE_COLOR = (70, 70, 70)
PLAYER_COLOR = (70, 130, 220)
ENEMY_COLOR = (220, 80, 80)
DEAD_COLOR = (90, 90, 90)
TEXT_COLOR = (230, 230, 230)
SELECTABLE_HIGHLIGHT_COLOR = (240, 220, 80, 110)
REACHABLE_HIGHLIGHT_COLOR = (80, 200, 120, 90)
TARGET_HIGHLIGHT_COLOR = (220, 80, 80, 140)
PENDING_ALLOCATION_COLOR = (220, 160, 60)

_ABILITY_SLOT_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)
_ATTRIBUTE_SLOT_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)
_ATTRIBUTE_SLOT_ORDER = (
    AttributeName.MIGHT,
    AttributeName.FOCUS,
    AttributeName.RESOLVE,
    AttributeName.AGILITY,
)


def run(battle: Battle, max_frames: int | None = None, session: Session | None = None) -> None:
    """Interactive debug visualizer. The player controls player-side
    heroes' turns (click/keys, see the module docstring in
    visualizer/player_input.py for the interaction model); the AI keeps
    controlling the enemy side. A toggles full AI-vs-AI auto-play. I
    instantly resolves the rest of the current battle — identical rules to
    auto-play (every remaining turn, either side, decided by ai.decide_turn
    via Battle.run_to_completion()), just without the per-turn pacing. C
    toggles the hero card view, Esc cancels the in-progress turn (or
    quits if there's nothing to cancel).

    The visualizer never computes legality itself — all of it comes from
    engine/queries.py via PlayerTurnController — and never mutates Battle
    state except through Battle.take_turn()/Battle.step()/Session.advance().

    `max_frames` bounds the loop for scripted/headless testing; production
    callers leave it `None` and quit via the window/Esc.

    `session`, if given, chains battles: `battle` must be
    `session.current_battle`. Once it ends, the session is scored
    immediately (so its state is accurate right away). If another battle is
    coming, control hands to the between-battle screen (docs/04_phase2b_
    definition.md section 6) — resolve any pending manual attribute
    allocations (1-4 to choose, SPACE to let affinity decide), then click
    roster heroes to choose the fielded squad and press Enter to start the
    next battle. Omit `session` to play a single standalone battle,
    unchanged from before session chaining existed.
    """
    pygame.init()
    grid_width_px = battle.grid.width * config.TILE_SIZE_PX
    grid_height_px = battle.grid.height * config.TILE_SIZE_PX
    battle_view_width = grid_width_px + config.SIDEBAR_WIDTH_PX
    battle_view_height = grid_height_px + config.MESSAGE_BAR_HEIGHT_PX
    battle_view_size = (battle_view_width, battle_view_height)
    screen = pygame.display.set_mode(battle_view_size)
    pygame.display.set_caption("Tactics Game — Debug Visualizer")
    font = pygame.font.SysFont("consolas", 16)
    clock = pygame.time.Clock()

    auto_play = False
    time_since_step = 0
    show_cards = False
    controller: PlayerTurnController | None = None
    between_battle: BetweenBattleController | None = None

    running = True
    frame_count = 0
    while running:
        if max_frames is not None and frame_count >= max_frames:
            break
        frame_count += 1
        dt = clock.tick(60)

        if between_battle is None and battle.is_over:
            controller = None
            # Score the finished battle into the session immediately, once,
            # the moment it ends — session.current_battle becomes a new
            # object as a side effect when the session continues, which is
            # what guards this against re-running on later frames. Once the
            # session itself is over, current_battle stops changing (there's
            # nothing left to play), so `not session.is_over` is what
            # guards *that* case — Session.advance() is a no-op once over
            # too, but this loop shouldn't rely on that alone.
            if session is not None and not session.is_over and session.current_battle is battle:
                session.advance()
                if session.is_over:
                    if config.TELEMETRY_ENABLED:
                        telemetry.write_session_report(session)
                elif session.current_battle is None:
                    between_battle = BetweenBattleController(session=session)
                    screen = pygame.display.set_mode(_between_battle_view_size(len(session.roster)))

        if between_battle is not None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif (
                        between_battle is not None
                        and between_battle.phase == BetweenBattlePhase.ALLOCATING
                    ):
                        attribute = _attribute_slot(event.key)
                        if attribute is not None:
                            between_battle.choose_manual_attribute(attribute)
                        elif event.key == pygame.K_SPACE:
                            between_battle.choose_manual_attribute(None)
                    elif (
                        between_battle is not None
                        and event.key == pygame.K_RETURN
                        and between_battle.is_ready
                    ):
                        between_battle.confirm()
                        assert session is not None
                        next_battle = session.current_battle
                        assert next_battle is not None
                        battle = next_battle
                        between_battle = None
                        screen = pygame.display.set_mode(battle_view_size)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if (
                        between_battle is not None
                        and between_battle.phase != BetweenBattlePhase.ALLOCATING
                    ):
                        hero = _roster_row_at(event.pos, between_battle.session.roster)
                        if hero is not None:
                            between_battle.toggle_fielded(hero)

            screen.fill(BACKGROUND_COLOR)
            if between_battle is not None:
                _draw_between_battle_screen(screen, between_battle, font)
            pygame.display.flip()
            continue

        if not battle.is_over:
            actor = battle.current_actor
            if actor is not None and actor.is_player_controlled and not auto_play:
                if controller is None or controller.actor is not actor:
                    controller = PlayerTurnController(
                        actor=actor,
                        allies=battle.player_squad,
                        enemies=battle.enemy_squad,
                        grid=battle.grid,
                    )
            else:
                controller = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if controller is not None and controller.cancel():
                        pass
                    else:
                        running = False
                elif event.key == pygame.K_a:
                    auto_play = not auto_play
                    time_since_step = 0
                    controller = None
                elif event.key == pygame.K_i:
                    if not battle.is_over:
                        battle.run_to_completion()
                        auto_play = False
                        time_since_step = 0
                        controller = None
                elif event.key == pygame.K_c:
                    show_cards = not show_cards
                    # The card view needs more room than the battle view —
                    # resize the window to fit it exactly, rather than
                    # cramming cards into the fixed battle-view size (which
                    # was clipping ability text past the card/window edge).
                    size = (
                        _card_view_size(len(battle.all_heroes), font)
                        if show_cards
                        else battle_view_size
                    )
                    screen = pygame.display.set_mode(size)
                elif event.key == pygame.K_TAB:
                    if controller is not None:
                        controller.select_active_hero()
                elif event.key == pygame.K_SPACE:
                    if controller is not None and controller.phase == InputPhase.MOVING:
                        controller.skip_move()
                    elif controller is not None and controller.phase == InputPhase.ACTING:
                        controller.skip_ability()
                    elif controller is None and not auto_play and not battle.is_over:
                        battle.step()
                elif event.key == pygame.K_RETURN:
                    if controller is not None and controller.is_ready:
                        battle.take_turn(controller.actor, controller.build_decision())
                        controller = None
                elif controller is not None and controller.phase == InputPhase.ACTING:
                    index = _ability_slot_key_index(event.key)
                    if index is not None and index < len(controller.actor.abilities):
                        controller.choose_ability(controller.actor.abilities[index])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if controller is not None and not show_cards:
                    tile = _pixel_to_tile(event.pos, battle.grid)
                    if tile is not None:
                        if controller.phase == InputPhase.IDLE:
                            if tile == controller.actor.position:
                                controller.select_active_hero()
                        elif controller.phase == InputPhase.MOVING:
                            if tile == controller.actor.position:
                                controller.skip_move()
                            else:
                                controller.choose_destination(tile)
                        elif controller.phase == InputPhase.TARGETING:
                            controller.choose_target(tile)

        if auto_play and not battle.is_over:
            time_since_step += dt
            if time_since_step >= config.AUTO_PLAY_INTERVAL_MS:
                battle.step()
                time_since_step = 0

        screen.fill(BACKGROUND_COLOR)
        if show_cards:
            _draw_hero_cards(screen, battle, font)
        else:
            _draw_grid(screen, battle.grid)
            if controller is not None:
                _draw_controller_highlights(screen, controller)
            for hero in battle.all_heroes:
                _draw_hero(screen, hero, font)
            _draw_sidebar(screen, battle, font, grid_width_px, grid_height_px, controller)
            _draw_message_bar(screen, battle, font, grid_height_px, battle_view_width, session)
        pygame.display.flip()

    pygame.quit()


def _pixel_to_tile(pos: tuple[int, int], grid: Grid) -> Position | None:
    x, y = pos
    if x < 0 or y < 0:
        return None
    candidate = Position(x // config.TILE_SIZE_PX, y // config.TILE_SIZE_PX)
    return candidate if grid.in_bounds(candidate) else None


def _ability_slot_key_index(key: int) -> int | None:
    return _ABILITY_SLOT_KEYS.index(key) if key in _ABILITY_SLOT_KEYS else None


def _draw_grid(screen: pygame.Surface, grid: Grid) -> None:
    grid_width_px = grid.width * config.TILE_SIZE_PX
    grid_height_px = grid.height * config.TILE_SIZE_PX
    for x in range(grid.width + 1):
        px = x * config.TILE_SIZE_PX
        pygame.draw.line(screen, GRID_LINE_COLOR, (px, 0), (px, grid_height_px))
    for y in range(grid.height + 1):
        py = y * config.TILE_SIZE_PX
        pygame.draw.line(screen, GRID_LINE_COLOR, (0, py), (grid_width_px, py))


def _draw_highlight_tile(screen: pygame.Surface, position: Position, color: tuple[int, int, int, int]) -> None:
    overlay = pygame.Surface((config.TILE_SIZE_PX, config.TILE_SIZE_PX), pygame.SRCALPHA)
    overlay.fill(color)
    screen.blit(overlay, (position.x * config.TILE_SIZE_PX, position.y * config.TILE_SIZE_PX))


def _draw_controller_highlights(screen: pygame.Surface, controller: PlayerTurnController) -> None:
    """Every highlighted tile comes straight from engine/queries.py via
    the controller — never computed here."""
    if controller.phase == InputPhase.IDLE:
        _draw_highlight_tile(screen, controller.actor.position, SELECTABLE_HIGHLIGHT_COLOR)
    elif controller.phase == InputPhase.MOVING:
        for tile in controller.reachable_tiles:
            _draw_highlight_tile(screen, tile, REACHABLE_HIGHLIGHT_COLOR)
    elif controller.phase == InputPhase.TARGETING:
        for target in controller.valid_targets:
            _draw_highlight_tile(screen, target.position, TARGET_HIGHLIGHT_COLOR)


def _draw_hero(screen: pygame.Surface, hero: Hero, font: pygame.font.Font) -> None:
    if not hero.is_alive:
        color = DEAD_COLOR
    elif hero.is_player_controlled:
        color = PLAYER_COLOR
    else:
        color = ENEMY_COLOR

    center = (
        hero.position.x * config.TILE_SIZE_PX + config.TILE_SIZE_PX // 2,
        hero.position.y * config.TILE_SIZE_PX + config.TILE_SIZE_PX // 2,
    )
    radius = config.TILE_SIZE_PX // 2 - 6
    pygame.draw.circle(screen, color, center, radius)

    label = font.render(f"{hero.current_hp}/{hero.max_hp}", True, TEXT_COLOR)
    screen.blit(label, (center[0] - label.get_width() // 2, center[1] + radius + 2))


def _controller_prompt_lines(battle: Battle, controller: PlayerTurnController | None) -> list[str]:
    """Context-sensitive hint text for the sidebar, reflecting whichever
    stage of a player turn (if any) is in progress. Ability lines carry
    the ability's class track (docs/03_phase2a_definition.md section 3:
    class XP accrual must be visible while choosing, not just after)."""
    if battle.is_over:
        return []
    actor = battle.current_actor
    if actor is None:
        return []
    if controller is None:
        return [f"{actor.name}'s turn (AI) — SPACE to resolve, A for auto-play"]
    if controller.phase == InputPhase.IDLE:
        return [f"{actor.name}'s turn — click the hero or TAB to begin"]
    if controller.phase == InputPhase.MOVING:
        return [f"{actor.name}: click a highlighted tile to move, SPACE to skip, ESC to deselect"]
    if controller.phase == InputPhase.ACTING:
        lines = [f"{actor.name}: choose an ability (1-4), SPACE to skip, ESC to reconsider move"]
        lines.extend(_ability_option_lines(actor, controller))
        return lines
    if controller.phase == InputPhase.TARGETING:
        return [f"{actor.name}: click a highlighted target, ESC to cancel ability"]
    return [f"{actor.name}: ENTER to end turn, ESC to reconsider"]


def _ability_option_lines(hero: Hero, controller: PlayerTurnController) -> list[str]:
    class_tracks = class_track_library.load_class_tracks()
    usable_names = {ability.name for ability in controller.usable_abilities}
    lines = []
    for index, ability in enumerate(hero.abilities):
        track = class_tracks.get(ability.name)
        track_label = f" -> {track.value}" if track is not None else ""
        status = "" if ability.name in usable_names else "  [cooldown]"
        lines.append(f"  {index + 1}: {ability.name}{track_label}{status}")
    return lines


def _draw_sidebar(
    screen: pygame.Surface,
    battle: Battle,
    font: pygame.font.Font,
    x_offset: int,
    height: int,
    controller: PlayerTurnController | None,
) -> None:
    pygame.draw.rect(screen, SIDEBAR_COLOR, (x_offset, 0, config.SIDEBAR_WIDTH_PX, height))

    lines = [
        f"Round: {battle.round_number}   Turn idx: {battle.turn_index}",
        "",
    ]
    lines.extend(_controller_prompt_lines(battle, controller))
    lines.append("")
    lines.append("A auto-play   I instant resolve   C cards   ESC quit/cancel")
    lines.append("")
    lines.append("-- Heroes --")
    for hero in battle.all_heroes:
        side = "P" if hero.is_player_controlled else "E"
        status = "DEAD" if not hero.is_alive else f"{hero.current_hp}/{hero.max_hp} HP"
        lines.append(f"[{side}] {hero.name} L{hero.level}  {status}")
        lines.append(f"    xp {hero.xp}")
        for class_xp_line in _format_class_xp_lines(hero):
            lines.append(f"    {class_xp_line}")

    y = 10
    for line in lines:
        surf = font.render(line, True, TEXT_COLOR)
        screen.blit(surf, (x_offset + 10, y))
        y += 18


def _draw_message_bar(
    screen: pygame.Surface,
    battle: Battle,
    font: pygame.font.Font,
    y_offset: int,
    width: int,
    session: Session | None = None,
) -> None:
    """Full-width strip below the grid for the last turn's event text — the
    sidebar column is too narrow for combined move+ability descriptions."""
    pygame.draw.rect(screen, SIDEBAR_COLOR, (0, y_offset, width, config.MESSAGE_BAR_HEIGHT_PX))

    lines: list[str] = []
    if battle.last_log is not None:
        lines.append(f"Last: {battle.last_log.actor_name}")
        # Split on the same "; " the battle loop joins move+ability segments
        # with, so a combined description wraps at a natural boundary
        # instead of running off the edge.
        lines.extend(battle.last_log.description.split("; "))
    if battle.is_over:
        lines.append(f"BATTLE OVER - winner: {battle.winner}")
        lines.extend(_session_progress_lines(session))

    y = y_offset + 8
    for line in lines:
        surf = font.render(line, True, TEXT_COLOR)
        screen.blit(surf, (10, y))
        y += 18


def _session_progress_lines(session: Session | None) -> list[str]:
    """Only ever called once a battle is over — session.advance() has
    already scored it by then (see the top of run()'s loop), so
    session.battles_won/is_over/result are already accurate here."""
    if session is None:
        return []
    if session.is_over:
        assert session.result is not None
        return [
            f"SESSION {session.result.upper()} — "
            f"{session.battles_won}/{session.battles_total} battles won"
        ]
    return [
        f"Battle won! ENTER for next battle ({session.battles_won}/{session.battles_total} so far)"
    ]


def _format_class_xp_lines(hero: Hero) -> list[str]:
    """Two tracks per line so the sidebar never has to fit all four at once."""
    entries = [f"{track.value}:{xp}" for track, xp in hero.class_xp.items()]
    return [" ".join(entries[i : i + 2]) for i in range(0, len(entries), 2)]


def _card_columns(total_heroes: int) -> int:
    return max(1, min(total_heroes, config.CARD_VIEW_COLUMNS))


def _card_view_top(font: pygame.font.Font) -> int:
    return config.CARD_MARGIN_PX * 2 + font.get_linesize()


def _card_view_size(total_heroes: int, font: pygame.font.Font) -> tuple[int, int]:
    """Window size that fits every hero card at full width — sized to the
    content, rather than squeezing cards into a fixed-size window."""
    columns = _card_columns(total_heroes)
    rows = max(1, -(-total_heroes // columns)) if total_heroes else 1
    width = config.CARD_MARGIN_PX + columns * (config.CARD_WIDTH_PX + config.CARD_MARGIN_PX)
    height = _card_view_top(font) + rows * (config.CARD_HEIGHT_PX + config.CARD_MARGIN_PX)
    return width, height


def _draw_hero_cards(screen: pygame.Surface, battle: Battle, font: pygame.font.Font) -> None:
    """Full-screen grid of per-hero stat cards. Read-only, same source data
    as the sidebar — just laid out for reviewing the whole roster at once."""
    hint = font.render("C: back to battle view   ESC: quit", True, TEXT_COLOR)
    screen.blit(hint, (config.CARD_MARGIN_PX, config.CARD_MARGIN_PX))

    columns = _card_columns(len(battle.all_heroes))
    top = _card_view_top(font)
    for index, hero in enumerate(battle.all_heroes):
        col = index % columns
        row = index // columns
        x = config.CARD_MARGIN_PX + col * (config.CARD_WIDTH_PX + config.CARD_MARGIN_PX)
        y = top + row * (config.CARD_HEIGHT_PX + config.CARD_MARGIN_PX)
        _draw_hero_card(screen, hero, font, x, y)


def _draw_hero_card(
    screen: pygame.Surface, hero: Hero, font: pygame.font.Font, x: int, y: int
) -> None:
    if not hero.is_alive:
        border_color = DEAD_COLOR
    elif hero.is_player_controlled:
        border_color = PLAYER_COLOR
    else:
        border_color = ENEMY_COLOR

    rect = (x, y, config.CARD_WIDTH_PX, config.CARD_HEIGHT_PX)
    pygame.draw.rect(screen, CARD_BACKGROUND_COLOR, rect)
    pygame.draw.rect(screen, border_color, rect, width=2)

    side = "P" if hero.is_player_controlled else "E"
    status = "DEAD" if not hero.is_alive else f"{hero.current_hp}/{hero.max_hp} HP"
    attrs = hero.attributes
    lines = [
        f"[{side}] {hero.name}  L{hero.level}",
        status,
        f"xp {hero.xp}/{config.XP_LEVEL_THRESHOLD}",
        "",
        f"Might {attrs.might}   Focus {attrs.focus}",
        f"Resolve {attrs.resolve}   Agility {attrs.agility}",
        "",
        "Abilities:",
    ]
    class_tracks = class_track_library.load_class_tracks()
    for ability in hero.abilities:
        range_label = (
            f"{ability.min_range}-{ability.range}" if ability.min_range else f"{ability.range}"
        )
        cd_label = ""
        if ability.cooldown:
            remaining = hero.cooldowns.get(ability.name, 0)
            cd_label = f", cd {remaining}/{ability.cooldown}"
        track = class_tracks.get(ability.name)
        track_label = track.value if track is not None else "?"
        lines.append(f"  {ability.name} ({track_label}, rng {range_label}{cd_label})")
    lines.append("")
    lines.extend(_format_class_xp_lines(hero))

    text_y = y + 8
    for line in lines:
        surf = font.render(line, True, TEXT_COLOR)
        screen.blit(surf, (x + 8, text_y))
        text_y += 14


def _attribute_slot(key: int) -> AttributeName | None:
    return _ATTRIBUTE_SLOT_ORDER[_ATTRIBUTE_SLOT_KEYS.index(key)] if key in _ATTRIBUTE_SLOT_KEYS else None


def _between_battle_view_size(roster_size: int) -> tuple[int, int]:
    height = (
        config.BETWEEN_BATTLE_TOP_PX
        + roster_size * config.BETWEEN_BATTLE_ROW_HEIGHT_PX
        + config.BETWEEN_BATTLE_MARGIN_PX
    )
    return config.BETWEEN_BATTLE_WIDTH_PX, height


def _roster_row_at(pos: tuple[int, int], roster: list[Hero]) -> Hero | None:
    x, y = pos
    margin = config.BETWEEN_BATTLE_MARGIN_PX
    if not (margin <= x <= config.BETWEEN_BATTLE_WIDTH_PX - margin) or y < config.BETWEEN_BATTLE_TOP_PX:
        return None
    index = (y - config.BETWEEN_BATTLE_TOP_PX) // config.BETWEEN_BATTLE_ROW_HEIGHT_PX
    return roster[index] if 0 <= index < len(roster) else None


def _format_signed(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def _format_attribute_delta_line(hero: Hero, delta: HeroDelta) -> str:
    attrs = hero.attributes
    fields = (
        ("Might", attrs.might, AttributeName.MIGHT),
        ("Focus", attrs.focus, AttributeName.FOCUS),
        ("Resolve", attrs.resolve, AttributeName.RESOLVE),
        ("Agility", attrs.agility, AttributeName.AGILITY),
    )
    parts = []
    for label, current, name in fields:
        change = delta.attribute_deltas[name]
        suffix = f" ({_format_signed(change)})" if change else ""
        parts.append(f"{label} {current}{suffix}")
    return "  ".join(parts)


def _format_between_battle_class_xp_lines(hero: Hero, delta: HeroDelta) -> list[str]:
    """Mirrors _format_class_xp_lines' two-per-line layout, with a delta
    suffix when this hero's class XP moved since the last battle."""
    entries = []
    for track, xp in hero.class_xp.items():
        change = delta.class_xp_deltas[track]
        suffix = f"({_format_signed(change)})" if change else ""
        entries.append(f"{track.value}:{xp}{suffix}")
    return [" ".join(entries[i : i + 2]) for i in range(0, len(entries), 2)]


def _between_battle_status_line(controller: BetweenBattleController) -> str:
    if controller.phase == BetweenBattlePhase.ALLOCATING:
        pending = controller.pending_hero
        assert pending is not None
        return (
            f"{pending.name} leveled up! Choose a bonus attribute: "
            "1 Might  2 Focus  3 Resolve  4 Agility   SPACE let affinity decide"
        )
    count = len(controller.selected)
    action = "ENTER to start the next battle" if controller.is_ready else "select at least 1 hero"
    return f"Select up to {config.FIELDED_SQUAD_SIZE} heroes to field ({count} selected) — click a row, {action}"


def _draw_between_battle_screen(
    screen: pygame.Surface, controller: BetweenBattleController, font: pygame.font.Font
) -> None:
    """The payoff surface of Phase 2b (docs/04_phase2b_definition.md section
    6): squad selection and manual attribute allocation, with per-hero
    level/attribute/class-XP deltas sourced entirely from Session.deltas()
    — this module computes none of that itself, mirroring how battle
    rendering never computes legality itself."""
    session = controller.session
    status = font.render(_between_battle_status_line(controller), True, TEXT_COLOR)
    screen.blit(status, (config.BETWEEN_BATTLE_MARGIN_PX, config.BETWEEN_BATTLE_MARGIN_PX))

    deltas = session.deltas()
    row_width = config.BETWEEN_BATTLE_WIDTH_PX - 2 * config.BETWEEN_BATTLE_MARGIN_PX
    row_height = config.BETWEEN_BATTLE_ROW_HEIGHT_PX - config.BETWEEN_BATTLE_MARGIN_PX
    for index, hero in enumerate(session.roster):
        delta = deltas[index] if index < len(deltas) else None
        x = config.BETWEEN_BATTLE_MARGIN_PX
        y = config.BETWEEN_BATTLE_TOP_PX + index * config.BETWEEN_BATTLE_ROW_HEIGHT_PX
        _draw_roster_row(screen, controller, hero, delta, font, x, y, row_width, row_height)


def _draw_roster_row(
    screen: pygame.Surface,
    controller: BetweenBattleController,
    hero: Hero,
    delta: HeroDelta | None,
    font: pygame.font.Font,
    x: int,
    y: int,
    width: int,
    height: int,
) -> None:
    is_fielded = any(candidate is hero for candidate in controller.selected)
    is_pending = controller.pending_hero is hero
    if is_pending:
        border_color = PENDING_ALLOCATION_COLOR
    elif is_fielded:
        border_color = PLAYER_COLOR
    else:
        border_color = GRID_LINE_COLOR
    rect = (x, y, width, height)
    pygame.draw.rect(screen, CARD_BACKGROUND_COLOR, rect)
    pygame.draw.rect(screen, border_color, rect, width=2)

    checkbox = "[X]" if is_fielded else "[ ]"
    leveled = "  LEVEL UP!" if delta is not None and delta.leveled_up else ""
    recovering = "  (recovering)" if hero.current_hp < hero.max_hp else ""
    lines = [f"{checkbox} {hero.name}  L{hero.level}{leveled}", f"{hero.current_hp}/{hero.max_hp} HP{recovering}"]
    if delta is not None:
        lines.append(_format_attribute_delta_line(hero, delta))
        lines.extend(_format_between_battle_class_xp_lines(hero, delta))

    text_y = y + 6
    for line in lines:
        surf = font.render(line, True, TEXT_COLOR)
        screen.blit(surf, (x + 8, text_y))
        text_y += 16
