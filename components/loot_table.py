from __future__ import annotations

from typing import Optional

import copy

from dropgen.RDSTable import RDSTable
import entity_factories


class WeaponsTable(RDSTable):
    def __init__(self):
        super().__init__()


class HealingItemTable(RDSTable):
    def __init__(self, current_floor: int, count: int, probability: Optional[float] = None):
        super().__init__(count=count, probability=probability)

        self.current_floor = current_floor

        self.add_entry(entry=copy.deepcopy(entity_factories.tasty_rat), enabled=False)
        self.add_entry(entry=copy.deepcopy(entity_factories.plump_rat), enabled=False)
        self.add_entry(entry=copy.deepcopy(entity_factories.enormous_rat), enabled=False)
        self.add_entry(entry=copy.deepcopy(entity_factories.rodent_of_unusual_size), enabled=False)
