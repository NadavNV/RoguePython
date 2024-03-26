from __future__ import annotations

import sys
import copy
from typing import List, Tuple, Type, TYPE_CHECKING

import random

import colors
from components.base_component import BaseComponent
from components.equipment import Equipment
from components.inventory import Inventory
from components.level import Level
from dropgen.RDSObject import RDSObject
from dropgen.RDSValue import RDSValue
from dropgen.RDSTable import RDSTable
from entity import Item
from equipment_slots import EquipmentSlot
from equipment_types import EquipmentType
from fighter_classes import FighterClass
from weapon_types import WeaponType

if TYPE_CHECKING:
    from actions import Ability
    from components.ai import BaseAI
    from engine import Engine
    from entity import FighterGroup

BASE_DEFENSE = 10


class Fighter(BaseComponent, RDSObject):
    parent: FighterGroup
    """
    Strength - Affects damage with weapons and block amount with shields.
    Perseverance - Affects max hp.
    Agility - Affects chance to hit with weapons and chance to avoid attacks.
    Magic - Affects damage and chance to hit with spells, magic resistance, and max mana.
    
    Bonus = stat // 2
    
    3 points to spend when leveling up.
    Avoidance = 10 + Agility bonus.
    Armor reduces weapon damage, heavier armor penalizes Agility. (You're easier to hit, but you take less damage)
    Proficiency bonus = 1 + level // 4, added to attack rolls with proficient weapons and spell attacks.
    Warrior is proficient with swords and axes, rogue is proficient with daggers and rapiers. Mage
    is proficient with spells.
    """

    def __init__(
            self,
            strength: int,
            perseverance: int,
            agility: int,
            magic: int,
            min_hp_per_level: int,
            max_hp_per_level: int,
            fighter_class: FighterClass,
            ai_cls: Type[BaseAI],
            inventory: Inventory = Inventory(capacity=26),
            equipment: Equipment = Equipment(),
            level: Level = Level(),
            abilities: List[Ability] = None,
            mana: int = 0,
            weapon_crit_threshold: int = 20,
            spell_crit_threshold: int = 20,
            char: str = "?",
            color: Tuple[int, int, int] = colors.white,
            name: str = "<Unnamed>",
            sprite: str = "images/rogue_icon.png"
    ):
        super().__init__()
        self.char = char
        self.name = name
        self.color = color
        self.sprite = colors.image_to_rgb(sprite)

        self.fighter_class = fighter_class

        self.strength = strength
        self.perseverance = perseverance
        self.agility = agility
        self.magic = magic

        self.max_hp_per_level = max_hp_per_level
        self.min_hp_per_level = min_hp_per_level
        self._hp = 0
        self.max_hp = 0

        self.max_mana = mana
        self._mana = mana

        self.equipment = equipment
        self.equipment.parent = self
        self.inventory = inventory
        self.inventory.parent = self
        self.level = level
        self.level.parent = self
        self.abilities = [] if abilities is None else copy.deepcopy(abilities)
        self.ai = ai_cls(self)

        self.weapon_crit_threshold = weapon_crit_threshold
        self.spell_crit_threshold = spell_crit_threshold

        self.roll_hitpoints()

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        self._hp = max(0, min(value, self.max_hp))
        if self._hp == 0 and self.parent.ai:
            self.die()

    @property
    def mana(self) -> int:
        return self._mana

    @mana.setter
    def mana(self, value: int) -> None:
        self._mana = max(0, min(value, self.max_mana))

    @property
    def armor(self) -> int:
        if self.equipment:
            return self.equipment.armor_bonus
        else:
            return 0

    @property
    def avoidance(self) -> int:
        return BASE_DEFENSE + (self.agility + self.equipment.agility_bonus) // 2 + self.equipment.avoidance_bonus

    @property
    def magic_defense(self) -> int:
        return BASE_DEFENSE + (self.magic + self.equipment.magic_bonus) // 2 + self.equipment.magic_resistance

    @property
    def mainhand_attack_bonus(self) -> int:
        return self.weapon_base_attack_bonus(EquipmentSlot.MAINHAND) + self.equipment.mainhand_attack_bonus

    @property
    def offhand_attack_bonus(self) -> int:
        return self.weapon_base_attack_bonus(EquipmentSlot.OFFHAND) + self.equipment.offhand_attack_bonus

    @property
    def spell_attack_bonus(self) -> int:
        bonus = (self.magic + self.equipment.magic_bonus) // 2
        if self.fighter_class == FighterClass.MAGE:
            bonus += self.level.proficiency
        return bonus

    def weapon_base_attack_bonus(self, slot: EquipmentSlot) -> int:
        weapon = self.equipment.items[slot]
        bonus = (self.agility + self.equipment.agility_bonus) // 2
        if weapon is not None and hasattr(weapon, 'weapon_type'):
            if self.fighter_class == FighterClass.ROGUE and (
                    weapon.weapon_type == WeaponType.AGILITY or
                    weapon.weapon_type == WeaponType.FINESSE
            ):
                bonus += self.level.proficiency
            elif self.fighter_class == FighterClass.WARRIOR and (
                    weapon.weapon_type == WeaponType.STRENGTH or
                    weapon.weapon_type == WeaponType.FINESSE
            ):
                bonus += self.level.proficiency
            elif self.fighter_class == FighterClass.MAGE and weapon.weapon_type == WeaponType.MAGIC:
                bonus += self.level.proficiency
        return bonus

    def die(self) -> None:
        if self.engine.player is self.parent:
            death_message = "You died!"
            death_message_color = colors.player_die
        else:
            death_message = f"{self.name} is dead!"
            death_message_color = colors.enemy_die

        self.char = "%"
        self.color = (191, 0, 0)
        self.ai = None
        self.name = f"Dead {self.parent.name}"

        self.engine.message_log.add_message(death_message, death_message_color)

        self.engine.player[0].level.add_xp(self.level.xp_given)

    def heal(self, amount: int) -> int:
        if self.hp == self.max_hp:
            return 0

        new_hp_value = self.hp + amount

        if new_hp_value > self.max_hp:
            new_hp_value = self.max_hp

        amount_recovered = new_hp_value - self.hp

        self.hp = new_hp_value

        return amount_recovered

    def restore_mana(self, amount: int) -> int:
        if self.mana == self.max_mana:
            return 0

        new_mana_value = self.mana + amount

        if new_mana_value > self.max_mana:
            new_mana_value = self.max_mana

        amount_recovered = new_mana_value - self.mana

        self.mana = new_mana_value

        return amount_recovered

    def take_damage(self, amount: int) -> None:
        self.hp -= amount

    @staticmethod
    def roll_attack(crit_threshold: int, attack_bonus: int, advantage: bool = False) -> int:
        roll = random.randint(1, 20)
        if advantage:
            roll = max(roll, random.randint(1, 20))
        if roll >= crit_threshold:
            return sys.maxsize
        else:
            return roll + attack_bonus

    def roll_weapon_attack(self, slot: EquipmentSlot, advantage: bool = False):
        if slot == EquipmentSlot.MAINHAND:
            return self.roll_attack(self.weapon_crit_threshold, self.mainhand_attack_bonus, advantage=advantage)
        elif slot == EquipmentSlot.OFFHAND and self.equipment.items[slot].equipment_type == EquipmentType.WEAPON:
            return self.roll_attack(self.weapon_crit_threshold, self.offhand_attack_bonus, advantage=advantage)
        else:
            return 0

    def roll_spell_attack(self) -> int:
        return self.roll_attack(
            self.spell_crit_threshold,
            self.spell_attack_bonus,
        )

    def roll_hitpoints(self) -> None:
        new_hp = random.randint(self.min_hp_per_level, self.max_hp_per_level)
        new_hp += (self.perseverance + self.equipment.perseverance_bonus) // 2
        self.max_hp += new_hp
        self._hp += new_hp

    @property
    def is_alive(self) -> bool:
        """Returns True as long as this fighter can perform actions."""
        return bool(self.ai)

    @property
    def engine(self) -> Engine:
        return self.parent.engine

    def roll_weapon_damage(self, slot: EquipmentSlot):
        if slot == EquipmentSlot.MAINHAND:
            return ((self.strength + self.equipment.strength_bonus) // 2 +
                    random.randint(self.equipment.mainhand_min_damage, self.equipment.mainhand_max_damage))
        elif slot == EquipmentSlot.OFFHAND and self.equipment.items[slot].equipment_type == EquipmentType.WEAPON:
            return ((self.strength + self.equipment.strength_bonus) // 2 +
                    random.randint(self.equipment.offhand_min_damage, self.equipment.offhand_max_damage))
        else:
            return 0


class Enemy(Fighter):
    def __init__(
            self,
            target_level: int,
            loot_table: RDSTable,
            stat_prio: RDSTable,
            strength: int,
            perseverance: int,
            agility: int,
            magic: int,
            min_hp_per_level: int,
            max_hp_per_level: int,
            fighter_class: FighterClass,
            ai_cls,
            inventory: Inventory = Inventory(capacity=26),
            equipment: Equipment = Equipment(),
            level: Level = Level(),
            abilities: List[Ability] = None,
            mana: int = 0,
            weapon_crit_threshold: int = 20,
            spell_crit_threshold: int = 20,
            char: str = "?",
            color: Tuple[int, int, int] = colors.white,
            name: str = "<Unnamed>",
            sprite: str = "images/rogue_icon.png",
    ):
        super().__init__(
            strength=strength,
            perseverance=perseverance,
            agility=agility,
            magic=magic,
            min_hp_per_level=min_hp_per_level,
            max_hp_per_level=max_hp_per_level,
            fighter_class=fighter_class,
            ai_cls=ai_cls,
            inventory=inventory,
            equipment=equipment,
            level=level,
            abilities=abilities,
            mana=mana,
            weapon_crit_threshold=weapon_crit_threshold,
            spell_crit_threshold=spell_crit_threshold,
            name=name,
            color=color,
            char=char,
            sprite=sprite
        )

        self.loot_table = loot_table

        while self.level.current_level < target_level:
            self.level.increase_level(stats=[x.rds_value for x in stat_prio.rds_result])

        self.level.xp_given *= self.level.current_level

    def die(self) -> None:
        super().die()

        loot = self.loot_table.rds_result

        for item in loot:
            if isinstance(item, RDSValue):
                print(f"Dropped {item.rds_value} gold")
                self.inventory.gold += item.rds_value
            elif isinstance(item, Item):
                print(f"Dropped {item.name}")
                self.inventory.add_item(item)
