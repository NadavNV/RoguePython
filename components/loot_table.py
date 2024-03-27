from __future__ import annotations

import copy

from dropgen.RDSTable import RDSTable
import entity_factories


class WeaponsTable(RDSTable):
    def __init__(self):
        super().__init__()


class HealingItemTable(RDSTable):
    def __init__(self, current_floor: int, count: int,):
        super().__init__(count=count)

        self.current_floor = current_floor

        self.add_entry(entry=copy.deepcopy(entity_factories.tasty_rat), probability=50, enabled=False)
        self.add_entry(entry=copy.deepcopy(entity_factories.plump_rat), probability=40, enabled=False)
        self.add_entry(entry=copy.deepcopy(entity_factories.enormous_rat), probability=20, enabled=False)
        self.add_entry(entry=copy.deepcopy(entity_factories.rodent_of_unusual_size), probability=10, enabled=False)
