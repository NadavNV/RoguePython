from __future__ import annotations

import copy
import random
from typing import Dict, Iterator, List, Tuple, TYPE_CHECKING, Union

import tcod

import entity_factories
from game_map import GameMap
from components.ai import RoamingEnemy
import tile_types
from mapentity import MapEntity, FighterGroup, Item
from components.fighter import Fighter

if TYPE_CHECKING:
    from engine import Engine

Entity = Union[MapEntity, Fighter]

TRADER_FLOOR = 3

max_items_by_floor = [
    (1, 1),
    (3, 2),
    (4, 3),
]

max_groups_by_floor = [
    (1, 2),
    (4, 3),
    (6, 5),
]

max_enemies_per_group_by_floor = [
    (1, 1),
    (3, 2),
    (6, 3)
]

item_chances: Dict[int, List[Tuple[MapEntity, int]]] = {
    0: [(entity_factories.tasty_rat, 30), (entity_factories.mana_potion, 12)],
    2: [(entity_factories.confusion_scroll, 12), (entity_factories.dagger, 3)],
    4: [(entity_factories.lightning_scroll, 25), (entity_factories.short_sword, 5)],
    6: [(entity_factories.fireball_scroll, 25), (entity_factories.chain_mail, 15)],
}

enemy_chances: Dict[int, List[Tuple[Fighter, int]]] = {
    0: [(entity_factories.janitor, 80)],
    3: [(entity_factories.lumberjack, 15)],
    5: [(entity_factories.lumberjack, 30)],
    7: [(entity_factories.lumberjack, 60)],
}


def get_max_value_for_floor(
        max_value_by_floor: List[Tuple[int, int]], floor: int
) -> int:
    current_value = 0

    for floor_minimum, value in max_value_by_floor:
        if floor_minimum > floor:
            break
        else:
            current_value = value

    return current_value


def generate_fighter_groups(
        number_of_groups: int,
        floor: int,
) -> List[FighterGroup]:
    groups = []
    for i in range(number_of_groups):
        # TODO: This needs(?) to be redesigned to work without entity_factories
        number_of_monsters = random.randint(1, get_max_value_for_floor(max_enemies_per_group_by_floor, floor))
        templates = get_entities_at_random(enemy_chances, number_of_entities=number_of_monsters, floor=floor)
        fighters = []
        gold = 0
        for template in templates:
            fighter = copy.deepcopy(template)
            fighter.roll_hitpoints()
            fighter.inventory.add_item(copy.deepcopy(entity_factories.tasty_rat))
            for ability in fighter.abilities:
                ability.entity = fighter
            fighters.append(fighter)
            gold += fighter.inventory.gold
        group = FighterGroup(fighters=fighters, ai_cls=RoamingEnemy, gold=gold)
        for fighter in group:
            fighter.parent = group
        groups.append(group)
    return groups


def get_entities_at_random(
        weighted_chances_by_floor: Dict[int, List[Tuple[Entity, int]]],
        number_of_entities: int,
        floor: int,
) -> List[Entity]:
    entity_weighted_chances = {}

    for key, values in weighted_chances_by_floor.items():
        if key > floor:
            break
        else:
            for value in values:
                entity = value[0]
                weighted_chance = value[1]

                entity_weighted_chances[entity] = weighted_chance

    entities = list(entity_weighted_chances.keys())
    entity_weighted_chance_values = list(entity_weighted_chances.values())

    chosen_entities = random.choices(
        entities, weights=entity_weighted_chance_values, k=number_of_entities
    )

    return chosen_entities


class RectangularRoom:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def center(self) -> Tuple[int, int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)

        return center_x, center_y

    @property
    def inner(self) -> Tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    def intersects(self, other: RectangularRoom) -> bool:
        """Return True if this room overlaps with another RectangularRoom."""
        return (
                self.x1 <= other.x2
                and self.x2 >= other.x1
                and self.y1 <= other.y2
                and self.y2 >= other.y1
        )


def tunnel_between(
        start: Tuple[int, int], end: Tuple[int, int]
) -> Iterator[Tuple[int, int]]:
    """Return an L-shaped tunnel between these two points."""
    x1, y1 = start
    x2, y2 = end
    if random.random() < 0.5:  # 50% chance.
        # Move horizontally, then vertically.
        corner_x, corner_y = x2, y1
    else:
        # Move vertically, then horizontally.
        corner_x, corner_y = x1, y2

    # Generate the coordinates for this tunnel.
    for x, y in tcod.los.bresenham((x1, y1), (corner_x, corner_y)).tolist():
        yield x, y
    for x, y in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        yield x, y


def generate_dungeon(
        max_rooms: int,
        room_min_size: int,
        room_max_size: int,
        map_width: int,
        map_height: int,
        engine: Engine,
) -> GameMap:
    """Generate a new dungeon map."""
    player = engine.player
    dungeon = GameMap(engine, map_width, map_height, entities=[player])

    rooms: List[RectangularRoom] = []

    center_of_last_room = (0, 0)

    for r in range(max_rooms):
        room_width = random.randint(room_min_size, room_max_size)
        room_height = random.randint(room_min_size, room_max_size)

        x = random.randint(0, dungeon.width - room_width - 1)
        y = random.randint(0, dungeon.height - room_height - 1)

        # "RectangularRoom" class makes rectangles easier to work with
        new_room = RectangularRoom(x, y, room_width, room_height)

        # Run through the other rooms and see if they intersect with this one.
        if any(new_room.intersects(other_room) for other_room in rooms):
            continue  # This room intersects, so go to the next attempt.
        # If there are no intersections then the room is valid.

        # Dig out this room's inner area.
        dungeon.tiles[new_room.inner] = tile_types.floor

        if len(rooms) == 0:
            # The first room, where the player starts.
            player.place(*new_room.center, game_map=dungeon)
        else:  # All rooms after the first.
            # Dig out a tunnel between this room and the previous one.
            for x, y in tunnel_between(rooms[-1].center, new_room.center):
                dungeon.tiles[x, y] = tile_types.floor
            if (
                    engine.game_world.current_floor % TRADER_FLOOR == 0 and
                    len(rooms) == max_rooms // 2
            ):
                # TODO: Place a vendor in the center of the room
                pass

            center_of_last_room = new_room.center

        place_entities(new_room, dungeon, engine.game_world.current_floor)

        dungeon.tiles[center_of_last_room] = tile_types.down_stairs
        dungeon.downstairs_location = center_of_last_room

        # Finally, append the new room to the list.
        rooms.append(new_room)

    return dungeon


def place_entities(room: RectangularRoom, dungeon: GameMap, floor_number: int) -> None:
    number_of_groups = random.randint(
        0, get_max_value_for_floor(max_groups_by_floor, floor_number)
    )
    number_of_items = random.randint(
        0, get_max_value_for_floor(max_items_by_floor, floor_number)
    )

    monsters: List[MapEntity] = generate_fighter_groups(
        number_of_groups, floor_number
    )
    items: List[MapEntity] = get_entities_at_random(
        item_chances, number_of_items, floor_number
    )

    for entity in monsters + items:
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)

        if not any(i.x == x and i.y == y for i in dungeon.entities):
            entity.spawn(dungeon, x, y)


def generate_items(current_floor: int, number_of_items: int) -> Dict[Item, int]:
    # TODO: Generate a random set of items based on current floor
    return {
        entity_factories.tasty_rat: 20,
        entity_factories.mana_potion: 20,
    }
