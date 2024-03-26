from __future__ import annotations

from dropgen.RDSTable import RDSTable
import entity_factories


class WeaponsTable(RDSTable):
    def __init__(self):
        super().__init__()
        pass


class HealingItemTable(RDSTable):
    def __init__(self, current_floor: int, count: int,):
        super().__init__(count=count)
        # TODO: Finish