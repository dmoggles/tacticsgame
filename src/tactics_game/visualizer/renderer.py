from __future__ import annotations

import pygame

from .. import config
from ..engine import class_track_library
from ..engine.battle import Battle
from ..models.grid import Grid
from ..models.hero import Hero

BACKGROUND_COLOR = (24, 24, 24)
SIDEBAR_COLOR = (16, 16, 16)
CARD_BACKGROUND_COLOR = (34, 34, 34)
GRID_LINE_COLOR = (70, 70, 70)
PLAYER_COLOR = (70, 130, 220)
ENEMY_COLOR = (220, 80, 80)
DEAD_COLOR = (90, 90, 90)
TEXT_COLOR = (230, 230, 230)


def run(battle: Battle) -> None:
    """Passive, read-only debug renderer. Space steps one turn, A toggles
    auto-play, C toggles the hero card view, Esc/close quits. Never mutates
    engine state beyond calling battle.step()."""
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

    running = True
    while running:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    battle.step()
                elif event.key == pygame.K_a:
                    auto_play = not auto_play
                    time_since_step = 0
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
                elif event.key == pygame.K_ESCAPE:
                    running = False

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
            for hero in battle.all_heroes:
                _draw_hero(screen, hero, font)
            _draw_sidebar(screen, battle, font, grid_width_px, grid_height_px)
            _draw_message_bar(screen, battle, font, grid_height_px, battle_view_width)
        pygame.display.flip()

    pygame.quit()


def _draw_grid(screen: pygame.Surface, grid: Grid) -> None:
    grid_width_px = grid.width * config.TILE_SIZE_PX
    grid_height_px = grid.height * config.TILE_SIZE_PX
    for x in range(grid.width + 1):
        px = x * config.TILE_SIZE_PX
        pygame.draw.line(screen, GRID_LINE_COLOR, (px, 0), (px, grid_height_px))
    for y in range(grid.height + 1):
        py = y * config.TILE_SIZE_PX
        pygame.draw.line(screen, GRID_LINE_COLOR, (0, py), (grid_width_px, py))


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


def _draw_sidebar(
    screen: pygame.Surface,
    battle: Battle,
    font: pygame.font.Font,
    x_offset: int,
    height: int,
) -> None:
    pygame.draw.rect(screen, SIDEBAR_COLOR, (x_offset, 0, config.SIDEBAR_WIDTH_PX, height))

    lines = [
        f"Round: {battle.round_number}   Turn idx: {battle.turn_index}",
        "",
        "SPACE step   A auto-play   C cards   ESC quit",
        "",
        "-- Heroes --",
    ]
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

    y = y_offset + 8
    for line in lines:
        surf = font.render(line, True, TEXT_COLOR)
        screen.blit(surf, (10, y))
        y += 18


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
