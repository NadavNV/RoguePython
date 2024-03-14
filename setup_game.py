"""Handle the loading and initialization of game sessions."""
from __future__ import annotations

import copy
import tcod

import color
from engine import Engine
import entity_factories
from game_map import GameWorld
from equipment_slots import EquipmentSlot
from player_classes import PlayerClass


# Load the background image and remove the alpha channel.
background_image = tcod.image.load("images/menu_background.png")[:, :, :3]

WINDOW_WIDTH = 128
WINDOW_HEIGHT = 72


def new_game(player_class: PlayerClass) -> Engine:
    """Return a brand new game session as an engine instance."""
    map_width = WINDOW_WIDTH * 2 // 3
    map_height = WINDOW_HEIGHT * 2 // 3

    room_max_size = 10
    room_min_size = 6
    max_rooms = 30

    player = copy.deepcopy(entity_factories.player)

    if player_class == PlayerClass.WARRIOR:
        print("Creating warrior")
        player.fighter.strength = 6
        player.fighter.agility = 3

        sword = copy.deepcopy(entity_factories.short_sword)
        armor = copy.deepcopy(entity_factories.chain_mail)

        sword.parent = player.equipment
        armor.parent = player.equipment

        player.equipment.equip_to_slot(EquipmentSlot.MAINHAND, sword, add_message=False)
        player.equipment.equip_to_slot(EquipmentSlot.ARMOR, armor, add_message=False)

    elif player_class == PlayerClass.ROGUE:
        print("Creating rogue")
        player.fighter.strength = 3
        player.fighter.agility = 6

        dagger = copy.deepcopy(entity_factories.dagger)
        leather_armor = copy.deepcopy(entity_factories.leather_armor)

        dagger.parent = player.equipment
        leather_armor.parent = player.equipment

        player.equipment.equip_to_slot(EquipmentSlot.MAINHAND, dagger, add_message=False)
        player.equipment.equip_to_slot(EquipmentSlot.ARMOR, leather_armor, add_message=False)

    elif player_class == PlayerClass.MAGE:
        print("Creating mage")
        player.fighter.magic = 6
        player.fighter.agility = 3

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

    return engine
