"""Handle the loading and initialization of game sessions."""
from __future__ import annotations

import copy
import pickle
import lzma

import exceptions
from cards import AttackCard
import colors
from components.resoucre import Mana, Rage, Stamina
from engine import Engine
from actions import AttackAction, SanguineStrike
import entity_factories
from game_map import GameWorld
from equipment_slots import EquipmentSlot
from fighter_classes import FighterClass

WINDOW_WIDTH = 128
WINDOW_HEIGHT = 72


def load_game(filename: str) -> Engine:
    """Load an engine instance from a file."""
    with open(filename, "rb") as f:
        engine = pickle.loads(lzma.decompress(f.read()))
    assert isinstance(engine, Engine)
    return engine


def new_game(player_class: FighterClass) -> Engine:
    """Return a brand new game session as an engine instance."""
    map_width = WINDOW_WIDTH * 2 // 3
    map_height = WINDOW_HEIGHT * 2 // 3

    room_max_size = 10
    room_min_size = 6
    max_rooms = 30

    if player_class == FighterClass.WARRIOR:
        player = entity_factories.warrior
        # player[0].equipment.parent = player[0]
        # player[0].inventory.parent = player[0]

        club = copy.deepcopy(entity_factories.club)
        leather_armor = copy.deepcopy(entity_factories.leather_armor)

        player[0].equipment.equip_to_slot(EquipmentSlot.MAINHAND, club, add_message=False)
        player[0].equipment.equip_to_slot(EquipmentSlot.ARMOR, leather_armor, add_message=False)

    elif player_class == FighterClass.ROGUE:
        player = entity_factories.rogue
        # player[0].equipment.parent = player[0]
        # player[0].inventory.parent = player[0]

        dagger = copy.deepcopy(entity_factories.dagger)
        leather_armor = copy.deepcopy(entity_factories.leather_armor)

        player[0].equipment.equip_to_slot(EquipmentSlot.MAINHAND, dagger, add_message=False)
        player[0].equipment.equip_to_slot(EquipmentSlot.ARMOR, leather_armor, add_message=False)

    elif player_class == FighterClass.MAGE:
        player = entity_factories.mage
        # player[0].equipment.parent = player[0]
        # player[0].inventory.parent = player[0]

        wand = copy.deepcopy(entity_factories.wand)
        leather_armor = copy.deepcopy(entity_factories.leather_armor)

        player[0].equipment.equip_to_slot(EquipmentSlot.MAINHAND, wand, add_message=False)
        player[0].equipment.equip_to_slot(EquipmentSlot.ARMOR, leather_armor, add_message=False)
        player[0].resource = Mana()
    else:
        raise exceptions.Impossible("Invalid class selected")

    player[0].resource.parent = player[0]
    player[0].parent = player

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
    print(engine.player.parent)

    engine.message_log.add_message(
        "Hello and welcome, adventurer, to yet another dungeon!", colors.welcome_text
    )

    return engine
