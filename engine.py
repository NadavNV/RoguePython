from __future__ import annotations

import lzma
import pickle
from typing import List, Optional, TYPE_CHECKING

from tcod.console import Console
from tcod.map import compute_fov

import exceptions
from message_log import MessageLog
import render_functions

if TYPE_CHECKING:
    from mapentity import Actor
    from game_map import GameMap, GameWorld


class Engine:
    game_map: GameMap
    game_world: GameWorld
    in_combat: bool
    active_enemies: List[Actor]

    def __init__(self, player: Actor):
        self.message_log = MessageLog()
        self.mouse_location = (0, 0)
        self.player = player
        self.in_combat = False
        self.active_enemies = []

    def handle_enemy_turns(self) -> None:
        if not self.in_combat:
            for entity in set(self.game_map.actors) - {self.player}:
                if entity.ai:
                    try:
                        entity.ai.perform()
                    except exceptions.Impossible:
                        pass  # Ignore impossible action exceptions from AI.
        else:
            for entity in self.active_enemies:
                if entity.ai:
                    entity.ai.perform()

    def save_as(self, filename: str) -> None:
        """Save this Engine instance as a compressed file."""
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)

    def render(self, console: Console):
        self.message_log.render(
            console=console,
            x=console.width * 2 // 3 + 2,
            y=1,
            width=console.width // 3 - 2,
            height=console.height * 2 // 3 - 1,
        )

        render_functions.render_bars(
            console=console,
            player=self.player.fighter,
            total_width=console.width // 3 - 2,
        )

        render_functions.render_dungeon_level(
            console=console,
            dungeon_level=self.game_world.current_floor,
            location=(1, console.height * 2 // 3 + 6)
        )

        if self.in_combat:
            render_functions.render_combat_ui(console)
        else:
            self.game_map.render(console)

            render_functions.render_names_at_mouse_location(
                console=console, x=0, y=console.height * 2 // 3 + 7, engine=self
            )

            render_functions.render_dungeon_ui(console)

    def update_fov(self) -> None:
        """Recompute the visible area based on the player's point of view."""
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles["transparent"],
            (self.player.x, self.player.y),
            radius=8,
        )
        # If a tile is "visible" it should be added to "explored".
        self.game_map.explored |= self.game_map.visible
