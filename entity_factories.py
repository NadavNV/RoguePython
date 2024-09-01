from typing import Optional

import copy
import random
import sys

import colors
from cards import AttackCard, Jab
from components.ai import RoamingEnemy, HostileEnemy
from components import consumable, equippable
from components.equipment import Equipment
from components.fighter import Enemy, Rogue, Warrior, Mage
from components.inventory import Inventory
from components.level import Level
from components.loot_table import HealingItemTable, WeaponsTable
from components.resoucre import Rage, Stamina, Mana
from dropgen.RDSNullValue import RDSNullValue
from dropgen.RDSTable import RDSTable
from dropgen.RDSValue import RDSValue
from entity import FighterGroup, Item
from equipment_slots import EquipmentSlot
from fighter_classes import FighterClass

SCROLL_CHAR = '~'
POTION_CHAR = '!'
WEAPON_CHAR = '/'
ARMOR_CHAR = '['


class HealingItem(Item):
    def __init__(
            self,
            min_floor: int,
            max_floor: int,
            min_amount: int,
            max_amount: int,
            probability: float,
            sell_price: int,
            buy_price: int,
            name: str = "<Unnamed>",
            description: str = "<None>",
    ):
        super().__init__(
            sell_price=sell_price,
            buy_price=buy_price,
            char=POTION_CHAR,
            color=colors.healing_potion,
            name=name,
            description=description,
            consumable=consumable.HealingConsumable(min_amount, max_amount),
            probability=probability,
            stackable=True,
        )

        self.min_floor = min_floor
        self.max_floor = max_floor

    def on_rds_pre_result_eval(self, **kwargs):
        if self.min_floor <= self.rds_table.current_floor <= self.max_floor:
            self.rds_enabled = True


class WeaponItem(Item):
    def __init__(
            self,
            sell_price: int,
            buy_price: int,
            equippable_component: equippable.Equippable,
            probability: Optional[float] = None,
            name: str = "<Unnamed>",
            description: str = "<None>",
    ):
        super().__init__(
            sell_price=sell_price,
            buy_price=buy_price,
            char=WEAPON_CHAR,
            color=colors.weapon,
            name=name,
            description=description,
            probability=probability,
            stackable=False,
            equippable=equippable_component
        )

    def on_rds_hit(self, **kwargs):
        floor = self.rds_table.current_floor
        n = random.choices(
            population=[floor - 2, floor - 1, floor, floor + 1, floor + 2],
            weights=[1, 7, 14, 7, 1],
        )[0]

        if n > 0:
            self.equippable.enhance_item(n)


rogue_deck = [Jab() for _ in range(10)]

rogue = FighterGroup(
    x=0,
    y=0,
    fighters=[Rogue(
        ai_cls=HostileEnemy,
        deck=rogue_deck
    )],
    ai_cls=RoamingEnemy
)

warrior = FighterGroup(
    x=0,
    y=0,
    fighters=[Warrior(
        ai_cls=HostileEnemy,
        deck=[AttackCard(
            name='Attack',
            damage=5,
            description="Deal <1> damage to a single enemy.",
        ) for _ in range(10)] +
             [AttackCard(
                 name='Super Attack',
                 damage=10,
                 description="Deal <1> damage to a single enemy.",
             ) for _ in range(5)]
    )],
    ai_cls=RoamingEnemy
)

mage = FighterGroup(
    x=0,
    y=0,
    fighters=[Mage(
        ai_cls=HostileEnemy,
        deck=[AttackCard(
            name='Attack',
            damage=5,
            description="Deal <1> damage to a single enemy.",
        ) for _ in range(10)] +
             [AttackCard(
                 name='Super Attack',
                 damage=10,
                 description="Deal <1> damage to a single enemy.",
             ) for _ in range(5)]
    )],
    ai_cls=RoamingEnemy
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

tasty_rat = HealingItem(
    buy_price=50,
    sell_price=10,
    name="Tasty Rat",
    description="Eat the tasty rat to restore 4 to 10 hit points.",
    probability=50,
    min_amount=4,
    max_amount=10,
    min_floor=1,
    max_floor=5,
)

plump_rat = HealingItem(
    buy_price=500,
    sell_price=100,
    name="Plump Rat",
    description="Eat the plump rat to restore 8 to 20 hit points.",
    probability=40,
    min_amount=8,
    max_amount=20,
    min_floor=4,
    max_floor=8,
)

enormous_rat = HealingItem(
    buy_price=5000,
    sell_price=1000,
    name="Enormous Rat",
    description="Eat the enormous rat to restore 16 to 40 hit points.",
    probability=20,
    min_amount=16,
    max_amount=40,
    min_floor=7,
    max_floor=sys.maxsize
)

rodent_of_unusual_size = HealingItem(
    buy_price=50000,
    sell_price=10000,
    name="Rodent of Unusual Size",
    description="Eat the R.O.U.S. to restore 30 to 60 hit points.",
    probability=10,
    min_amount=30,
    max_amount=60,
    min_floor=12,
    max_floor=sys.maxsize

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

dagger = WeaponItem(
    buy_price=25,
    sell_price=5,
    name="Dagger",
    description="Fine steel, good for stabbing. Can be used in the off hand. Agility weapon.",
    equippable_component=equippable.Dagger(),
)

broom = WeaponItem(
    buy_price=20,
    sell_price=4,
    name="Broom",
    description="Useful for sweeping floors and hitting snakes. Agility weapon. Requires both hands to wield",
    equippable_component=equippable.Broom(),
)

club = WeaponItem(
    buy_price=25,
    sell_price=5,
    name="Club",
    description="Long piece of wood, used for smacking evil in the face. Strength weapon.",
    equippable_component=equippable.Club(),
)

short_sword = WeaponItem(
    buy_price=45,
    sell_price=9,
    name="Short Sword",
    description="Shorter than a longsword, longer than a dagger. Finesse weapon. Must be equipped in the main hand.",
    equippable_component=equippable.ShortSword(),
)

handaxe = WeaponItem(
    buy_price=25,
    sell_price=5,
    name="Hand Axe",
    description="For cutting trees and enemies. Strength weapon. Must be equipped in the main hand.",
    equippable_component=equippable.Handaxe(),
)

greatsword = WeaponItem(
    buy_price=100,
    sell_price=20,
    name="Greatsword",
    description="Massive piece of steel. Requires both hands to wield. Strength based.",
    equippable_component=equippable.Greatsword(),
)

wand = WeaponItem(
    buy_price=25,
    sell_price=5,
    name="Wand",
    description="Enchanted wooden rod that can fire magical projectiles. Magic based weapon.",
    equippable_component=equippable.Wand(),
)

staff = WeaponItem(
    buy_price=25,
    sell_price=5,
    name="Staff",
    description="Enchanted wooden rod that can fire magical projectiles. Magic based weapon." +
                " Requires both hands to wield",
    equippable_component=equippable.Staff(),
)

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


class Gold(RDSValue):
    def __init__(self, level: int, min_value: int, max_value: int, probability: float):
        level = max(1, level)
        value = random.randint(level * min_value, level * max_value)

        super().__init__(
            probability=probability,
            value=value,
            unique=True,
        )


janitor_deck = [AttackCard(name='Smack', damage=5, description="Deal <1> damage to the player.")]


class Janitor(Enemy):
    def __init__(self, target_level: int):
        super().__init__(
            min_hp_on_spawn=30,
            max_hp_on_spawn=50,
            hp_per_level=10,
            deck=janitor_deck,
            char="j",
            color=colors.janitor_icon,
            name="Janitor",
            sprite='images/janitor_sprite.png',
            ai_cls=HostileEnemy,
            level=Level(xp_given=50),
            target_level=target_level,
            loot_table=RDSTable(
                contents=[
                    Gold(level=target_level, min_value=10, max_value=35, probability=30),
                    RDSNullValue(probability=50),
                    HealingItemTable(current_floor=max(1, target_level), count=1, probability=20),
                    WeaponsTable(current_floor=max(1, target_level), count=1, probability=10),
                    # TODO: Add item drops
                ],
                count=2,
            ),
        )


lumberjack_deck = [AttackCard(name='Chop', damage=5, description="Deal <1> damage to the player.")]


class Lumberjack(Enemy):
    def __init__(self, target_level: int):
        super().__init__(
            min_hp_on_spawn=45,
            max_hp_on_spawn=65,
            hp_per_level=20,
            char="L",
            color=colors.lumberjack_icon,
            name="Lumberjack",
            sprite='images/lumberjack_sprite.png',
            ai_cls=HostileEnemy,
            deck=lumberjack_deck,
            level=Level(xp_given=100),
            target_level=target_level,
            loot_table=RDSTable(
                contents=[
                    Gold(level=target_level, min_value=35, max_value=70, probability=30),
                    RDSNullValue(probability=50),
                    HealingItemTable(current_floor=max(1, target_level), count=1, probability=20),
                    WeaponsTable(current_floor=max(1, target_level), count=1, probability=10),
                    # TODO: Add item drops
                ],
                count=2,
            ),
        )


if __name__ == "__main__":
    janitor = Janitor(target_level=3)
    print(janitor.hp)
    print(janitor.level.current_level)
