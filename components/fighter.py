from __future__ import annotations

from typing import TYPE_CHECKING

import random
import math

import color
from components.base_component import BaseComponent, roll_dice
from render_order import RenderOrder

if TYPE_CHECKING:
    from entity import Actor


class Fighter(BaseComponent):
    parent: Actor
    """
    Strength - Affects damage with weapons and block amount with shields.
    Perseverance - Affects max hp.
    Agility - Affects chance to hit with weapons and chance to avoid attacks.
    Magic - Affects damage and chance to hit with spells, magic resistence, and max mana.
    
    Bonus = stat // 2
    
    3 points to spend when leveling up.
    Avoidance = 10 + Agility bonus.
    Armor reduces weapon damage, heavier armor penalizes Agility. (You're easier to hit, but you take less damage)
    Proficiency bonus = 1 + level modulo 4, added to attack rolls with proficient weapons and spell attacks.
    Warrior is proficient with swords and axes, rogue is proficient with daggers, rapiers, and scimitars. Mage
    is proficient with spells.
    """

    def __init__(
            self,
            strength: int,
            perseverance: int,
            agility: int,
            magic: int,
            hit_dice: str,
            hp: int,
            base_defense: int,
            base_power: int,
            mana: int = 0,
            weapon_crit_threshold: int = 20,
            spell_crit_threshold: int = 20,
            has_weapon_advantage: bool = False,
            has_spell_advantage: bool = False,
    ):
        self.strength = strength
        self.perseverance = perseverance
        self.agility = agility
        self.magic = magic
        # self.max_hp = hp
        self.hit_dice = hit_dice
        self.max_hp = roll_dice(hit_dice) + self.perseverance // 2
        self._hp = self.max_hp
        self.max_mana = mana
        self._mana = mana
        self.base_defense = base_defense
        self.base_power = base_power
        self.weapon_crit_threshold = weapon_crit_threshold
        self.spell_crit_threshold = spell_crit_threshold
        self.has_weapon_advantage = has_weapon_advantage
        self.has_spell_advantage = has_spell_advantage
        self.proficiency = 1

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
    def defense(self) -> int:
        return self.base_defense + self.defense_bonus

    @property
    def power(self) -> int:
        return self.base_power + self.power_bonus

    @property
    def defense_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.defense_bonus
        else:
            return 0

    @property
    def power_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.power_bonus
        else:
            return 0

    def die(self) -> None:
        if self.engine.player is self.parent:
            death_message = "You died!"
            death_message_color = color.player_die
        else:
            death_message = f"{self.parent.name} is dead!"
            death_message_color = color.enemy_die

        self.parent.char = "%"
        self.parent.color = (191, 0, 0)
        self.parent.blocks_movement = False
        self.parent.ai = None
        self.parent.name = f"remains of {self.parent.name}"
        self.parent.render_order = RenderOrder.CORPSE

        self.engine.message_log.add_message(death_message, death_message_color)

        self.engine.player.level.add_xp(self.parent.level.xp_given)

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
            return int(math.inf)
        else:
            return roll + attack_bonus

    def roll_weapon_attack(self) -> int:
        return self.roll_attack(
            self.weapon_crit_threshold,
            self.weapon_attack_bonus,
            self.has_weapon_advantage
        )

    def roll_spell_attack(self) -> int:
        return self.roll_attack(
            self.spell_crit_threshold,
            self.spell_attack_bonus,
            self.has_spell_advantage
        )

    def roll_hit_dice(self) -> None:
        self.max_hp = roll_dice(self.hit_dice) + self.perseverance // 2
        self._hp = self.max_hp