from __future__ import annotations

from typing import TYPE_CHECKING

from components.base_component import BaseComponent
from equipment_types import EquipmentType
from weapon_types import WeaponType

if TYPE_CHECKING:
    from entity import Item


class Equippable(BaseComponent):
    parent: Item

    def __init__(
            self,
            equipment_type: EquipmentType,
            power_bonus: int = 0,
            defense_bonus: int = 0,
    ):
        self.equipment_type = equipment_type

        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus


class Weapon(Equippable):
    def __init__(
            self,
            equipment_type: EquipmentType,
            weapon_type: WeaponType,
            min_damage: int,
            max_damage: int,
            power_bonus: int = 0,
            defense_bonus: int = 0,
            two_handed: bool = False,  # If True, this weapon requires both main hand and offhand slots
            offhand: bool = False,  # If True, this weapon can be equipped in the offhand slot
    ):
        super().__init__(equipment_type=equipment_type, power_bonus=power_bonus, defense_bonus=defense_bonus)

        self.two_handed = two_handed
        self.offhand = offhand
        self.min_damage = min_damage
        self.max_damage = max_damage
        self.weapon_type = weapon_type


class Armor(Equippable):
    def __init__(
            self,
            equipment_type: EquipmentType,
            agility_penalty: int = 0,  # Heavier armors penalize the player's agility
            power_bonus: int = 0,
            defense_bonus: int = 0,
    ):
        super().__init__(equipment_type=equipment_type, power_bonus=power_bonus, defense_bonus=defense_bonus)

        self.agility_penalty = agility_penalty


class Dagger(Weapon):
    def __init__(self) -> None:
        super().__init__(weapon_type=WeaponType.AGILITY, equipment_type=EquipmentType.WEAPON, min_damage=1, max_damage=4, power_bonus=2, offhand=True)


class ShortSword(Weapon):
    def __init__(self) -> None:
        super().__init__(weapon_type= WeaponType.FINESSE, equipment_type=EquipmentType.WEAPON, min_damage=2, max_damage=6, power_bonus=4)


class LeatherArmor(Armor):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.ARMOR, defense_bonus=1)


class ChainMail(Armor):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.ARMOR, agility_penalty=1, defense_bonus=3)
