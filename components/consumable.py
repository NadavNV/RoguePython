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
from status_types import StatusType

if TYPE_CHECKING:
    from entity import Item
    from components.fighter import Fighter


class Consumable(BaseComponent):
    parent: Item

    def get_action(self, consumer: Fighter) -> Optional[ActionOrHandler]:
        """Try to return the action for this item"""
        return actions.ItemAction(consumer, self.parent)

    def activate(self, action: actions.ItemAction) -> bool:
        """Invoke this item's ability.

        'action' is the context for this activation.

        returns True if the activation was successful
        """
        raise NotImplementedError()

    def consume(self) -> None:
        """Remove the consumed item from its containing inventory."""
        entity = self.parent
        inventory = entity.parent
        if isinstance(inventory, components.inventory.Inventory):
            inventory.remove_item(entity)


class FireballDamageConsumable(Consumable):
    def __init__(self, damage: int):
        self.damage = damage

    def get_action(self, consumer: Fighter) -> Optional[ActionOrHandler]:
        if self.engine.in_combat:
            return actions.ItemAction(entity=consumer, item=self.parent)
        else:
            self.engine.message_log.add_message("You can only use this item in combat.", colors.invalid)
            return None

    def activate(self, action: actions.ItemAction) -> bool:
        caster = action.entity
        targets_hit = False
        for enemy in self.engine.active_enemies.fighters:
            if enemy.is_alive:
                self.engine.message_log.add_message(
                    f"The {enemy.name} is engulfed in a fiery explosion, taking {self.damage} damage!"
                )
                enemy.take_damage(self.damage)
                targets_hit = True

        if not targets_hit:
            raise Impossible("All available targets are dead.")
        self.consume()
        return True


class HealingConsumable(Consumable):
    def __init__(self, min_amount: int, max_amount):
        self.min_amount = min_amount
        self.max_amount = max_amount

    def activate(self, action: actions.ItemAction) -> bool:
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
            return True
        else:
            raise Impossible(f"Your health is already full.")


class ManaConsumable(Consumable):
    def __init__(self, amount: int):
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> bool:
        consumer = action.entity
        amount_recovered = consumer.restore_mana(self.amount)

        if amount_recovered > 0:
            if consumer == self.engine.player[0]:
                message = f"You consume the {self.parent.name}, and recover {amount_recovered} mana!"
            else:
                message = f"The {consumer.name} consumes the {self.parent.name}, and recovers {amount_recovered} mana!"
            self.engine.message_log.add_message(message, colors.health_recovered)
            self.consume()
            return True
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

    def activate(self, action: actions.ItemAction) -> bool:
        target = action.target
        hit_successful = False

        if target.buffs[StatusType.EVASION] == 0:
            self.engine.message_log.add_message(
                f"A lightning bolt strikes the {target.name} with a loud thunder, for {self.damage} damage!"
            )
            target.take_damage(self.damage)
            hit_successful = True
        else:
            self.engine.message_log.add_message(
                f"The {target.name} quickly moves out of the way of the lightning bolt!"
            )
            target.buffs[StatusType.EVASION] -= 1
        self.consume()
        return hit_successful
