from __future__ import annotations

import sys
from typing import Optional, TYPE_CHECKING

import random

import actions
import colors
import components.ai
import components.inventory
from components.base_component import BaseComponent
from exceptions import Impossible
from input_handlers import (
    ActionOrHandler,
    SelectTargetEventHandler,
    CombatEventHandler,
)

if TYPE_CHECKING:
    from mapentity import Item
    from components.fighter import Fighter


class Consumable(BaseComponent):
    parent: Item

    def get_action(self, consumer: Fighter) -> Optional[ActionOrHandler]:
        """Try to return the action for this item"""
        return actions.ItemAction(consumer, self.parent)

    def activate(self, action: actions.ItemAction) -> None:
        """Invoke this item's ability.

        'action' is the context for this activation.
        """
        raise NotImplementedError()

    def consume(self) -> None:
        """Remove the consumed item from its containing inventory."""
        entity = self.parent
        inventory = entity.parent
        if isinstance(inventory, components.inventory.Inventory):
            inventory.remove_item(entity)


class ConfusionConsumable(Consumable):
    def __init__(self, number_of_turns: int):
        self.number_of_turns = number_of_turns

    def get_action(self, consumer: Fighter) -> Optional[ActionOrHandler]:
        if self.engine.in_combat:
            return SelectTargetEventHandler(
                engine=self.engine,
                parent=CombatEventHandler(self.engine),
                action=actions.ItemAction(entity=consumer, item=self.parent, target=None)
            )
        else:
            self.engine.message_log.add_message("You can only use this item in combat.", colors.invalid)
            return None

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        target = action.target

        if not target:
            raise Impossible("You must select an enemy to target.")
        if target is consumer:
            raise Impossible("You cannot confuse yourself!")

        if consumer.roll_spell_attack() >= target.magic_defense:
            self.engine.message_log.add_message(
                f"The eyes of the {target.name} look vacant, as it starts to stumble around!",
                colors.status_effect_applied,
            )
            target.ai = components.ai.ConfusedEnemy(
                entity=target, previous_ai=target.ai, turns_remaining=self.number_of_turns
            )
        else:
            self.engine.message_log.add_message(
                f"The {target.name} resists the effect, and the spell fizzles!",
                colors.invalid,
            )
        self.consume()


class FireballDamageConsumable(Consumable):
    def __init__(self, damage: int):
        self.damage = damage

    def get_action(self, consumer: Fighter) -> Optional[ActionOrHandler]:
        if self.engine.in_combat:
            return actions.ItemAction(entity=consumer, item=self.parent)
        else:
            self.engine.message_log.add_message("You can only use this item in combat.", colors.invalid)
            return None

    def activate(self, action: actions.ItemAction) -> None:
        caster = action.entity
        targets_hit = False
        for enemy in self.engine.active_enemies.fighters:
            if enemy.is_alive:
                if caster.roll_spell_attack() < enemy.magic_defense:
                    damage = self.damage // 2
                else:
                    damage = self.damage
                self.engine.message_log.add_message(
                    f"The {enemy.name} is engulfed in a fiery explosion, taking {damage} damage!"
                )
                enemy.take_damage(damage)
                targets_hit = True

        if not targets_hit:
            raise Impossible("All available targets are dead.")
        self.consume()


class HealingConsumable(Consumable):
    def __init__(self, min_amount: int, max_amount):
        self.min_amount = min_amount
        self.max_amount = max_amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        amount = random.randint(self.min_amount, self.max_amount)
        amount_recovered = consumer.heal(amount)

        if amount_recovered > 0:
            if consumer == self.engine.player[0]:
                message = f"You consume the {self.parent.name}, and recover {amount_recovered} HP!"
            else:
                message = f"The {consumer.name} consumes the {self.parent.name}, and recovers {amount_recovered} HP!"
            self.engine.message_log.add_message(message, colors.health_recovered)
            self.consume()
        else:
            raise Impossible(f"Your health is already full.")


class ManaConsumable(Consumable):
    def __init__(self, amount: int):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        amount_recovered = consumer.restore_mana(self.amount)

        if amount_recovered > 0:
            if consumer == self.engine.player[0]:
                message = f"You consume the {self.parent.name}, and recover {amount_recovered} mana!"
            else:
                message = f"The {consumer.name} consumes the {self.parent.name}, and recovers {amount_recovered} mana!"
            self.engine.message_log.add_message(message,colors.health_recovered)
            self.consume()
        else:
            raise Impossible(f"Your mana is already full.")


class LightningDamageConsumable(Consumable):
    def __init__(self, damage: int):
        self.damage = damage

    def get_action(self, consumer: Fighter) -> Optional[ActionOrHandler]:
        if self.engine.in_combat:
            return SelectTargetEventHandler(
                engine=self.engine,
                parent=CombatEventHandler(self.engine),
                action=actions.ItemAction(entity=consumer, item=self.parent, target=None)
            )
        else:
            self.engine.message_log.add_message("You can only use this item in combat.", colors.invalid)
            return None

    def activate(self, action: actions.ItemAction) -> None:
        caster = action.entity
        target = action.target

        attack = caster.roll_spell_attack()
        if attack >= target.avoidance:
            if attack == sys.maxsize:
                damage = self.damage * 2
            else:
                damage = self.damage
            self.engine.message_log.add_message(
                f"A lightning bolt strikes the {target.name} with a loud thunder, for {damage} damage!"
            )
            target.take_damage(damage)
        self.consume()
