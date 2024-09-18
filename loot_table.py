from __future__ import annotations

from typing import Optional

import copy
import random

from dropgen.RDSTable import RDSTable
from dropgen.RDSValue import RDSValue
import entity_factories
from cards import (
    SanguineStrike, Muster, PrecisionStrike, SmokeBomb, FlashBomb, ShrapnelBomb, SideEffects, SnakeBite,
    DanseMacabre, Flourish, CardTrick
)


class WeaponsTable(RDSTable):
    def __init__(self, current_floor: int, count: int, probability: Optional[float] = None):
        super().__init__(count=count, probability=probability)

        self.current_floor = current_floor

        self.add_entry(entry=copy.deepcopy(entity_factories.dagger), unique=True)
        self.add_entry(entry=copy.deepcopy(entity_factories.broom), unique=True)
        self.add_entry(entry=copy.deepcopy(entity_factories.club), unique=True)
        self.add_entry(entry=copy.deepcopy(entity_factories.handaxe), unique=True)
        self.add_entry(entry=copy.deepcopy(entity_factories.greatsword), unique=True)
        self.add_entry(entry=copy.deepcopy(entity_factories.wand), unique=True)
        self.add_entry(entry=copy.deepcopy(entity_factories.staff), unique=True)
        self.add_entry(entry=copy.deepcopy(entity_factories.short_sword), unique=True)


class HealingItemTable(RDSTable):
    def __init__(self, current_floor: int, count: int, probability: Optional[float] = None):
        super().__init__(count=count, probability=probability)

        self.current_floor = current_floor

        self.add_entry(entry=copy.deepcopy(entity_factories.tasty_rat), enabled=False)
        self.add_entry(entry=copy.deepcopy(entity_factories.plump_rat), enabled=False)
        self.add_entry(entry=copy.deepcopy(entity_factories.enormous_rat), enabled=False)
        self.add_entry(entry=copy.deepcopy(entity_factories.rodent_of_unusual_size), enabled=False)


class RogueCommonCards(RDSTable):
    def __init__(self):
        super().__init__(count=3, unique=True)

        self.add_entry(entry=SanguineStrike(), unique=True)
        self.add_entry(entry=SnakeBite(), unique=True)
        self.add_entry(entry=PrecisionStrike(), unique=True)
        self.add_entry(entry=SideEffects(), unique=True)
        self.add_entry(entry=Muster(), unique=True)
        self.add_entry(entry=FlashBomb(), unique=True)
        self.add_entry(entry=SmokeBomb(), unique=True)
        self.add_entry(entry=ShrapnelBomb(), unique=True)
        self.add_entry(entry=DanseMacabre(), unique=True)
        self.add_entry(entry=Flourish(), unique=True)
        self.add_entry(entry=CardTrick(), unique=True)


class Gold(RDSValue):
    def __init__(self, level: int, min_value: int, max_value: int, probability: float):
        level = max(1, level)
        value = random.randint(level * min_value, level * max_value)

        super().__init__(
            probability=probability,
            value=value,
            unique=True,
        )

