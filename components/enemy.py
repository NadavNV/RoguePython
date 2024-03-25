from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from entity import FighterGroup
    from components.ability import Ability

from components.base_component import BaseComponent


class Enemy(BaseComponent):
    parent: FighterGroup

    def __init__(
            self,
            *,
            char: str,
            name: str,
            color: Tuple[int, int, int],
            abilities: List[Ability],
    ):
        super().__init__()

        self.char = char
        self.name = name
        self.color = color
        self.abilities = abilities
