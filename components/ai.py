from __future__ import annotations

import random
from typing import List, Optional, Tuple, TYPE_CHECKING

import numpy as np  # type: ignore
import tcod

from components.consumable import HealingConsumable
from actions import Action, BumpAction, MovementAction, WaitAction, TargetedAbility, MeleeAttack, ItemAction

if TYPE_CHECKING:
    from entity import FighterGroup
    from components.fighter import Fighter


class BaseAI(Action):

    def perform(self) -> None:
        raise NotImplementedError()

    def get_path_to(self, dest_x: int, dest_y: int) -> List[Tuple[int, int]]:
        """Compute and return a path to the target position.

        If there is no valid path then returns an empty list.
        """
        # Copy the walkable array.
        cost = np.array(self.entity.parent.tiles["walkable"], dtype=np.int8)

        for entity in self.entity.parent.entities:
            # Check that an entity blocks movement and the cost isn't zero (blocking).
            if entity.blocks_movement and cost[entity.x, entity.y]:
                # Add to the cost of a blocked position.
                # A lower number means more enemies will crowd behind each other in
                # hallways. A higher number means enemies will take longer paths in
                # order to surround the player.
                cost[entity.x, entity.y] += 10

        # Create a graph from the cost array and pass that graph to a new pathfinder.
        graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        pathfinder = tcod.path.Pathfinder(graph)

        pathfinder.add_root((self.entity.x, self.entity.y))  # Start position

        # Compute the path to the destination and remove the starting point.
        path: List[List[int]] = pathfinder.path_to((dest_x, dest_y))[1:].tolist()

        # Convert from List[List[int]] to List[Tuple[int, int]].
        return [(index[0], index[1]) for index in path]


class ConfusedEnemy(BaseAI):
    """
    A confused enemy will stumble around aimlessly for a given number of turns, then revert back to its previous AI.
    If an actor occupies a tile it is randomly moving into, it will attack.
    """

    def __init__(
            self, entity: Fighter, previous_ai: Optional[BaseAI], turns_remaining: int,
    ):
        super().__init__(entity)

        self.previous_ai = previous_ai
        self.turns_remaining = turns_remaining

    def perform(self) -> None:
        # Revert the AI back to the original state if the effect has run its course.
        if self.turns_remaining <= 0:
            self.engine.message_log.add_message(
                f"The {self.entity.name} is no longer confused."
            )
            self.entity.ai = self.previous_ai
        else:
            if random.random() < 0.5:
                self.engine.message_log.add_message(
                    f"The {self.entity.name} shuffles around aimlessly."
                )
            else:
                target = random.choice(list(filter(
                    lambda x: x.is_alive(),
                    self.engine.active_enemies.fighters + self.engine.player.fighters
                )))
                self.engine.message_log.add_message(
                    f"The confused {self.entity.name} strikes the {target.name}!"
                )
                MeleeAttack(caster=self.entity, target=target).perform()


class RoamingEnemy(BaseAI):
    def __init__(self, entity: FighterGroup):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []

    def perform(self) -> None:
        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))  # Chebyshev distance

        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            if distance <= 1:
                return BumpAction(self.entity, dx, dy).perform()

            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()

        return WaitAction(self.entity).perform()


class HostileEnemy(BaseAI):
    def __init__(self, entity: Fighter):
        super().__init__(entity)

    def perform(self) -> None:

        if self.entity.hp < self.entity.max_hp // 2:
            for stack in self.entity.inventory.items:
                item = stack[0]
                if item.consumable is not None and isinstance(item.consumable, HealingConsumable):
                    return item.consumable.activate(ItemAction(entity=self.entity, item=item))
        for ability in self.entity.abilities:
            if not ability.is_on_cooldown():
                if isinstance(ability, TargetedAbility):
                    ability.target = self.entity.engine.player[0]
                ability.start_cooldown()
                return ability.perform()
