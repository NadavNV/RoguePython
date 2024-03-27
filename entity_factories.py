import copy
import random
import sys

from actions import MeleeAttack
import colors
from components.ai import RoamingEnemy, HostileEnemy
from components import consumable, equippable
from components.equipment import Equipment
from components.fighter import Fighter, Enemy
from components.inventory import Inventory
from components.level import Level
from components.loot_table import HealingItemTable
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


player = FighterGroup(
    x=0,
    y=0,
    fighters=[Fighter(
        strength=1,
        perseverance=1,
        agility=1,
        magic=1,
        min_hp_per_level=10,
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
    equippable=equippable.Handaxe(),
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


class Janitor(Enemy):
    def __init__(self, target_level: int):
        super().__init__(
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
            inventory=Inventory(capacity=26),
            level=Level(xp_given=50),
            weapon_crit_threshold=20,
            target_level=target_level,
            loot_table=RDSTable(
                contents=[
                    Gold(level=target_level, min_value=10, max_value=35, probability=30),
                    RDSNullValue(probability=50),
                    HealingItemTable(current_floor=max(1, target_level), count=1, probability=20)
                    # TODO: Add item drops
                ],
                count=2,
            ),
            stat_prio=RDSTable(
                contents=[
                    RDSValue(probability=3, value="Strength"),
                    RDSValue(probability=2, value="Perseverance"),
                    RDSValue(probability=4, value="Agility"),
                    RDSValue(probability=1, value="Magic"),
                ],
                count=3,
                always=True
            ),
        )

        self.equipment.parent = self
        self.inventory.parent = self

        self.abilities = [MeleeAttack(caster=self, target=None)]

        self.equipment.equip_to_slot(EquipmentSlot.MAINHAND, copy.deepcopy(broom), add_message=False)


class Lumberjack(Enemy):
    def __init__(self, target_level: int):
        super().__init__(
            strength=8,
            perseverance=3,
            agility=4,
            magic=1,
            min_hp_per_level=10,
            max_hp_per_level=25,
            fighter_class=FighterClass.WARRIOR,
            char="L",
            color=colors.lumberjack_icon,
            name="Lumberjack",
            sprite='images/lumberjack_sprite.png',
            ai_cls=HostileEnemy,
            equipment=Equipment(),
            inventory=Inventory(capacity=26),
            level=Level(xp_given=100),
            weapon_crit_threshold=20,
            target_level=target_level,
            loot_table=RDSTable(
                contents=[
                    Gold(level=target_level, min_value=35, max_value=70, probability=30),
                    RDSNullValue(probability=50),
                    # TODO: Add item drops
                ],
                count=2,
            ),
            stat_prio=RDSTable(
                contents=[
                    RDSValue(probability=3, value="Strength"),
                    RDSValue(probability=2, value="Perseverance"),
                    RDSValue(probability=4, value="Agility"),
                    RDSValue(probability=1, value="Magic"),
                ],
                count=3,
                always=True
            ),
        )

        self.equipment.parent = self
        self.inventory.parent = self

        self.abilities = [MeleeAttack(caster=self, target=None)]

        self.equipment.equip_to_slot(EquipmentSlot.MAINHAND, copy.deepcopy(handaxe), add_message=False)
        self.inventory.add_item(copy.deepcopy(tasty_rat))


if __name__ == "__main__":
    janitor = Janitor(target_level=3)
    print(janitor.hp)
    print(janitor.level.current_level)
    print(f"Strength: {janitor.strength}")
    print(f"Perseverance: {janitor.perseverance}")
    print(f"Agility: {janitor.agility}")
    print(f"Magic: {janitor.magic}")
