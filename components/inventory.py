from __future__ import annotations

from typing import List, TYPE_CHECKING

from components.base_component import BaseComponent

if TYPE_CHECKING:
    from entity import Actor, Item

MAX_STACK_SIZE = 99


class Inventory(BaseComponent):
    parent: Actor

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items: List[List[Item]] = []

    def drop(self, item: Item) -> None:
        """
        Removes an item from the inventory and restores it to the game map, at the player's current location.
        """
        self.remove_item(item)
        item.place(self.parent.x, self.parent.y, self.game_map)

        self.engine.message_log.add_message(f"You dropped the {item.name}.")

    def remove_item(self, item: Item) -> None:
        """
        Removes an item from the inventory and restores it to the game map, at the player's current location.
        """
        for stack in range(len(self.items)):
            if item in self.items[stack]:
                self.items[stack].remove(item)

                if len(self.items[stack]) == 0:
                    del self.items[stack]

                break

    def add_item(self, item: Item) -> None:
        item.parent = self
        if item.stackable:
            for stack in self.items:
                if item.name == stack[0].name and len(stack) < MAX_STACK_SIZE:
                    stack.append(item)
                    return None

        # Item is not stackable or can't fit in any existing stack
        self.items.append([item])

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
