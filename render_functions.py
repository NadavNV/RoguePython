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


def render_combat_ui(console: Console) -> None:
    console.draw_frame(
        x=0,
        y=0,
        width=console.width * 2 // 3,
        height=console.height * 2 // 3,
        clear=True,
        fg=(255, 255, 255),
        bg=(0, 0, 0)
    )

    frame_x = console.width // 3
    frame_y = console.height * 2 // 3
    width = console.width // 3 + 1
    height = console.height // 3
    console.draw_frame(
        x=frame_x,
        y=frame_y,
        width=width,
        height=height,
        clear=True,
        fg=(255, 255, 255),
        bg=(0, 0, 0),
    )

    console.print(
        x=frame_x + width // 5,
        y=frame_y + height // 5,
        string="Attack"
    )

    console.print(
        x=frame_x + width // 5,
        y=frame_y + height * 3 // 5,
        string="Run"
    )

    console.print(
        x=frame_x + width * 3 // 5,
        y=frame_y + height // 5,
        string="Use ability"
    )

    console.print(
        x=frame_x + width * 3 // 5,
        y=frame_y + height * 3 // 5,
        string="Use item"
    )


def render_dungeon_ui(console: Console) -> None:
    frame_x = console.width // 3 + 1
    frame_y = console.height * 2 // 3 + 1
    console.draw_frame(
        x=frame_x,
        y=frame_y,
        width=console.width // 3 - 1,
        height=console.height // 3 - 2,
        title="Keyboard Commands",
        clear=True,
        fg=(255, 255, 255),
        bg=(0, 0, 0),
    )

    console.print(x=frame_x + 1, y=frame_y + 1, string="Use item from bags:              i")
    console.print(x=frame_x + 1, y=frame_y + 2, string="Drop item:                       d")
    console.print(x=frame_x + 1, y=frame_y + 3, string="Unequip item:                    u")
    console.print(x=frame_x + 1, y=frame_y + 4, string="Character information:           c")
    console.print(x=frame_x + 1, y=frame_y + 5, string="Expand message log:              v")
    console.print(x=frame_x + 1, y=frame_y + 6, string="Descend stairs:          shift + .")
    console.print(x=frame_x + 1, y=frame_y + 7, string="Movement:              Numpad keys")
    console.print(x=frame_x + 1, y=frame_y + 8, string="Wait:                     Numpad 5")

    frame_x = console.width * 2 // 3 + 1
    frame_y = console.height * 2 // 3 + 1
    console.draw_frame(
        x=frame_x,
        y=frame_y,
        width=console.width // 3 - 1,
        height=console.height // 3 - 2,
        title="Map Legend",
        clear=True,
        fg=(255, 255, 255),
        bg=(0, 0, 0),
    )

    console.print(x=frame_x + 1, y=frame_y + 1, string="@: Player / Trader")
    console.print(x=frame_x + 1, y=frame_y + 2, string=">: Stairs down")
    console.print(x=frame_x + 1, y=frame_y + 3, string="/: Weapon")
    console.print(x=frame_x + 1, y=frame_y + 4, string="[: Armor")
    console.print(x=frame_x + 1, y=frame_y + 5, string="!: Potion")
    console.print(x=frame_x + 1, y=frame_y + 6, string="~: Scroll")
