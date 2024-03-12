from __future__ import annotations

from typing import Tuple, TYPE_CHECKING

import color
import setup_game
from components.fighter import Fighter

if TYPE_CHECKING:
    from tcod import Console
    from engine import Engine
    from game_map import GameMap


def get_names_at_location(x: int, y: int, game_map: GameMap) -> str:
    if not game_map.in_bounds(x, y) or not game_map.visible[x, y]:
        return ""

    names = ', '.join(
        entity.name for entity in game_map.entities if entity.x == x and entity.y == y
    )

    return names.capitalize()


def render_bars(
        console: Console, player: Fighter, total_width: int
) -> None:
    """Render the player's hit points and mana as data bars."""
    # TODO: Add rendering of second bar with different values

    def render_bar(current_value: int, maximum_value: int, x: int, y: int, bar_color: Tuple[int, int, int], name: str):
        bar_width = int(float(current_value) / maximum_value * total_width)

        console.draw_rect(
            x=x,
            y=y,
            width=total_width,
            height=1,
            ch=1,
            bg=color.bar_empty
        )

        if bar_width > 0:
            console.draw_rect(
                x=x, y=y, width=bar_width, height=1, ch=1, bg=bar_color
            )

            console.print(
                x=2, y=y, string=f"{name}: {current_value}/{maximum_value}", fg=color.bar_text
            )

    render_bar(
        player.hp,
        player.max_hp,
        x=1,
        y=setup_game.WINDOW_HEIGHT * 2 // 3 + 2,
        bar_color=color.bar_hp_filled,
        name="HP"
    )

    render_bar(
        player.mana,
        player.max_mana,
        x=1,
        y=setup_game.WINDOW_HEIGHT * 2 // 3 + 4,
        bar_color=color.bar_mana_filled,
        name="Mana"
    )


def render_dungeon_level(
        console: Console, dungeon_level: int, location: Tuple[int, int]
) -> None:
    """
    Render the level the player is currently on, at the given location.
    """
    x, y = location

    console.print(x=x, y=y, string=f"Dungeon level: {dungeon_level}")


def render_names_at_mouse_location(
    console: Console, x: int, y: int, engine: Engine
) -> None:
    mouse_x, mouse_y = engine.mouse_location

    names_at_mouse_location = get_names_at_location(
        x=mouse_x, y=mouse_y, game_map=engine.game_map
    )

    console.print(x=x, y=y, string=names_at_mouse_location)
