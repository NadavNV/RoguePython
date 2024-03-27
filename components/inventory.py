from __future__ import annotations
import random

from typing import List, TYPE_CHECKING

from components.base_component import BaseComponent
from exceptions import Impossible

if TYPE_CHECKING:
    from entity import Item
    from components.fighter import Fighter

MAX_STACK_SIZE = 99


class Inventory(BaseComponent):
    parent: Fighter

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items: List[List[Item]] = []
        self.gold = 0

    def drop(self, item: Item) -> None:
        """
        Removes an item from the inventory and restores it to the game map, at the player's current location.
        """
        self.remove_item(item)
        item.place(self.parent.parent.x, self.parent.parent.y, self.game_map)

        self.engine.message_log.add_message(f"You dropped the {item.name}.")

    def remove_item(self, item: Item) -> None:
        """
        Removes an item from the inventory.
        """
        for stack in range(len(self.items)):
            if item in self.items[stack]:
                self.items[stack].remove(item)

                if len(self.items[stack]) == 0:
                    del self.items[stack]

                break

    def add_item(self, item: Item) -> None:
        if len(self.items) < self.capacity:
            item.parent = self
            if item.stackable:
                for stack in self.items:
                    if item.name == stack[0].name and len(stack) < MAX_STACK_SIZE:
                        stack.append(item)
                        return None

            # Item is not stackable or can't fit in any existing stack
            self.items.append([item])
        else:
            if not item.stackable:
                raise Impossible("Inventory is full")
            else:
                for stack in self.items:
                    if item.name == stack[0].name and len(stack) < MAX_STACK_SIZE:
                        stack.append(item)
                        return None
                raise Impossible("Inventory is full")

    def list_items(self) -> List[str]:
        """Creates a list of the items in the inventory, with their amounts if stacked."""
        result = []

        for stack in self.items:
            if len(stack) == 1:
                result.append(f"{stack[0].name}")
            else:
                result.append(f"{stack[0].name} (x{len(stack)})")

        return result

    def has_item(self, item: Item) -> bool:
        for stack in self.items:
            if item in stack:
                return True
        return False
