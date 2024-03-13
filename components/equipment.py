from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

from components.base_component import BaseComponent
from components.equippable import Equippable
from equipment_types import EquipmentType
from equipment_slots import EquipmentSlot

if TYPE_CHECKING:
    from entity import Actor, Item


class Equipment(BaseComponent):
    parent: Actor

    def __init__(self, items: Optional[Dict[EquipmentSlot, Equippable]]):
        self.items = {}
        for slot in EquipmentSlot:
            self.items[slot] = None

        if items is not None:
            for slot, item in items:
                self.items[slot] = item

    @property
    def defense_bonus(self) -> int:
        bonus = 0

        for slot, item in self.items.items():
            if item is not None and item.equippable is not None:
                bonus += item.equippable.defense_bonus

        return bonus

    @property
    def power_bonus(self) -> int:
        bonus = 0

        for slot, item in self.items.items():
            if item is not None and item.equippable is not None:
                bonus += item.equippable.power_bonus

        return bonus

    def item_is_equipped(self, slot: EquipmentSlot) -> bool:
        return self.items[slot] is not None

    def unequip_message(self, item_name: str) -> None:
        self.parent.game_map.engine.message_log.add_message(
            f"You remove the {item_name}."
        )

    def equip_message(self, item_name: str) -> None:
        self.parent.game_map.engine.message_log.add_message(
            f"You equip the {item_name}."
        )

    def equip_to_slot(self, slot: EquipmentSlot, item: Item, add_message: bool) -> None:
        current_item = self.items[slot]

        if current_item is not None:
            self.unequip_from_slot(slot, add_message)

        if item in self.parent.inventory.items:
            self.parent.inventory.items.remove(item)

        self.items[slot] = item

        if (
                slot == EquipmentSlot.MAINHAND and
                item.equippable.two_handed and
                self.items[EquipmentSlot.OFFHAND] is not None
        ):
            self.unequip_from_slot(EquipmentSlot.OFFHAND, add_message)

        if add_message:
            self.equip_message(item.name)

    def unequip_from_slot(self, slot: EquipmentSlot, add_message: bool) -> None:
        current_item = self.items.pop(slot)
        self.items[slot] = None
        self.parent.inventory.items.append(current_item)

        if add_message:
            self.unequip_message(current_item.name)

    def toggle_equip(self, slot: EquipmentSlot, item_to_equip: Item, add_message: bool = True) -> None:
        """Unequips the item currently in 'slot' and equips 'item_to_equip' instead."""
        self.unequip_from_slot(slot, add_message)
        self.equip_to_slot(slot, item_to_equip, add_message)

    def list_equipped_items(self) -> List[str]:
        result = []
        for slot, item in self.items.items():
            if item is None:
                name = "None"
            else:
                name = item.name
            result.append(f"{slot.name.capitalize() + ':': <9} {name}")
        return result

    @staticmethod
    def get_slot_type(slot: EquipmentSlot) -> EquipmentType:
        if slot == EquipmentSlot.MAINHAND:
            return EquipmentType.WEAPON
        elif slot == EquipmentSlot.OFFHAND:
            return EquipmentType.WEAPON
        elif slot == EquipmentSlot.ARMOR:
            return EquipmentType.ARMOR
        elif slot == EquipmentSlot.HEAD:
            return EquipmentType.HEAD
        elif slot == EquipmentSlot.TRINKET1:
            return EquipmentType.TRINKET
        elif slot == EquipmentSlot.TRINKET2:
            return EquipmentType.TRINKET
