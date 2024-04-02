"""Handle the loading and initialization of game sessions."""
from __future__ import annotations

import copy
import pickle
import lzma

import colors
from components.resoucre import Mana, Rage, Stamina
from engine import Engine
from actions import MeleeAttack, SanguineStrike
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

    player = copy.deepcopy(entity_factories.player)

    if player_class == FighterClass.WARRIOR:
        player[0].fighter_class = FighterClass.WARRIOR
        player[0].strength = 7
        player[0].agility = 4

        club = copy.deepcopy(entity_factories.club)
        leather_armor = copy.deepcopy(entity_factories.leather_armor)

        player[0].equipment.equip_to_slot(EquipmentSlot.MAINHAND, club, add_message=False)
        player[0].equipment.equip_to_slot(EquipmentSlot.ARMOR, leather_armor, add_message=False)
        player[0].resource = Rage()

    elif player_class == FighterClass.ROGUE:
        player[0].fighter_class = FighterClass.ROGUE
        player[0].strength = 4
        player[0].agility = 7

        dagger = copy.deepcopy(entity_factories.dagger)
        leather_armor = copy.deepcopy(entity_factories.leather_armor)

        player[0].equipment.equip_to_slot(EquipmentSlot.MAINHAND, dagger, add_message=False)
        player[0].equipment.equip_to_slot(EquipmentSlot.ARMOR, leather_armor, add_message=False)
        player[0].resource = Stamina()
        player[0].abilities_by_level = {
            2: SanguineStrike(caster=player[0], target=None)
        }

    elif player_class == FighterClass.MAGE:
        player[0].fighter_class = FighterClass.MAGE
        player[0].magic = 7
        player[0].agility = 4

        wand = copy.deepcopy(entity_factories.wand)
        leather_armor = copy.deepcopy(entity_factories.leather_armor)

        player[0].equipment.equip_to_slot(EquipmentSlot.MAINHAND, wand, add_message=False)
        player[0].equipment.equip_to_slot(EquipmentSlot.ARMOR, leather_armor, add_message=False)
        player[0].resource = Mana()

    player[0].resource.parent = player[0]
    player[0].abilities.append(MeleeAttack(caster=player[0], target=None))
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

    engine.message_log.add_message(
        "Hello and welcome, adventurer, to yet another dungeon!", colors.welcome_text
    )

    return engine
