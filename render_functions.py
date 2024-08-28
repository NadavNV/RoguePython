from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

import textwrap
import numpy as np
from tcod import libtcodpy

import colors
from cards import keyword_to_description
from components.fighter import Fighter

if TYPE_CHECKING:
    from cards import Card
    from tcod.console import Console
    from engine import Engine
    from game_map import GameMap


def wrap(text: str, width: int):
    """"Returns 'text' split into lines up to the given width"""
    # Taken from https://stackoverflow.com/questions/1166317/python-textwrap-library-how-to-preserve-line-breaks
    return '\n'.join(['\n'.join(textwrap.wrap(line,
                                              width,
                                              break_long_words=False,
                                              replace_whitespace=False
                                              )
                                ) for line in text.splitlines()])


def get_names_at_location(x: int, y: int, game_map: GameMap) -> str:
    if not game_map.in_bounds(x, y) or not game_map.visible[x, y]:
        return ""

    names = ', '.join(
        entity.name for entity in game_map.entities if entity.x == x and entity.y == y
    )

    return names.capitalize()


def render_bar(
        console: Console,
        total_width: int,
        current_value: int,
        maximum_value: int,
        x: int,
        y: int,
        bar_color: Tuple[int, int, int], name: str
):
    if maximum_value == 0:
        bar_width = 0
    else:
        bar_width = int(float(current_value) / maximum_value * total_width)

    console.draw_rect(
        x=x,
        y=y,
        width=total_width,
        height=1,
        ch=1,
        bg=colors.bar_empty
    )

    if bar_width >= 0:
        console.draw_rect(
            x=x, y=y, width=bar_width, height=1, ch=1, bg=bar_color
        )

        console.print(
            x=x + 1, y=y, string=f"{name}: {current_value}/{maximum_value}", fg=colors.bar_text
        )


def render_player_bars(
        console: Console, player: Fighter, total_width: int
) -> None:
    """Render the player's hit points and mana as data bars."""

    render_bar(
        console=console,
        current_value=player.hp,
        maximum_value=player.max_hp,
        total_width=total_width,
        x=1,
        y=console.height * 2 // 3 + 2,
        bar_color=colors.bar_hp_filled,
        name="HP"
    )

    if player.block > 0:
        console.draw_rect(
            x=total_width + 2,
            y=console.height * 2 // 3 + 2,
            width=2 + len(str(player.block)),
            height=1,
            ch=1,
            bg=colors.bar_mana_filled
        )
        console.print(x=total_width + 3, y=console.height * 2 // 3 + 2, string=str(player.block))

    player.resource.render_bar(
        console=console,
        x=1,
        y=console.height * 2 // 3 + 4,
        width=total_width,
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


def render_combat_ui(console: Console, cursor: Optional[np.ndarray]) -> None:
    console.draw_frame(
        x=0,
        y=0,
        width=console.width * 2 // 3,
        height=console.height * 2 // 3,
        clear=True,
        fg=colors.white,
        bg=colors.black
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
        fg=colors.white,
        bg=colors.black,
    )

    if cursor is not None and np.array_equal(cursor, [0, 0]):
        fg = colors.black
        bg = colors.white
    else:
        fg = colors.white
        bg = colors.black

    console.print(
        x=frame_x + 4,
        y=frame_y + 4,
        string="Hand",
        fg=fg,
        bg=bg,
    )

    if cursor is not None and np.array_equal(cursor, [0, 1]):
        fg = colors.black
        bg = colors.white
    else:
        fg = colors.white
        bg = colors.black

    console.print(
        x=frame_x + 4,
        y=frame_y + 7,
        string="Inspect Enemies",
        fg=fg,
        bg=bg,
    )

    if cursor is not None and np.array_equal(cursor, [0, 2]):
        fg = colors.black
        bg = colors.white
    else:
        fg = colors.white
        bg = colors.black

    console.print(
        x=frame_x + 4,
        y=frame_y + 10,
        string="Discard Pile",
        fg=fg,
        bg=bg,
    )

    if cursor is not None and np.array_equal(cursor, [0, 3]):
        fg = colors.black
        bg = colors.white
    else:
        fg = colors.white
        bg = colors.black

    console.print(
        x=frame_x + 4,
        y=frame_y + 13,
        string="Run",
        fg=fg,
        bg=bg,
    )

    if cursor is not None and np.array_equal(cursor, [1, 0]):
        fg = colors.black
        bg = colors.white
    else:
        fg = colors.white
        bg = colors.black

    console.print(
        x=frame_x + 22,
        y=frame_y + 4,
        string="Use Item",
        fg=fg,
        bg=bg,
    )

    if cursor is not None and np.array_equal(cursor, [1, 1]):
        fg = colors.black
        bg = colors.white
    else:
        fg = colors.white
        bg = colors.black

    console.print(
        x=frame_x + 22,
        y=frame_y + 7,
        string="Draw Pile",
        fg=fg,
        bg=bg,
    )

    if cursor is not None and np.array_equal(cursor, [1, 2]):
        fg = colors.black
        bg = colors.white
    else:
        fg = colors.white
        bg = colors.black

    console.print(
        x=frame_x + 22,
        y=frame_y + 10,
        string="Burn Pile",
        fg=fg,
        bg=bg,
    )

    if cursor is not None and np.array_equal(cursor, [1, 3]):
        fg = colors.black
        bg = colors.white
    else:
        fg = colors.white
        bg = colors.black

    console.print(
        x=frame_x + 22,
        y=frame_y + 13,
        string="End Turn",
        fg=fg,
        bg=bg,
    )


def render_card_list(console: Console, cards: List[Card], cursor: int,
                     name: str, up_arrow: bool, down_arrow: bool) -> None:
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
        fg=colors.white,
        bg=colors.black,
    )

    console.print_box(
        x=frame_x,
        y=frame_y,
        width=console.width // 3 - 1,
        height=1,
        string=f"┤{name}├",
        fg=colors.white,
        bg=colors.black,
        alignment=libtcodpy.CENTER
    )

    if up_arrow:
        console.print(
            x=frame_x + 2,
            y=frame_y + 2,
            string="▲",
            fg=colors.white,
            bg=colors.black,
        )

    for i in range(len(cards)):
        if i == cursor:
            fg = colors.black
            bg = colors.white
        else:
            fg = colors.white
            bg = colors.black
        console.print(
            x=frame_x + 2,
            y=frame_y + 3 + i,
            string=cards[i].name,
            fg=fg,
            bg=bg,
        )

    # Display card tooltip
    tooltip_x = console.width * 2 // 3
    tooltip_y = 0
    width = console.width // 3 + 1
    title = wrap(cards[cursor].name, width - 2)
    text = wrap(cards[cursor].description, width - 2)
    height = len(title.split('\n')) + len(text.split('\n')) + 3

    console.draw_frame(
        x=tooltip_x,
        y=tooltip_y,
        width=width,
        height=height,
        clear=True,
        fg=colors.white,
        bg=colors.black,
    )
    console.print_box(
        x=tooltip_x + 1,
        y=tooltip_y + 1,
        width=width - 2,
        height=height - 2,
        string=title + '\n\n' + text,
        fg=colors.white,
        bg=colors.black,
    )

    # Display keyword descriptions
    if len(cards[cursor].keywords) > 0:
        tooltip_y += height
        text = []
        for keyword in cards[cursor].keywords:
            text.append(f"{keyword.capitalize()} - {keyword_to_description(keyword)}")
        text = wrap('\n\n'.join(text), width - 2)
        height = len(text.split('\n')) + 2
        console.draw_frame(
            x=tooltip_x,
            y=tooltip_y,
            width=width,
            height=height,
            clear=True,
            fg=colors.white,
            bg=colors.black,
        )
        console.print_box(
            x=tooltip_x + 1,
            y=tooltip_y + 1,
            width=width - 2,
            height=height - 2,
            string=text,
            fg=colors.white,
            bg=colors.black,
        )

    if down_arrow:
        console.print(
            x=frame_x + 2,
            y=frame_y + 2 + len(cards) + 1,
            string="▼",
            fg=colors.white,
            bg=colors.black,
        )


def render_dungeon_ui(console: Console) -> None:
    frame_x = console.width // 3 + 1
    frame_y = console.height * 2 // 3 + 1
    console.draw_frame(
        x=frame_x,
        y=frame_y,
        width=console.width // 3 - 1,
        height=console.height // 3 - 2,
        clear=True,
        fg=colors.white,
        bg=colors.black,
    )
    console.print_box(
        x=frame_x,
        y=frame_y,
        width=console.width // 3 - 1,
        height=1,
        string=f"┤Keyboard Commands├",
        fg=colors.white,
        bg=colors.black,
        alignment=libtcodpy.CENTER
    )

    console.print(x=frame_x + 1, y=frame_y + 1, string="Use item from inventory:         i")
    console.print(x=frame_x + 1, y=frame_y + 2, string="Drop item:                       d")
    console.print(x=frame_x + 1, y=frame_y + 3, string="Unequip item:                    u")
    console.print(x=frame_x + 1, y=frame_y + 4, string="Character & Equipment info:      c")
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
        clear=True,
        fg=colors.white,
        bg=colors.black,
    )
    console.print_box(
        x=frame_x,
        y=frame_y,
        width=console.width // 3 - 1,
        height=1,
        string=f"┤Map Legend├",
        fg=colors.white,
        bg=colors.black,
        alignment=libtcodpy.CENTER
    )

    console.print(x=frame_x + 1, y=frame_y + 1, string="@: Player / Trader")
    console.print(x=frame_x + 1, y=frame_y + 2, string=">: Stairs down")
    console.print(x=frame_x + 1, y=frame_y + 3, string="/: Weapon")
    console.print(x=frame_x + 1, y=frame_y + 4, string="[: Armor")
    console.print(x=frame_x + 1, y=frame_y + 5, string="!: Potion")
    console.print(x=frame_x + 1, y=frame_y + 6, string="~: Scroll")


def render_enemy(console: Console, x: int, y: int, enemy: Fighter):
    """Renders the given enemy's sprite and HP bar at the given xy coordinates"""
    console.draw_semigraphics(enemy.sprite, x=x, y=y)
    render_bar(
        console=console,
        x=x,
        y=y,
        bar_color=colors.bar_hp_filled,
        name='HP',
        current_value=enemy.hp,
        maximum_value=enemy.max_hp,
        total_width=console.width // 8
    )
    console.print_box(
        x=x,
        y=y + 2,
        width=console.width // 8,
        height=2,
        string=wrap(text=f"Level {enemy.level.current_level} {enemy.name}", width=console.width // 8),
        fg=colors.white,
        bg=colors.black,
    )
