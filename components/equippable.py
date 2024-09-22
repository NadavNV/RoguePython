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

    def __init__(
            self,
            two_handed: bool = False,  # If True, this weapon requires both main hand and offhand slots
            offhand: bool = False,  # If True, this weapon can be equipped in the offhand slot
            *,
            other: Weapon = None,
    ):
        super().__init__(equipment_type=EquipmentType.WEAPON)

        if other is not None:
            self.two_handed = other.two_handed
            self.offhand = other.offhand
        else:
            self.two_handed = two_handed
            self.offhand = offhand


class Armor(Equippable):

    def __init__(
            self,
            equipment_type: EquipmentType,
    ):
        super().__init__(equipment_type=equipment_type)


class Dagger(Weapon):
    def __init__(self) -> None:
        super().__init__(
            offhand=True
        )


class Club(Weapon):
    def __init__(self) -> None:
        super().__init__(
            offhand=True
        )


class ShortSword(Weapon):
    def __init__(self) -> None:
        super().__init__()


class Broom(Weapon):
    def __init__(self) -> None:
        super().__init__()


class Handaxe(Weapon):
    def __init__(self) -> None:
        super().__init__(
            offhand=True,
        )


class Greatsword(Weapon):
    def __init__(self) -> None:
        super().__init__(
            two_handed=True,
        )


class Wand(Weapon):
    def __init__(self) -> None:
        super().__init__()


class Staff(Weapon):
    def __init__(self) -> None:
        super().__init__(
            two_handed=True,
        )


class LeatherArmor(Armor):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.ARMOR)

    def on_equip(self, equipment: Equipment) -> None:
        print("Equipping Leather Armor")
        equipment.parent.max_hp += 10
        equipment.parent.hp += 10

    def on_unequip(self, equipment: Equipment) -> None:
        print("Unequipping Leather Armor")
        equipment.parent.max_hp -= 10
        equipment.parent.hp = min(equipment.parent.hp, equipment.parent.max_hp)


class ChainMail(Armor):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.ARMOR)
