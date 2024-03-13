from enum import auto, Enum


class EquipmentSlot(Enum):
    HEAD = auto()
    ARMOR = auto()
    MAINHAND = auto()
    OFFHAND = auto()
    TRINKET1 = auto()
    TRINKET2 = auto()

    def __lt__(self, other):
        if not hasattr(other, 'value'):
            return NotImplemented
        else:
            return self.value < other.value
