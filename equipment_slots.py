from enum import auto, Enum


class EquipmentSlot(Enum):
    HEAD = auto()
    ARMOR = auto()
    MAINHAND = auto()
    OFFHAND = auto()
    TRINKET = auto()
    POTION_1 = auto()
    POTION_2 = auto()
    POTION_3 = auto()
    POTION_4 = auto()

    def __lt__(self, other):
        if not isinstance(other, EquipmentSlot):
            raise NotImplemented
        else:
            return self.value < other.value
