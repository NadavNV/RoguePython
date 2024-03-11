from __future__ import annotations

from typing import List, TYPE_CHECKING

from components.base_component import BaseComponent

if TYPE_CHECKING:
    from entity import Actor, Item


class Inventory(BaseComponent):
    parent: Actor

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items: List[Item] = []

    def drop(self, item: Item) -> None:
        """
        Removes an item from the inventory and restores it to the game map, at the player's current location.
        """
        self.items.remove(item)
        item.place(self.parent.x, self.parent.y, self.game_map)

        self.engine.message_log.add_message(f"You dropped the {item.name}.")

    def list_items(self) -> List[str]:
        """Creates a list of the items in the inventory, with their amounts if stackable."""
        result = []
        item_amounts = {}
        for item in self.items:
            if item.name in item_amounts and item.stackable:
                item_amounts[item.name] += 1
            else:
                item_amounts[item.name] = 1

        for item in item_amounts:
            result.append(item if item_amounts[item] == 1 else f"{item} (x{item_amounts[item]})")

        return result
