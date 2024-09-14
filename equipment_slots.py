from enum import auto, Enum


class EquipmentSlot(Enum):
    HEAD = auto()
    ARMOR = auto()
    MAINHAND = auto()
    OFFHAND = auto()
    TRINKET = auto()
    CONSUMABLE_1 = auto()
    CONSUMABLE_2 = auto()
    CONSUMABLE_3 = auto()
    CONSUMABLE_4 = auto()

    def __lt__(self, other):
        if not isinstance(other, EquipmentSlot):
            raise NotImplemented
        else:
            return self.value < other.value
