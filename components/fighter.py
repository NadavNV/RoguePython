from __future__ import annotations

import copy
from typing import Dict, List, Optional, Tuple, Type, TYPE_CHECKING

import colors
from components.base_component import BaseComponent
from components.equipment import Equipment
from components.inventory import Inventory
from components.level import Level
from components.resoucre import Resource, Stamina
from dropgen.RDSObject import RDSObject
from dropgen.RDSValue import RDSValue
from dropgen.RDSTable import RDSTable
from entity import Item
from fighter_classes import FighterClass
from status_types import StatusTypes

if TYPE_CHECKING:
    from actions import Ability
    from cards import Card
    from components.ai import BaseAI
    from components.status_effects import StatusEffect
    from engine import Engine
    from entity import FighterGroup
    from game_map import GameMap

BASE_DEFENSE = 10


class Fighter(BaseComponent, RDSObject):
    parent: FighterGroup
    status_effects: List[StatusEffect]

    def __init__(
            self,
            min_hp_per_level: int,
            max_hp_per_level: int,
            fighter_class: FighterClass,
            ai_cls: Type[BaseAI],
            resource: Resource = Stamina(),
            inventory: Inventory = Inventory(capacity=26),
            equipment: Equipment = Equipment(),
            level: Level = Level(),
            abilities_by_level: Optional[Dict[int, Ability]] = None,
            abilities: Optional[List[Ability]] = None,
            char: str = "?",
            color: Tuple[int, int, int] = colors.white,
            name: str = "<Unnamed>",
            sprite: str = "images/rogue_icon.png"
    ):
        super().__init__()
        self.char = char
        self.name = name
        self.color = color
        self.sprite = colors.image_to_rgb(sprite)

        self.fighter_class = fighter_class

        self.buffs: Dict[StatusTypes, int] = {
            StatusTypes.AGILITY: 0,
            StatusTypes.ARMOR: 0,
            StatusTypes.BALM: 0,
            StatusTypes.BARBED: 0,
            StatusTypes.EVASION: 0,
            StatusTypes.STRENGTH: 0,
            StatusTypes.WARD: 0,
        }
        self.debuffs: Dict[StatusTypes, int] = {
            StatusTypes.BLEED: 0,
            StatusTypes.BLIGHT: 0,
            StatusTypes.BURN: 0,
            StatusTypes.EXPOSED: 0,
            StatusTypes.POISON: 0,
            StatusTypes.SHATTERED: 0,
        }

        self.deck: List[Card] = []
        self.hand: List[Card] = []
        self.draw: List[Card] = []
        self.discard: List[Card] = []
        self.burn: List[Card] = []

        self.max_hp_per_level = max_hp_per_level
        self.min_hp_per_level = min_hp_per_level
        self._hp = 0
        self.max_hp = 0
        self.block = 0

        self.resource = resource
        self.resource.parent = self
        self.equipment = equipment
        self.equipment.parent = self
        self.inventory = inventory
        self.inventory.parent = self
        self.level = level
        self.level.parent = self
        self.abilities_by_level = {} if abilities_by_level is None else copy.deepcopy(abilities_by_level)
        self.abilities = [] if abilities is None else copy.deepcopy(abilities)
        self.ai = ai_cls(self)

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        self._hp = max(0, min(value, self.max_hp))
        if self._hp == 0 and self.parent.ai:
            self.die()

    def die(self) -> None:
        if self.engine.player is self.parent:
            death_message = "You died!"
            death_message_color = colors.player_die
        else:
            death_message = f"{self.name} is dead!"
            death_message_color = colors.enemy_die

        self.char = "%"
        self.color = (191, 0, 0)
        self.ai = None
        self.name = f"Dead {self.parent.name}"

        self.engine.message_log.add_message(death_message, death_message_color)

        self.engine.player[0].level.add_xp(self.level.xp_given)

    def heal(self, amount: int) -> int:
        if self.hp == self.max_hp:
            return 0

        new_hp_value = self.hp + amount

        if new_hp_value > self.max_hp:
            new_hp_value = self.max_hp

        amount_recovered = new_hp_value - self.hp

        self.hp = new_hp_value

        return amount_recovered

    def take_damage(self, amount: int) -> None:
        self.hp -= amount

    @property
    def is_alive(self) -> bool:
        """Returns True as long as this fighter can perform actions."""
        return bool(self.ai)

    @property
    def engine(self) -> Engine:
        return self.parent.engine

    @property
    def game_map(self) -> GameMap:
        return self.parent.game_map


class Enemy(Fighter):
    def __init__(
            self,
            target_level: int,
            loot_table: RDSTable,
            stat_prio: RDSTable,
            min_hp_per_level: int,
            max_hp_per_level: int,
            fighter_class: FighterClass,
            ai_cls,
            resource: Resource = Stamina(),
            inventory: Inventory = Inventory(capacity=26),
            equipment: Equipment = Equipment(),
            level: Level = Level(),
            abilities: List[Ability] = None,
            char: str = "?",
            color: Tuple[int, int, int] = colors.white,
            name: str = "<Unnamed>",
            sprite: str = "images/rogue_icon.png",
    ):
        super().__init__(
            min_hp_per_level=min_hp_per_level,
            max_hp_per_level=max_hp_per_level,
            fighter_class=fighter_class,
            ai_cls=ai_cls,
            resource=resource,
            inventory=inventory,
            equipment=equipment,
            level=level,
            abilities=abilities,
            name=name,
            color=color,
            char=char,
            sprite=sprite
        )

        self.loot_table = loot_table

        while self.level.current_level < target_level:
            self.level.increase_level()

        self.level.xp_given *= self.level.current_level

    def die(self) -> None:
        super().die()

        loot = self.loot_table.rds_result

        for item in loot:
            if isinstance(item, RDSValue):
                print(f"Dropped {item.rds_value} gold")
                self.inventory.gold += item.rds_value
            elif isinstance(item, Item):
                print(f"Dropped {item.name}")
                self.inventory.add_item(item)

    def stun(self, turns_remaining: int) -> None:
        pass
