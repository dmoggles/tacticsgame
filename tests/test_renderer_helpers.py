from __future__ import annotations

import pygame

from tactics_game import config
from tactics_game.models.grid import Grid, Position
from tactics_game.visualizer.renderer import _ability_slot_key_index, _pixel_to_tile


def _grid() -> Grid:
    return Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)


def test_pixel_to_tile_maps_within_bounds() -> None:
    grid = _grid()
    px = config.TILE_SIZE_PX
    assert _pixel_to_tile((0, 0), grid) == Position(0, 0)
    assert _pixel_to_tile((px + 1, 2 * px + 3), grid) == Position(1, 2)


def test_pixel_to_tile_rejects_negative_coordinates() -> None:
    assert _pixel_to_tile((-1, 5), _grid()) is None
    assert _pixel_to_tile((5, -1), _grid()) is None


def test_pixel_to_tile_rejects_out_of_bounds_click() -> None:
    # A click past the grid's pixel extent — e.g. in the sidebar — maps to
    # a tile column past grid.width and must be rejected.
    grid = _grid()
    sidebar_x = grid.width * config.TILE_SIZE_PX + 10
    assert _pixel_to_tile((sidebar_x, 0), grid) is None


def test_ability_slot_key_index_maps_number_keys() -> None:
    assert _ability_slot_key_index(pygame.K_1) == 0
    assert _ability_slot_key_index(pygame.K_2) == 1
    assert _ability_slot_key_index(pygame.K_3) == 2
    assert _ability_slot_key_index(pygame.K_4) == 3


def test_ability_slot_key_index_rejects_other_keys() -> None:
    assert _ability_slot_key_index(pygame.K_5) is None
    assert _ability_slot_key_index(pygame.K_a) is None
