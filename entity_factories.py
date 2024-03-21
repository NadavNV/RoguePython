import copy

import colors
from components.ai import RoamingEnemy, HostileEnemy
from components import consumable, equippable
from components.equipment import Equipment
from components.fighter import Fighter
from components.inventory import Inventory
from components.level import Level
from mapentity import FighterGroup, Item
from fighter_classes import FighterClass
from equipment_slots import EquipmentSlot
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
        min_hp_per_level=7,
        max_hp_per_level=15,
        fighter_class=FighterClass.ROGUE,
        char="@",
        color=colors.player_icon,
        name="Player",
        ai_cls=HostileEnemy,
        inventory=Inventory(capacity=26, min_gold=0, max_gold=100),
        level=Level(level_up_base=200),
    )],
    ai_cls=RoamingEnemy
)
# TODO: Change to class Janitor(Fighter)
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
    inventory=Inventory(capacity=1, min_gold=15, max_gold=50),
    level=Level(xp_given=50),
)
janitor.abilities = [
    MeleeAttack(caster=janitor, target=None)
]

# TODO: Change to class Lumberjack(Fighter)
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
    inventory=Inventory(capacity=1, min_gold=50, max_gold=200),
    level=Level(xp_given=100),
)
lumberjack.abilities = [
    MeleeAttack(caster=lumberjack, target=None)
]

confusion_scroll = Item(
    buy_price=400,
    sell_price=60,
    char=SCROLL_CHAR,
    color=(207, 63, 255),
    name="Confusion Scroll",
    description="Confuse a single enemy, causing them to spend the next 5 turns doing nothing or attacking randomly.",
    consumable=consumable.ConfusionConsumable(number_of_turns=5),
    stackable=True
)

fireball_scroll = Item(
    buy_price=650,
    sell_price=100,
    char=SCROLL_CHAR,
    color=(255, 0, 0),
    name="Fireball Scroll",
    description="Create a magical explosion, hitting each enemy for up to 8 damage.",
    consumable=consumable.FireballDamageConsumable(damage=8),
    stackable=True
)

tasty_rat = Item(
    buy_price=50,
    sell_price=10,
    char=POTION_CHAR,
    color=(127, 0, 255),
    name="Tasty Rat",
    description="Eat the tasty rat to restore 4 to 10 hit points.",
    consumable=consumable.HealingConsumable(min_amount=4, max_amount=10),
    stackable=True
)

mana_potion = Item(
    buy_price=50,
    sell_price=10,
    char=POTION_CHAR,
    color=(0x0E, 0x86, 0xD4),
    name="Mana Potion",
    description="Drink to restore 4 mana.",
    consumable=consumable.ManaConsumable(amount=4),
    stackable=True
)

lightning_scroll = Item(
    buy_price=650,
    sell_price=100,
    char=SCROLL_CHAR,
    color=(255, 255, 0),
    name="Lightning Scroll",
    description="Strike a single enemy with a bolt of lightning, causing up to 12 damage.",
    consumable=consumable.LightningDamageConsumable(damage=12),
    stackable=True
)

dagger = Item(
    buy_price=25,
    sell_price=5,
    char=WEAPON_CHAR,
    color=(0, 191, 255),
    name="Dagger",
    description="Fine steel, good for stabbing. Can be used in the off hand. Agility weapon.",
    equippable=equippable.Dagger(),
)

broom = Item(
    buy_price=20,
    sell_price=4,
    char=WEAPON_CHAR,
    color=(0, 191, 255),
    name="Broom",
    description="Useful for sweeping floors and hitting snakes. Agility weapon.",
    equippable=equippable.Broom(),
)

janitor.equipment.equip_to_slot(EquipmentSlot.MAINHAND, copy.deepcopy(broom), add_message=False)

club = Item(
    buy_price=25,
    sell_price=5,
    char=WEAPON_CHAR,
    color=(0, 191, 255),
    name="Club",
    description="Long piece of wood, used for smacking evil in the face. Strength weapon.",
    equippable=equippable.Club(),
)

short_sword = Item(
    buy_price=45,
    sell_price=9,
    char=WEAPON_CHAR,
    color=(0, 191, 255),
    name="Short Sword",
    description="Shorter than a longsword, longer than a dagger. Finesse weapon. Must be equipped in the main hand.",
    equippable=equippable.ShortSword(),
)

handaxe = Item(
    buy_price=45,
    sell_price=9,
    char=WEAPON_CHAR,
    color=(0, 191, 255),
    name="Hand Axe",
    description="For cutting trees and enemies. Strength weapon. Must be equipped in the main hand.",
    equippable=equippable.ShortSword(),
)

lumberjack.equipment.equip_to_slot(EquipmentSlot.MAINHAND, copy.deepcopy(handaxe), add_message=False)

leather_armor = Item(
    buy_price=200,
    sell_price=40,
    char=ARMOR_CHAR,
    color=(139, 69, 19),
    name="Leather Armor",
    description="Layers of hardened leather provide some protection without restricting movement.",
    equippable=equippable.LeatherArmor(),
)

chain_mail = Item(
    buy_price=350,
    sell_price=70,
    char=ARMOR_CHAR,
    color=(139, 69, 19),
    name="Chain Mail",
    description=("A shirt made of interlocked metal rings. Provides decent protection but " +
                 "the weight makes movement somewhat challenging."),
    equippable=equippable.ChainMail(),
)
