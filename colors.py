import numpy as np
from PIL import Image
from status_types import StatusTypes
from typing import Tuple

white = (0xFF, 0xFF, 0xFF)
black = (0x0, 0x0, 0x0)
red = (0xFF, 0x0, 0x0)
yellow = (0xFF, 0xFF, 0x0)

player_atk = (0xE0, 0xE0, 0xE0)
enemy_atk = (0xFF, 0xC0, 0xC0)
needs_target = (0x3F, 0xFF, 0xFF)
status_effect_applied = (0x3F, 0xFF, 0x3F)
descend = (0x9F, 0x3F, 0xFF)

player_die = (0xFF, 0x30, 0x30)
enemy_die = (0xFF, 0xA0, 0x30)

invalid = (0xFF, 0xFF, 0x00)
impossible = (0x80, 0x80, 0x80)
error = (0xFF, 0x40, 0x40)

welcome_text = (0x20, 0xA0, 0xFF)
health_recovered = (0x0, 0xFF, 0x0)

player_icon = (0x3F, 0x7F, 0x3F)
janitor_icon = (0x6F, 0x8F, 0xAF)
lumberjack_icon = (0xC7, 0x0, 0x39)
trader_icon = (0xFF, 0xFF, 0xFF)
healing_potion = (127, 0, 255)
weapon = (0, 191, 255)

bar_text = white

bar_empty = (0x40, 0x10, 0x10)
bar_hp_filled = (0x0, 0x60, 0x0)
bar_rage_filled = (0xA0, 0x0, 0x0)
bar_stamina_filled = (0xF2, 0x8C, 0x28)
bar_mana_filled = (0x30, 0x30, 0x60)

buff = (0x93, 0xC4, 0x7D)
debuff = (0xE0, 0x66, 0x66)

agility = (0x33, 0xE6, 0xFF)
armor = (0xA0, 0x40, 0x0)
balm = (0xA9, 0xFF, 0x33)
barbed = (0xFF, 0x0, 0x0)
bleed = (0xB2, 0x0, 0x0)
blight = (0xBD, 0x1B, 0xFF)
burn = (0xFF, 0xBC, 0x1B)
evasion = (0x37, 0xFF, 0x33)
exposed = (0x37, 0xFF, 0x33)
poison = (0xCA, 0xFF, 0x33)
shattered = (0xA0, 0x40, 0x0)
strength = (0xFF, 0xBC, 0x1B)
ward = (0xBD, 0x1B, 0xFF)

def status_to_color(status: StatusTypes) -> Tuple[int, int, int]:
    match status:
        case StatusTypes.AGILITY:
            return agility
        case StatusTypes.ARMOR:
            return armor
        case StatusTypes.BALM:
            return balm
        case StatusTypes.BARBED:
            return barbed
        case StatusTypes.BLEED:
            return bleed
        case StatusTypes.BLIGHT:
            return blight
        case StatusTypes.BURN:
            return burn
        case StatusTypes.EVASION:
            return evasion
        case StatusTypes.EXPOSED:
            return exposed
        case StatusTypes.POISON:
            return poison
        case StatusTypes.SHATTERED:
            return shattered
        case StatusTypes.STRENGTH:
            return strength
        case StatusTypes.WARD:
            return ward

def image_to_rgb(filename: str) -> np.ndarray:
    with Image.open(filename) as im:
        data = list(im.convert('RGB').getdata())
        result = []
        for y in range(im.height):
            row = []
            for x in range(im.width):
                row.append(data[x + y * im.width])
            result.append(list(row))
        return np.array(result)
