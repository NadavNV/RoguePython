from __future__ import annotations

import copy
import math
from typing import Iterable, List, Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union

import colors
from render_order import RenderOrder

if TYPE_CHECKING:
    from components.ai import BaseAI
    from components.consumable import Consumable
    from components.equippable import Equippable
    from components.fighter import Fighter
    from components.inventory import Inventory
    from game_map import GameMap
    from engine import Engine

T = TypeVar("T", bound="MapEntity")


class MapEntity:
    """
    A generic object to represent any object that appears on the dungeon map.
    """

    parent: Union[GameMap, Inventory]

    def __init__(
        self,
        parent: Optional[GameMap] = None,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = colors.white,
        name: str = "<Unnamed>",
        blocks_movement: bool = False,
        render_order: RenderOrder = RenderOrder.CORPSE,
    ):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks_movement = blocks_movement
        self.render_order = render_order
        if parent:
            # If parent isn't provided now then it will be set later
            self.parent = parent
            parent.entities.add(self)

    @property
    def game_map(self) -> GameMap:
        return self.parent.game_map

    def spawn(self: T, game_map: GameMap, x: int, y: int) -> T:
        """Spawn a copy of this instance at the given location."""
        clone = copy.deepcopy(self)
        clone.x = x
        clone.y = y
        clone.parent = game_map
        game_map.entities.add(clone)
        return clone

    def place(self, x: int, y: int, game_map: Optional[GameMap] = None) -> None:
        """Place this entity at a new location. Handles moving across GameMaps."""
        self.x = x
        self.y = y
        if game_map:
            if hasattr(self, "parent"):  # Possibly uninitialized
                if self.parent is self.game_map:
                    self.parent.entities.remove(self)
            self.parent = game_map
            game_map.entities.add(self)

    @property
    def engine(self) -> Engine:
        return self.parent.engine


class FighterGroup(MapEntity):
    def __init__(
            self,
            *,
            x: int = 0,
            y: int = 0,
            fighters: List[Fighter],
            ai_cls: Type[BaseAI],
    ):
        super().__init__(
            x=x,
            y=y,
            char=fighters[0].char,
            color=fighters[0].color,
            name=', '.join([enemy.name for enemy in fighters]),
            blocks_movement=True,
            render_order=RenderOrder.ACTOR,
        )
        self.fighters = fighters
        self.ai = ai_cls(self)

    @property
    def is_alive(self) -> bool:
        """Returns True as long as there are any living fighters in this group."""
        for fighter in self.fighters:
            if fighter.is_alive:
                return True
        return False

    def distance(self, x: int, y: int) -> float:
        """
        Return the distance between the current entity and the given (x, y) coordinate.
        """
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def move(self, dx: int, dy: int) -> None:
        # Move the entity by a given amount
        self.x += dx
        self.y += dy

    @property
    def inventory(self) -> Inventory:
        """Return the player's inventory. Should only be used by the player group."""
        return self.fighters[0].inventory

    def __len__(self) -> int:
        return len(self.fighters)

    def __iter__(self) -> Iterable:
        return iter(self.fighters)

    def __getitem__(self, key: int):
        try:
            item = self.fighters[key]
        except IndexError:
            raise
        return item

    def __setitem__(self, key: int, value: Fighter):
        try:
            self.fighters[key] = value
        except IndexError:
            raise


class Item(MapEntity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        consumable: Optional[Consumable] = None,
        equippable: Optional[Equippable] = None,
        stackable: bool = False
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=False,
            render_order=RenderOrder.ITEM,
        )

        self.consumable = consumable

        if self.consumable:
            self.consumable.parent = self

        self.equippable = equippable

        if self.equippable:
            self.equippable.parent = self

        self.stackable = stackable
