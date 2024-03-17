from __future__ import annotations

from typing import TYPE_CHECKING

import sys

import colors
from actions import Action

if TYPE_CHECKING:
    from components.fighter import Fighter
    from equipment_slots import EquipmentSlot


class Ability(Action):
    def __init__(self, caster: Fighter, cooldown: int = 0):
        super().__init__(entity=caster)
        self.cooldown = cooldown
        self.cooldown_remaining = 0

    def reduce_cooldown(self) -> None:
        self.cooldown_remaining = max(0, self.cooldown_remaining - 1)

    def start_cooldown(self) -> None:
        self.cooldown_remaining = self.cooldown


class TargetedAbility(Ability):
    def __init__(self, caster: Fighter, target: Fighter, cooldown: int = 0):
        super().__init__(caster=caster, cooldown=cooldown)
        self.target = target


class WeaponAttack(TargetedAbility):
    def __init__(
            self,
            caster: Fighter,
            target: Fighter,
            slot: EquipmentSlot,
            cooldown: int = 0,
            with_advantage: bool = False,
    ):
        super().__init__(caster=caster, cooldown=cooldown, target=target)
        self.with_advantage = with_advantage
        self.slot = slot

    def perform(self) -> None:
        attack_desc = f"{self.entity.name.capitalize()} attacks {self.target.name}"

        if self.slot == EquipmentSlot.MAINHAND:
            attack = self.entity.roll_mainhand_attack()
            if attack == sys.maxsize:  # Critical hit
                attack_desc = f"{attack_desc} and critically hits"
                damage = self.entity.roll_mainhand_damage()
            else:
                damage = 0
        else:
            attack = self.entity.roll_offhand_attack()
            if attack == sys.maxsize:  # Critical hit
                attack_desc = f"{attack_desc} and critically hits"
                damage = self.entity.roll_mainhand_damage()
            else:
                damage = 0
            attack -= self.target.avoidance

        damage -= self.target.armor

        if self.entity.parent is self.engine.player:
            attack_color = colors.player_atk
        else:
            attack_color = colors.enemy_atk
        if attack < 0:
            self.engine.message_log.add_message(
                f"{attack_desc} but misses.", attack_color
            )
        elif damage > 0:
            self.engine.message_log.add_message(
                f"{attack_desc} for {damage} hit points.", attack_color
            )
            self.target.hp -= damage
        else:
            self.engine.message_log.add_message(
                f"{attack_desc} but does no damage.", attack_color
            )


class MeleeAttack(TargetedAbility):
    def perform(self) -> None:
        WeaponAttack(caster=self.entity, target=self.target, slot=EquipmentSlot.MAINHAND).perform()
        WeaponAttack(caster=self.entity, target=self.target, slot=EquipmentSlot.OFFHAND).perform()
