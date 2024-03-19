import colors
from components.ai import RoamingEnemy, HostileEnemy
from components import consumable, equippable
from components.equipment import Equipment
from components.fighter import Fighter
from components.inventory import Inventory
from components.level import Level
from mapentity import FighterGroup, Item
from fighter_classes import FighterClass
from actions import MeleeAttack

SCROLL_CHAR = '~'
POTION_CHAR = '!'
WEAPON_CHAR = '/'
ARMOR_CHAR = '['

player = FighterGroup(
    x=0,
    y=0,
    fighters=[Fighter(
        strength=1,
        perseverance=1,
        agility=1,
        magic=1,
        min_hp_per_level=5,
        max_hp_per_level=15,
        fighter_class=FighterClass.ROGUE,
        char="@",
        color=colors.player_icon,
        name="Player",
        ai_cls=HostileEnemy,
        inventory=Inventory(capacity=26),
        level=Level(level_up_base=200),
    )],
    ai_cls=RoamingEnemy
)

# TODO: Give enemies equipment

janitor = Fighter(
    strength=2,
    perseverance=1,
    agility=4,
    magic=1,
    min_hp_per_level=3,
    max_hp_per_level=8,
    fighter_class=FighterClass.ROGUE,
    char="j",
    color=colors.janitor_icon,
    name="Janitor",
    sprite='images/janitor_sprite.png',
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=35),
)
lumberjack = Fighter(
    strength=5,
    perseverance=3,
    agility=3,
    magic=1,
    min_hp_per_level=6,
    max_hp_per_level=12,
    fighter_class=FighterClass.WARRIOR,
    char="L",
    color=colors.lumberjack_icon,
    name="Lumberjack",
    sprite='images/lumberjack_sprite.png',
    ai_cls=HostileEnemy,
    equipment=Equipment(),
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
    consumable=consumable.HealingConsumable(min_amount=4, max_amount=10),
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
