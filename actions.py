from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING, Union

import colors
import exceptions
from equipment_slots import EquipmentSlot
from status_types import StatusType
from entity import FighterGroup, Trader
from components.fighter import Fighter

if TYPE_CHECKING:
    from engine import Engine
    from entity import Item

Actor = Union[Fighter, FighterGroup]


class Action:
    def __init__(self, entity: Actor) -> None:
        super().__init__()
        self.entity = entity

    @property
    def engine(self) -> Engine:
        """Return the engine this action belongs to."""
        return self.entity.engine

    def perform(self) -> bool:
        """Perform this action with the objects needed to determine its scope.

        `self.engine` is the scope this action is being performed in.

        `self.entity` is the object performing the action.

        This method must be overridden by Action subclasses.

        returns True if the action was performed successfully
        """
        raise NotImplementedError()


class PickupAction(Action):
    """Pick up an item and add it to the inventory, if there is room for it."""

    def __init__(self, entity: Actor):
        super().__init__(entity)

    def perform(self) -> bool:
        actor_location_x, actor_location_y = self.entity.x, self.entity.y
        inventory = self.entity.inventory

        for item in self.engine.game_map.items:
            if actor_location_y == item.y and actor_location_x == item.x:
                try:
                    inventory.add_item(item)
                    self.engine.game_map.entities.remove(item)
                    item.parent = inventory
                except exceptions.Impossible as exc:
                    raise exc

                self.engine.message_log.add_message(f"You picked up the {item.name}!")
                return True

        raise exceptions.Impossible("There is nothing here to pick up.")


class ItemAction(Action):
    def __init__(
            self, entity: Actor, item: Item, target: Optional[Fighter] = None
    ):
        super().__init__(entity)
        self.item = item
        if not target:
            target = entity
        self.target = target

    def perform(self) -> bool:
        """Invoke the item's ability, this action will be given to provide context."""
        if self.item.consumable:
            return self.item.consumable.activate(self)


class DropItem(ItemAction):
    def perform(self) -> bool:
        self.entity.inventory.drop(self.item)
        return True


class EquipAction(Action):
    def __init__(self, entity: Actor, item: Item, slot: EquipmentSlot):
        super().__init__(entity)

        self.item = item
        self.slot = slot

    def perform(self) -> bool:
        if self.entity.equipment.item_is_equipped(self.slot):
            self.entity.equipment.unequip_from_slot(self.slot, add_message=True)
        else:
            self.entity.equipment.equip_to_slot(slot=self.slot, item=self.item, add_message=True)
        return True


class WaitAction(Action):
    def perform(self) -> bool:
        return True


class TakeStairsAction(Action):
    def perform(self) -> bool:
        """
        Take the stairs, if any exist at the entity's location.
        """
        if (self.entity.x, self.entity.y) == self.engine.game_map.downstairs_location:
            self.engine.game_world.generate_floor()
            self.engine.message_log.add_message(
                "You descend the staircase.", colors.descend
            )
            return True
        else:
            raise exceptions.Impossible("There are no stairs here.")


class ActionWithDirection(Action):
    def __init__(self, entity: Actor, dx: int, dy: int):
        super().__init__(entity)

        self.dx = dx
        self.dy = dy

    @property
    def dest_xy(self) -> Tuple[int, int]:
        """Returns this action's destination."""
        return self.entity.x + self.dx, self.entity.y + self.dy

    @property
    def blocking_entity(self) -> Optional[FighterGroup]:
        """Return the blocking entity at this action's destination."""
        return self.engine.game_map.get_blocking_entity_at_location(*self.dest_xy)

    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this action's destination."""
        return self.engine.game_map.get_actor_at_location(*self.dest_xy)

    def perform(self) -> None:
        raise NotImplementedError()


class MovementAction(ActionWithDirection):

    def perform(self) -> bool:
        dest_x, dest_y = self.dest_xy

        if not self.engine.game_map.in_bounds(dest_x, dest_y):
            # Destination is out of bounds.
            raise exceptions.Impossible("That way is blocked.")
        if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
            # Destination is blocked by a tile.
            raise exceptions.Impossible("That way is blocked.")
        if self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y):
            # Destination is blocked by an entity.
            raise exceptions.Impossible("That way is blocked.")

        self.entity.move(self.dx, self.dy)
        return True


class BumpAction(ActionWithDirection):
    def perform(self) -> bool:
        if self.target_actor:
            if isinstance(self.target_actor, Trader) and self.entity is self.engine.player:
                self.engine.active_trader = self.target_actor
                return True
            if (
                    self.target_actor is not self.engine.player and
                    self.entity is not self.engine.player
            ):
                return True
            else:
                if self.entity is self.engine.player:
                    self.engine.start_combat(self.target_actor)
                else:
                    self.engine.start_combat(self.entity)
                return True

        else:
            return MovementAction(self.entity, self.dx, self.dy).perform()


class Ability(Action):
    def __init__(
            self,
            caster: Fighter,
            cost: int = 0,
            name: str = "<Unnamed>",
            description: str = "<None>"
    ):
        super().__init__(entity=caster)
        self.name = name
        self._description = description
        self.cost = cost

    @property
    def description(self) -> str:
        result = self._description
        if self.cost != 0:
            result += f"\nCosts {self.cost} {self.entity.resource.name}."
        return result


class TargetedAbility(Ability):
    def __init__(
            self,
            caster: Fighter,
            target: Optional[Fighter],
            cost: int = 0,
            name: str = "<UnnamedTargetedAbility>",
            description: str = "<None>"
    ):
        super().__init__(caster=caster, cost=cost, name=name, description=description)
        self.target = target


class AttackAction(TargetedAbility):
    def __init__(
            self,
            caster: Fighter,
            target: Optional[Fighter],
            damage: int,
            name: str = "<AttackAction>",
            description: str = "<Standard attack>"
    ):
        super().__init__(
            caster=caster,
            target=target,
            name=name,
            description=description,
        )
        self.damage = damage

    def perform(self) -> bool:
        attack_desc = f"{self.entity.name.capitalize()} attacks {self.target.name}"

        damage = self.damage
        if damage <= self.target.block:
            self.target.block -= damage
            damage = 0

        if self.entity.parent is self.engine.player:
            attack_color = colors.player_atk
        else:
            attack_color = colors.enemy_atk
        if self.target.buffs[StatusType.EVASION] > 0:
            self.engine.message_log.add_message(
                f"{attack_desc} but misses.", attack_color
            )
            self.target.buffs[StatusType.EVASION] -= 1
        elif damage > 0:
            self.engine.message_log.add_message(
                f"{attack_desc} for {damage} hit points.", attack_color
            )
            self.target.hp -= damage
            return True
        else:
            self.engine.message_log.add_message(
                f"{attack_desc} but does no damage.", attack_color
            )
            return False


class SanguineStrike(TargetedAbility):
    def __init__(
            self,
            caster: Fighter,
            target: Optional[Fighter],
    ):
        super().__init__(
            caster=caster,
            target=target,
            cost=30,
            name="Sanguine Strike",
            description=f"Attack a single enemy, dealing {4 + caster.buffs[StatusType.STRENGTH]} damage." +
                        f" If HP damage is done, inflict 4 bleed."
        )

    def perform(self) -> bool:
        if AttackAction(
                caster=self.entity,
                target=self.target,
                damage=4 + self.entity.buffs[StatusType.STRENGTH],
        ):
            self.target.debuffs[StatusType.BLEED] += 4
            if self.entity.parent is self.engine.player:
                attack_color = colors.player_atk
            else:
                attack_color = colors.enemy_atk
            self.engine.message_log.add_message(
                text=f"{self.target.name.capitalize()} received 4 bleed!",
                fg=attack_color
            )
            return True
        return False
