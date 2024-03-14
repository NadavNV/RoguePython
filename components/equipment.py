from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING

from components.base_component import BaseComponent
from components.equippable import Equippable
from equipment_types import EquipmentType
from equipment_slots import EquipmentSlot

if TYPE_CHECKING:
    from entity import Actor, Item


class Equipment(BaseComponent):
    items: Dict[EquipmentSlot, Equippable]
    parent: Actor

    armor_bonus: int

    mainhand_attack_bonus: int
    mainhand_min_damage: int
    mainhand_max_damage: int

    offhand_attack_bonus: int
    offhand_min_damage: int
    offhand_max_damage: int

    spell_attack_bonus: int

    strength_bonus: int
    perseverance_bonus: int
    agility_bonus: int
    magic_bonus: int

    avoidance_bonus: int

    def __init__(self):
        self.items = {slot: None for slot in EquipmentSlot}

        self.strength_bonus = 0
        self.perseverance_bonus = 0
        self.agility_bonus = 0
        self.magic_bonus = 0
        self.armor_bonus = 0
        self.avoidance_bonus = 0
        self.spell_attack_bonus = 0

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

        if self.parent.inventory.has_item(item):
            self.parent.inventory.remove_item(item)

        item.parent = self
        self.items[slot] = item.equippable

        item.equippable.on_equip(self)

        if slot == EquipmentSlot.MAINHAND:
            self.mainhand_max_damage = item.equippable.max_damage + item.equippable.damage_bonus
            self.mainhand_min_damage = item.equippable.min_damage + item.equippable.damage_bonus
            self.mainhand_attack_bonus = item.equippable.attack_bonus
        elif slot == EquipmentSlot.OFFHAND:
            self.offhand_max_damage = item.equippable.max_damage + item.equippable.damage_bonus
            self.offhand_min_damage = item.equippable.min_damage + item.equippable.damage_bonus
            self.offhand_attack_bonus = item.equippable.attack_bonus

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
            if slot == EquipmentSlot.MAINHAND:
                self.mainhand_max_damage = self.parent.fighter.strength // 2
                self.mainhand_min_damage = self.parent.fighter.strength // 2
                self.mainhand_attack_bonus = self.parent.fighter.strength // 2
            elif slot == EquipmentSlot.OFFHAND:
                self.offhand_max_damage = self.parent.fighter.strength // 2
                self.offhand_min_damage = self.parent.fighter.strength // 2
                self.offhand_attack_bonus = self.parent.fighter.strength // 2

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
