from enum import auto, Enum


class WeaponType(Enum):
    STRENGTH = auto()
    AGILITY = auto()
    FINESSE = auto()  # Uses either strength or agility, whichever is highest
    MAGIC = auto()
