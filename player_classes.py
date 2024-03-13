from enum import auto, Enum


class PlayerClass(Enum):
    WARRIOR = auto()
    ROGUE = auto()
    MAGE = auto()

if __name__ == "__main__":
    print(PlayerClass(1))