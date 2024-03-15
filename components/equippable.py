from __future__ import annotations

from typing import TYPE_CHECKING

from components.base_component import BaseComponent
from equipment_types import EquipmentType
from weapon_types import WeaponType

if TYPE_CHECKING:
    from entity import Item
    from components.equipment import Equipment


class Equippable(BaseComponent):
    parent: Item

    def __init__(self, equipment_type: EquipmentType):
        self.equipment_type = equipment_type

    def on_equip(self, equipment: Equipment) -> None:
        """What to do when equipping this item, e.g. apply a strength bonus."""
        pass

    def on_unequip(self, equipment: Equipment) -> None:
        """What to do when unequipping this item, e.g. remove a strength bonus"""
        pass

    @property
    def name(self) -> str:
        return self.parent.name


class Weapon(Equippable):
    attack_bonus: int
    damage_bonus: int

    def __init__(
            self,
            equipment_type: EquipmentType,
            weapon_type: WeaponType,
            min_damage: int,
            max_damage: int,
            two_handed: bool = False,  # If True, this weapon requires both main hand and offhand slots
            offhand: bool = False,  # If True, this weapon can be equipped in the offhand slot
    ):
        super().__init__(equipment_type=equipment_type)

        self.two_handed = two_handed
        self.offhand = offhand
        self.min_damage = min_damage
        self.max_damage = max_damage
        self.weapon_type = weapon_type
        self.attack_bonus = 0
        self.damage_bonus = 0


class Armor(Equippable):
    armor_bonus: int

    def __init__(
            self,
            equipment_type: EquipmentType,
            armor_bonus: int,
            agility_penalty: int = 0,  # Heavier armors penalize the player's agility
    ):
        super().__init__(equipment_type=equipment_type)

        self.agility_penalty = agility_penalty
        self.armor_bonus = armor_bonus

    def on_equip(self, equipment: Equipment) -> None:
        equipment.armor_bonus += self.armor_bonus
        equipment.agility_bonus -= self.agility_penalty

    def on_unequip(self, equipment: Equipment) -> None:
        equipment.armor_bonus -= self.armor_bonus
        equipment.agility_bonus += self.agility_penalty


class Dagger(Weapon):
    def __init__(self) -> None:
        super().__init__(
            weapon_type=WeaponType.AGILITY,
            equipment_type=EquipmentType.WEAPON,
            min_damage=1,
            max_damage=4,
            offhand=True
        )


class ShortSword(Weapon):
    def __init__(self) -> None:
        super().__init__(
            weapon_type=WeaponType.FINESSE,
            equipment_type=EquipmentType.WEAPON,
            min_damage=2,
            max_damage=6
        )


class LeatherArmor(Armor):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.ARMOR, armor_bonus=1)


class ChainMail(Armor):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.ARMOR, agility_penalty=1, armor_bonus=3)
