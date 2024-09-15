from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

from components.base_component import BaseComponent
from components.equippable import Equippable, Weapon
from equipment_types import EquipmentType
from equipment_slots import EquipmentSlot

if TYPE_CHECKING:
    from components.fighter import Player
    from entity import Item


class Equipment(BaseComponent):
    items: Dict[EquipmentSlot, Optional[Equippable]]
    parent: Player

    def __init__(self):
        self.items = {slot: None for slot in EquipmentSlot}

    def item_is_equipped(self, slot: EquipmentSlot) -> bool:
        return self.items[slot] is not None

    def unequip_message(self, item_name: str) -> None:
        self.parent.engine.message_log.add_message(
            f"You remove the {item_name}."
        )

    def equip_message(self, item_name: str) -> None:
        self.parent.engine.message_log.add_message(
            f"You equip the {item_name}."
        )

    def equip_to_slot(self, slot: EquipmentSlot, item: Item, add_message: bool) -> None:
        current_item = self.items[slot]

        if current_item is not None:
            self.unequip_from_slot(slot, add_message)

        if self.parent.inventory.has_item(item):
            self.parent.inventory.remove_item(item)

        item.parent = self
        self.items[slot] = item.equippable

        item.equippable.on_equip(self)

        if (
                slot == EquipmentSlot.MAINHAND and
                item.equippable.two_handed and
                self.items[EquipmentSlot.OFFHAND] is not None
        ):
            self.unequip_from_slot(EquipmentSlot.OFFHAND, add_message)

        if add_message:
            self.equip_message(item.name)

    def unequip_from_slot(self, slot: EquipmentSlot, add_message: bool) -> None:
        current_item = self.items[slot]
        if current_item is not None:
            self.items[slot] = None
            self.parent.inventory.add_item(current_item.parent)
            current_item.parent.parent = self.parent.inventory

            current_item.on_unequip(self)

            if add_message:
                self.unequip_message(current_item.parent.name)

    def toggle_equip(self, slot: EquipmentSlot, item_to_equip: Item, add_message: bool = True) -> None:
        """Unequip the item currently in 'slot' and equip 'item_to_equip' instead."""
        self.unequip_from_slot(slot, add_message)
        self.equip_to_slot(slot, item_to_equip, add_message)

    def list_equipped_items(self) -> List[str]:
        result = []
        for slot, item in sorted(self.items.items()):
            if item is None:
                name = "None"
            else:
                name = item.parent.name
            result.append(f"{slot.name.capitalize() + ':': <9} {name}")
        return result

    @staticmethod
    def get_slot_type(slot: EquipmentSlot) -> EquipmentType:
        match slot:
            case EquipmentSlot.MAINHAND | EquipmentSlot.OFFHAND:
                return EquipmentType.WEAPON
            case EquipmentSlot.ARMOR:
                return EquipmentType.ARMOR
            case EquipmentSlot.HEAD:
                return EquipmentType.HEAD
            case EquipmentSlot.TRINKET:
                return EquipmentType.TRINKET
            case EquipmentSlot.POTION_1 | EquipmentSlot.POTION_2 | EquipmentSlot.POTION_3 | EquipmentSlot.POTION_4:
                return EquipmentType.POTION
