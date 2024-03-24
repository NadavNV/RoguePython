from __future__ import annotations

from typing import TYPE_CHECKING

from components.base_component import BaseComponent
from equipment_types import EquipmentType
from weapon_types import WeaponType

if TYPE_CHECKING:
    from mapentity import Item
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
            weapon_type: WeaponType = WeaponType.FINESSE,
            min_damage: int = 0,
            max_damage: int = 0,
            two_handed: bool = False,  # If True, this weapon requires both main hand and offhand slots
            offhand: bool = False,  # If True, this weapon can be equipped in the offhand slot
            *,
            other: Weapon = None,
    ):
        super().__init__(equipment_type=EquipmentType.WEAPON)

        if other is not None:
            self.two_handed = other.two_handed
            self.offhand = other.offhand
            self.min_damage = other.min_damage
            self.max_damage = other.max_damage
            self.weapon_type = other.weapon_type
            self.attack_bonus = other.attack_bonus
            self.damage_bonus = other.damage_bonus
        else:
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


class EnhancedWeapon(Weapon):
    def __init__(self, *, parent: Item, n: int):
        # TODO: This should be a class method of Weapon/Armor rather than a subclass
        super().__init__(other=parent.equippable)
        self.parent = parent
        parent.equippable = self

        self.min_damage += n
        self.max_damage += n
        self.attack_bonus += n

        self.parent.name += f" +{n}"
        self.parent.buy_price *= n * 3
        self.parent.sell_price *= n * 3


class Dagger(Weapon):
    def __init__(self) -> None:
        super().__init__(
            weapon_type=WeaponType.AGILITY,
            min_damage=1,
            max_damage=4,
            offhand=True
        )


class Club(Weapon):
    def __init__(self) -> None:
        super().__init__(
            weapon_type=WeaponType.STRENGTH,
            min_damage=1,
            max_damage=4,
            offhand=True
        )


class ShortSword(Weapon):
    def __init__(self) -> None:
        super().__init__(
            weapon_type=WeaponType.FINESSE,
            min_damage=1,
            max_damage=5
        )


class Broom(Weapon):
    def __init__(self) -> None:
        super().__init__(
            weapon_type=WeaponType.AGILITY,
            min_damage=1,
            max_damage=3
        )


class Handaxe(Weapon):
    def __init__(self) -> None:
        super().__init__(
            weapon_type=WeaponType.STRENGTH,
            min_damage=1,
            max_damage=4
        )


class LeatherArmor(Armor):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.ARMOR, armor_bonus=1)


class ChainMail(Armor):
    def __init__(self) -> None:
        super().__init__(equipment_type=EquipmentType.ARMOR, agility_penalty=1, armor_bonus=3)


if __name__ == "__main__":
    from mapentity import Item
    dagger = Item(
        buy_price=25,
        sell_price=5,
        char="/",
        color=(0, 191, 255),
        name="Dagger",
        description="Fine steel, good for stabbing. Can be used in the off hand. Agility weapon.",
        equippable=Dagger(),
    )
    EnhancedWeapon(parent=dagger, n=1)
    print(dagger.name)
    print(f"Attack: +{dagger.equippable.attack_bonus}")
    print(f"Damage: {dagger.equippable.min_damage} - {dagger.equippable.max_damage}")
    print(dagger.buy_price)
    print(dagger.sell_price)
    print(dagger.equippable)

