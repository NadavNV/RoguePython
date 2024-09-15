from enum import auto, Enum


class EquipmentType(Enum):
    WEAPON = auto()
    ARMOR = auto()
    HEAD = auto()
    TRINKET = auto()
    OFFHAND = auto()  # Things like shields or magical focuses
    POTION = auto()
