import colors
from components.ai import HostileEnemy
from components import consumable, equippable
from components.equipment import Equipment
from components.fighter import Fighter
from components.inventory import Inventory
from components.level import Level
from mapentity import Actor, Item
from fighter_classes import FighterClass

SCROLL_CHAR = '~'
POTION_CHAR = '!'
WEAPON_CHAR = '/'
ARMOR_CHAR = '['

player = Actor(
    char="@",
    color=(255, 255, 255),
    name="Player",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        fighter_class=FighterClass.ROGUE,
        strength=1,
        perseverance=1,
        agility=1,
        magic=1,
        hit_dice="2d10",
        mana=20
    ),
    inventory=Inventory(capacity=26),
    level=Level(level_up_base=200),
)

janitor = Actor(
    char="j",
    color=(63, 127, 63),
    name="Janitor",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        fighter_class=FighterClass.ROGUE, strength=1, perseverance=2, agility=4, magic=1, hit_dice="1d8",
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=35),
)
lumberjack = Actor(
    char="L",
    color=(0, 127, 0),
    name="Lumberjack",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        fighter_class=FighterClass.WARRIOR, strength=5, perseverance=3, agility=3, magic=1, hit_dice="1d10",
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=100),
)

confusion_scroll = Item(
    char=SCROLL_CHAR,
    color=(207, 63, 255),
    name="Confusion Scroll",
    consumable=consumable.ConfusionConsumable(number_of_turns=10),
    stackable=True
)

fireball_scroll = Item(
    char=SCROLL_CHAR,
    color=(255, 0, 0),
    name="Fireball Scroll",
    consumable=consumable.FireballDamageConsumable(damage=12, radius=3),
    stackable=True
)

health_potion = Item(
    char=POTION_CHAR,
    color=(127, 0, 255),
    name="Health Potion",
    consumable=consumable.HealingConsumable(amount=4),
    stackable=True
)

mana_potion = Item(
    char=POTION_CHAR,
    color=(0x0E, 0x86, 0xD4),
    name="Mana Potion",
    consumable=consumable.ManaConsumable(amount=4),
    stackable=True
)

lightning_scroll = Item(
    char=SCROLL_CHAR,
    color=(255, 255, 0),
    name="Lightning Scroll",
    consumable=consumable.LightningDamageConsumable(damage=20, maximum_range=5),
    stackable=True
)

dagger = Item(
    char=WEAPON_CHAR,
    color=(0, 191, 255),
    name="Dagger",
    equippable=equippable.Dagger(),
)

short_sword = Item(
    char=WEAPON_CHAR,
    color=(0, 191, 255),
    name="Short Sword",
    equippable=equippable.ShortSword(),
)

leather_armor = Item(
    char=ARMOR_CHAR,
    color=(139, 69, 19),
    name="Leather Armor",
    equippable=equippable.LeatherArmor(),
)

chain_mail = Item(
    char=ARMOR_CHAR,
    color=(139, 69, 19),
    name="Chain Mail",
    equippable=equippable.ChainMail(),
)
