"""Handle the loading and initialization of game sessions."""
from __future__ import annotations

import copy
from typing import Optional

import tcod
from tcod import libtcodpy

import color
from engine import Engine
import entity_factories
from game_map import GameWorld
import input_handlers
from equipment_slots import EquipmentSlot


# Load the background image and remove the alpha channel.
background_image = tcod.image.load("menu_background.png")[:, :, :3]

WINDOW_WIDTH = 128
WINDOW_HEIGHT = 80


def new_game(player_class: int) -> Engine:
    """Return a brand new game session as an engine instance."""
    map_width = WINDOW_WIDTH * 2 // 3
    map_height = WINDOW_HEIGHT * 2 // 3

    room_max_size = 10
    room_min_size = 6
    max_rooms = 30

    player = copy.deepcopy(entity_factories.player)

    engine = Engine(player=player)

    engine.game_world = GameWorld(
        engine=engine,
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        map_width=map_width,
        map_height=map_height,
    )

    engine.game_world.generate_floor()
    engine.update_fov()

    engine.message_log.add_message(
        "Hello and welcome, adventurer, to yet another dungeon!", color.welcome_text
    )

    dagger = copy.deepcopy(entity_factories.dagger)
    leather_armor = copy.deepcopy(entity_factories.leather_armor)

    dagger.parent = player.equipment
    leather_armor.parent = player.equipment

    player.equipment.equip_to_slot(EquipmentSlot.MAINHAND, dagger, add_message=False)
    player.equipment.equip_to_slot(EquipmentSlot.ARMOR, leather_armor, add_message=False)

    return engine
