from enum import auto, Enum


class FighterClass(Enum):
    WARRIOR = auto()
    ROGUE = auto()
    MAGE = auto()

if __name__ == "__main__":
    print(FighterClass(1))