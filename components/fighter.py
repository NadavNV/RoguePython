from __future__ import annotations

import copy
import random
from typing import Dict, List, Optional, Tuple, Type, TYPE_CHECKING

import colors
from components.base_component import BaseComponent
from components.equipment import Equipment
from components.inventory import Inventory
from components.level import Level
from components.resoucre import Resource, Stamina, Rage, Mana
from dropgen.RDSObject import RDSObject
from fighter_classes import FighterClass
from status_types import StatusType
from talents import Talent

if TYPE_CHECKING:
    from cards import Card
    from components.ai import BaseAI
    from engine import Engine
    from entity import FighterGroup
    from game_map import GameMap

MAX_HAND_SIZE = 10


class Fighter(BaseComponent, RDSObject):
    parent: FighterGroup
    default_hand_size: int
    current_hand_size: int

    def __init__(
            self,
            min_hp_on_spawn: int,
            max_hp_on_spawn: int,
            hp_per_level: int,
            deck: List[Card],
            inventory: Inventory = Inventory(capacity=26),
            level: Level = Level(),
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

        self.baseline_buffs: Dict[StatusType, int] = {
            StatusType.AGILITY: 0,
            StatusType.ARMOR: 0,
            StatusType.BALM: 0,
            StatusType.BARBED: 0,
            StatusType.EVASION: 0,
            StatusType.STRENGTH: 0,
            StatusType.WARD: 0,
        }
        self.baseline_debuffs: Dict[StatusType, int] = {
            StatusType.BLEED: 0,
            StatusType.BLIGHT: 0,
            StatusType.BURNING: 0,
            StatusType.EXPOSED: 0,
            StatusType.POISON: 0,
            StatusType.SHATTERED: 0,
            StatusType.WEAKNESS: 0,
        }
        self.buffs: Dict[StatusType, int] = dict(self.baseline_buffs)
        self.debuffs: Dict[StatusType, int] = dict(self.baseline_debuffs)

        self.talents: Dict[Talent, int] = {}

        self.deck: List[Card] = copy.deepcopy(deck)
        for card in self.deck:
            card.parent = self
        self.hand: List[Card] = []
        self.draw: List[Card] = []
        self.discard: List[Card] = []
        self.burn: List[Card] = []

        self.max_hp = random.randrange(min_hp_on_spawn, max_hp_on_spawn + 1, 5)
        self._hp = self.max_hp
        self.hp_per_level = hp_per_level
        self.block = 0

        self.inventory = inventory
        self.inventory.parent = self
        self.level = level
        self.level.parent = self

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
            self.engine.active_enemies.fighters.remove(self)

        self.char = "%"
        self.color = (191, 0, 0)
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

    def take_damage(self, amount: int) -> int:
        """
        Receive an attack worth 'amount' damage. Reduce hp, block, and armor as necessary
        and return the amount of hp damage done.
        """
        if amount <= self.block:
            self.block -= amount
            amount = 0
        else:
            if self.block > 0:
                amount -= self.block
                self.block = 0
        if amount > 0 and self.buffs[StatusType.ARMOR] > 0:
            self.buffs[StatusType.ARMOR] -= 1

        self.hp -= amount
        return amount

    @property
    def is_alive(self) -> bool:
        """Returns True as long as this fighter can perform actions."""
        return self._hp > 0

    @property
    def engine(self) -> Engine:
        return self.parent.engine

    @property
    def game_map(self) -> GameMap:
        return self.parent.game_map

    def draw_hand(self) -> None:
        while len(self.hand) < self.current_hand_size:
            if len(self.draw) == 0:
                self.draw = self.discard
                self.discard = []
                random.shuffle(self.draw)
            next_card = self.draw.pop()
            next_card.on_draw()
            self.hand.append(next_card)

    def start_turn(self) -> None:
        self.block = 0
        if self.debuffs[StatusType.BLEED] > 0:
            self.hp -= self.debuffs[StatusType.BLEED]
            self.debuffs[StatusType.BLEED] -= 1
        if self.debuffs[StatusType.BURNING] > 0:
            self.hp -= self.debuffs[StatusType.BURNING]
            self.debuffs[StatusType.BURNING] //= 2
        if not self.is_alive:
            self.die()
            return
        self.hp += self.buffs[StatusType.BALM]
        if Talent.STRENGTH_PER_TURN in self.talents:
            self.buffs[StatusType.STRENGTH] += self.talents[Talent.STRENGTH_PER_TURN]
        self.draw_hand()

    def start_combat(self) -> None:
        self.buffs = dict(self.baseline_buffs)
        self.debuffs = dict(self.baseline_debuffs)
        self.draw = self.deck[:]
        random.shuffle(self.draw)
        self.draw_hand()

    def end_turn(self) -> None:
        if self.debuffs[StatusType.POISON] > 0:
            self.hp -= self.debuffs[StatusType.POISON]
        if self.debuffs[StatusType.BLIGHT] > 0:
            self.hp -= self.debuffs[StatusType.BLIGHT]
            self.debuffs[StatusType.BLIGHT] += 1
        if not self.is_alive:
            self.die()
            return
        if self.debuffs[StatusType.WEAKNESS] > 0:
            self.debuffs[StatusType.WEAKNESS] -= 1
        if Talent.BLOCK_PER_TURN in self.talents:
            self.block += self.talents[Talent.BLOCK_PER_TURN]
        self.block += self.buffs[StatusType.ARMOR]
        while self.hand:
            card = self.hand.pop()
            card.on_turn_end()


class Player(Fighter):
    def __init__(
            self,
            min_hp_on_spawn: int,
            max_hp_on_spawn: int,
            hp_per_level: int,
            deck: List[Card],
            resource: Resource,
            fighter_class: FighterClass,
            inventory: Inventory = Inventory(capacity=26),
            equipment: Equipment = Equipment(),
            level: Level = Level(),
            sprite: str = "images/rogue_icon.png"
    ):
        super().__init__(
            min_hp_on_spawn=min_hp_on_spawn,
            max_hp_on_spawn=max_hp_on_spawn,
            hp_per_level=hp_per_level,
            deck=deck,
            level=level,
            char="@",
            color=colors.player_icon,
            name="Player",
            sprite=sprite,
            inventory=inventory,
        )

        self.resource = resource
        self.resource.parent = self
        self.equipment = equipment
        self.equipment.parent = self

        self.fighter_cls = fighter_class

    def end_combat(self) -> None:
        self.buffs = dict(self.baseline_buffs)
        self.debuffs = dict(self.baseline_debuffs)
        if Talent.STAMINA_PER_TURN in self.talents:
            self.resource.max_amount -= self.talents[Talent.STAMINA_PER_TURN]
        self.talents.clear()
        if isinstance(self, Rogue) or isinstance(self, Mage):
            self.resource.gain(self.resource.max_amount)
        if isinstance(self, Warrior):
            self.resource.current_amount = self.resource.max_amount // 2


class Enemy(Fighter):
    def __init__(
            self,
            target_level: int,
            min_hp_on_spawn: int,
            max_hp_on_spawn: int,
            hp_per_level: int,
            ai_cls: Type[BaseAI],
            deck: List[Card],
            level: Level = Level(),
            char: str = "?",
            color: Tuple[int, int, int] = colors.white,
            name: str = "<Unnamed>",
            sprite: str = "images/rogue_icon.png",
    ):
        super().__init__(
            min_hp_on_spawn=min_hp_on_spawn,
            max_hp_on_spawn=max_hp_on_spawn,
            hp_per_level=hp_per_level,
            level=level,
            name=name,
            color=color,
            char=char,
            sprite=sprite,
            deck=deck,
        )
        self.ai = ai_cls
        self.default_hand_size = 1
        self.current_hand_size = 1

        while self.level.current_level < target_level:
            self.level.increase_level()

        self.level.xp_given *= self.level.current_level

    def die(self) -> None:
        super().die()

    def stun(self):
        self.draw.append(self.hand.pop())


class Rogue(Player):
    def __init__(
            self,
            deck: List[Card],

    ):
        super().__init__(
            min_hp_on_spawn=80,
            max_hp_on_spawn=80,
            hp_per_level=10,
            resource=Stamina(),
            level=Level(level_up_base=50),  # 200
            deck=deck,
            fighter_class=FighterClass.ROGUE
        )
        self.default_hand_size = 5
        self.current_hand_size = 5


class Warrior(Player):
    def __init__(
            self,
            deck: List[Card],

    ):
        super().__init__(
            min_hp_on_spawn=100,
            max_hp_on_spawn=100,
            hp_per_level=10,
            resource=Rage(),
            level=Level(level_up_base=200),
            deck=deck,
            fighter_class=FighterClass.WARRIOR
        )
        self.default_hand_size = 4
        self.current_hand_size = 4


class Mage(Player):
    def __init__(
            self,
            deck: List[Card],

    ):
        super().__init__(
            min_hp_on_spawn=80,
            max_hp_on_spawn=80,
            hp_per_level=5,
            resource=Mana(),
            level=Level(level_up_base=200),
            deck=deck,
            fighter_class=FighterClass.MAGE
        )
        self.default_hand_size = 6
        self.current_hand_size = 6
