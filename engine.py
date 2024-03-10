from __future__ import annotations

import lzma
import pickle
from typing import List, Optional, TYPE_CHECKING

from tcod.console import Console
from tcod.map import compute_fov

import exceptions
from message_log import MessageLog
import render_functions
import setup_game

if TYPE_CHECKING:
    from entity import Actor
    from game_map import GameMap, GameWorld


class Engine:
    """Superclass for the different modes of play, i.e. roaming the dungeon and
    instanced combat.
    """
    def __init__(self, player: Actor):
        self.message_log = MessageLog()
        self.mouse_location = (0, 0)
        self.player = player

    def handle_enemy_turns(self) -> Optional[Engine]:
        raise NotImplementedError()

    def save_as(self, filename: str) -> None:
        """Save this Engine instance as a compressed file."""
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)

    def render(self, console: Console):
        self.message_log.render(
            console=console,
            x=setup_game.WINDOW_WIDTH * 2 // 3 + 2,
            y=1,
            width=setup_game.WINDOW_WIDTH // 3 - 2,
            height=setup_game.WINDOW_HEIGHT * 2 // 3 - 1,
        )

        render_functions.render_bars(
            console=console,
            current_value=self.player.fighter.hp,
            maximum_value=self.player.fighter.max_hp,
            total_width=setup_game.WINDOW_WIDTH // 3 - 2,
        )


class DungeonEngine(Engine):
    """Engine that handles roaming the dungeon. There is a different engine for instanced combat."""
    game_map: GameMap
    game_world: GameWorld

    def handle_enemy_turns(self) -> None:
        for entity in set(self.game_map.actors) - {self.player}:
            if entity.ai:
                try:
                    entity.ai.perform()
                except exceptions.Impossible:
                    pass  # Ignore impossible action exceptions from AI.

    def update_fov(self) -> None:
        """Recompute the visible area based on the player's point of view."""
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles["transparent"],
            (self.player.x, self.player.y),
            radius=8,
        )
        # If a tile is "visible" it should be added to "explored".
        self.game_map.explored |= self.game_map.visible

    def render(self, console: Console) -> None:
        super().render(console)
        self.game_map.render(console)

        render_functions.render_dungeon_level(
            console=console,
            dungeon_level=self.game_world.current_floor,
            location=(0, setup_game.WINDOW_HEIGHT * 2 // 3 + 6)
        )

        render_functions.render_names_at_mouse_location(
            console=console, x=0, y=setup_game.WINDOW_HEIGHT * 2 // 3 + 7, engine=self
        )

        frame_x = setup_game.WINDOW_WIDTH // 3 + 1
        frame_y = setup_game.WINDOW_HEIGHT * 2 // 3 + 1
        console.draw_frame(
            x=frame_x,
            y=frame_y,
            width=setup_game.WINDOW_WIDTH // 3 - 1,
            height=setup_game.WINDOW_HEIGHT // 3 - 2,
            title="Keyboard Commands",
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(x=frame_x + 1, y=frame_y + 1, string="Use item from bags:              i")
        console.print(x=frame_x + 1, y=frame_y + 2, string="Drop item:                       d")
        console.print(x=frame_x + 1, y=frame_y + 3, string="Character information and gear:  c")
        console.print(x=frame_x + 1, y=frame_y + 4, string="Expand message log:              v")
        console.print(x=frame_x + 1, y=frame_y + 5, string="Descend stairs:          shift + .")
        console.print(x=frame_x + 1, y=frame_y + 6, string="Movement:              Numpad keys")
        console.print(x=frame_x + 1, y=frame_y + 7, string="Wait:                     Numpad 5")

        frame_x = setup_game.WINDOW_WIDTH * 2 // 3 + 1
        frame_y = setup_game.WINDOW_HEIGHT * 2 // 3 + 1
        console.draw_frame(
            x=frame_x,
            y=frame_y,
            width=setup_game.WINDOW_WIDTH // 3 - 1,
            height=setup_game.WINDOW_HEIGHT // 3 - 2,
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


class CombatEngine(Engine):
    enemies: List[Actor]

    def __init__(self, parent: DungeonEngine, enemies: List[Actor]):
        super().__init__(player=parent.player)
        self.parent = parent
        self.enemies = enemies

    def handle_enemy_turns(self) -> Optional[Engine]:
        if len(self.enemies) == 0:
            # TODO: Remove the enemies from the parent world state
            # TODO: Drop loot
            return self.parent  # Return to the main game
        else:
            for enemy in self.enemies:
                enemy.ai.perform()
