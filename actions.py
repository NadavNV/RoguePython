from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING, Union

import sys

import colors
import exceptions
from equipment_slots import EquipmentSlot
from equipment_types import EquipmentType
from mapentity import FighterGroup
from components.fighter import Fighter

if TYPE_CHECKING:
    from engine import Engine
    from mapentity import Item

Actor = Union[Fighter, FighterGroup]


class Action:
    def __init__(self, entity: Actor) -> None:
        super().__init__()
        self.entity = entity

    @property
    def engine(self) -> Engine:
        """Return the engine this action belongs to."""
        return self.entity.engine

    def perform(self) -> None:
        """Perform this action with the objects needed to determine its scope.

        `self.engine` is the scope this action is being performed in.

        `self.entity` is the object performing the action.

        This method must be overridden by Action subclasses.
        """
        raise NotImplementedError()


class PickupAction(Action):
    """Pick up an item and add it to the inventory, if there is room for it."""

    def __init__(self, entity: Actor):
        super().__init__(entity)

    def perform(self) -> None:
        actor_location_x, actor_location_y = self.entity.x, self.entity.y
        inventory = self.entity.inventory

        for item in self.engine.game_map.items:
            if actor_location_y == item.y and actor_location_x == item.x:
                if len(inventory.items) >= inventory.capacity:
                    raise exceptions.Impossible("Your inventory is full.")

                self.engine.game_map.entities.remove(item)
                item.parent = inventory
                inventory.add_item(item)

                self.engine.message_log.add_message(f"You picked up the {item.name}!")
                return

        raise exceptions.Impossible("There is nothing here to pick up.")


class ItemAction(Action):
    def __init__(
            self, entity: Actor, item: Item, target_xy: Optional[Tuple[int, int]] = None
    ):
        super().__init__(entity)
        self.item = item
        if not target_xy:
            target_xy = entity.x, entity.y
        self.target_xy = target_xy

    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this action's destination."""
        return self.engine.game_map.get_actor_at_location(*self.target_xy)

    def perform(self) -> None:
        """Invoke the item's ability, this action will be given to provide context."""
        if self.item.consumable:
            self.item.consumable.activate(self)


class DropItem(ItemAction):
    def perform(self) -> None:
        self.entity.inventory.drop(self.item)


class EquipAction(Action):
    def __init__(self, entity: Actor, item: Item, slot: EquipmentSlot):
        super().__init__(entity)

        self.item = item
        self.slot = slot

    def perform(self) -> None:
        if self.entity.equipment.item_is_equipped(self.slot):
            self.entity.equipment.unequip_from_slot(self.slot, add_message=True)
        else:
            self.entity.equipment.equip_to_slot(slot=self.slot, item=self.item, add_message=True)


class WaitAction(Action):
    def perform(self) -> None:
        pass


class TakeStairsAction(Action):
    def perform(self) -> None:
        """
        Take the stairs, if any exist at the entity's location.
        """
        if (self.entity.x, self.entity.y) == self.engine.game_map.downstairs_location:
            self.engine.game_world.generate_floor()
            self.engine.message_log.add_message(
                "You descend the staircase.", colors.descend
            )
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

    def perform(self) -> None:
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


class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        if self.target_actor:
            self.engine.in_combat = True
            if (
                    self.target_actor is not self.engine.player and
                    self.entity is not self.engine.player
            ):
                return
            else:
                self.engine.in_combat = True
                if self.entity is self.engine.player:
                    self.engine.active_enemies = self.target_actor
                else:
                    self.engine.active_enemies = self.entity
                return

        else:
            return MovementAction(self.entity, self.dx, self.dy).perform()


class Ability(Action):
    def __init__(self, caster: Fighter, cooldown: int = 0, name: str = "<Unnamed>", description: str = "<None>"):
        super().__init__(entity=caster)
        self.name = name
        self.description = description
        self.cooldown = cooldown
        self.cooldown_remaining = 0

    def reduce_cooldown(self) -> None:
        self.cooldown_remaining = max(0, self.cooldown_remaining - 1)

    def start_cooldown(self) -> None:
        self.cooldown_remaining = self.cooldown

    def is_on_cooldown(self) -> bool:
        return self.cooldown_remaining > 0


class TargetedAbility(Ability):
    def __init__(
            self,
            caster: Fighter,
            target: Optional[Fighter],
            cooldown: int = 0,
            name: str = "<UnnamedTargetedAbility>",
            description: str = "<None>"
    ):
        super().__init__(caster=caster, cooldown=cooldown, name=name, description=description)
        self.target = target


class WeaponAttack(TargetedAbility):
    def __init__(
            self,
            caster: Fighter,
            target: Fighter,
            slot: EquipmentSlot,
            cooldown: int = 0,
            with_advantage: bool = False,
            name: str = "<WeaponAttack>",
            description: str = "<Single weapon attack>"
    ):
        super().__init__(
            caster=caster,
            cooldown=cooldown,
            target=target,
            name=name,
            description=description,
        )
        self.with_advantage = with_advantage
        self.slot = slot

    def perform(self) -> None:
        attack_desc = f"{self.entity.name.capitalize()} attacks {self.target.name}"

        if (
                self.slot == EquipmentSlot.OFFHAND and
                (
                    not self.entity.equipment.item_is_equipped(self.slot) or
                    self.entity.equipment.items[self.slot].equipment_type != EquipmentType.WEAPON
                )
        ):
            # Don't attack with shield or magical focus, or empty slot
            return
        attack = self.entity.roll_weapon_attack(slot=self.slot, advantage=self.with_advantage)
        if attack == sys.maxsize:  # Critical hit
            attack_desc = f"{attack_desc} and critically hits"
            damage = self.entity.roll_weapon_damage(self.slot)
        else:
            damage = 0
        attack -= self.target.avoidance
        damage += self.entity.roll_weapon_damage(self.slot) - self.target.armor

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

    def __init__(
            self,
            caster: Fighter,
            target: Optional[Fighter],
    ):
        super().__init__(
            caster=caster,
            target=target,
            name="Weapon Attack",
            description="Attack a single enemy with your equipped weapons."
        )

    def perform(self) -> None:
        WeaponAttack(caster=self.entity, target=self.target, slot=EquipmentSlot.MAINHAND).perform()
        WeaponAttack(caster=self.entity, target=self.target, slot=EquipmentSlot.OFFHAND).perform()
