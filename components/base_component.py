from __future__ import annotations

from typing import TYPE_CHECKING

import random

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity
    from game_map import GameMap


def roll_dice(dice_string: str):
    number_of_dice, dice_size = tuple(dice_string.split('d'))
    result = 0
    for i in range(int(number_of_dice)):
        result += random.randint(1, int(dice_size))
    return result


class BaseComponent:
    parent: Entity  # Owning entity instance

    @property
    def game_map(self) -> GameMap:
        return self.parent.game_map

    @property
    def engine(self) -> Engine:
        return self.game_map.engine


if __name__ == "__main__":
    print(roll_dice("2d12"))
