from enum import auto, Enum


class Talent(Enum):
    STRENGTH_PER_TURN = auto()
    ATTACKS_INFLICT_BLEED = auto()
    BLOCK_PER_TURN = auto()
    STAMINA_PER_TURN = auto()
    DRAW_EXTRA_FREE_CARD = auto()