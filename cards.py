from __future__ import annotations

from typing import Optional, Set, TYPE_CHECKING

from tcod.constants import COLCTRL_FORE_RGB, COLCTRL_STOP

import colors
from components.fighter import Fighter
from dropgen.RDSObject import RDSObject
from status_types import StatusType
from talents import Talent

if TYPE_CHECKING:
    from engine import Engine


def keyword_to_description(keyword: str) -> str:
    match keyword:
        case "agility":
            return "Increase block gained from cards by 1 per stack."
        case "armor":
            return "At the end of the turn, grant 1 block per stack. Lose 1 stack when taking HP damage from attacks."
        case "balm":
            return "At the end of the turn, restore 1 HP per stack."
        case "barbed":
            return "When attacked, deal 1 damage to the attacker per stack."
        case "bleed":
            return "At the start of the turn, take 1 damage per stack and decrease stacks by 1."
        case "blight":
            return "At the end of the turn, take 1 damage per stack and increase stacks by 1."
        case "block":
            return "Absorbs 1 attack damage per stack. Does not block damage-over-time effects like bleed or poison." + \
                " Removed at the start of the turn."
        case "burn":
            return "When played, does not go to the discard pile."
        case "burning":
            return "At the start of the turn, take 1 damage per stack and decrease stacks by half."
        case "ethereal":
            return "If not played this turn, goes to the burn pile."
        case "evasion":
            return "Negate the next attack that would have dealt HP damage and remove 1 stack."
        case "exposed":
            return "Damage received from attacks is increased by 50%. Stacks reduced by 1 at the end of the turn."
        case "poison":
            return "At the end of the turn, take 1 damage per stack."
        case "shattered":
            return "Block gained from cards is reduced by 50%. Reduced by 1 at the end of the turn."
        case "strength":
            return "Damage dealt by attacks is increased by 1 per stack."
        case 'ward':
            return "Negate the next debuff application and remove a stack."
        case 'weakness':
            return "Base damage dealt is reduced by 50%."


class Card(RDSObject):
    parent: Fighter = None

    def __init__(self, cost: int, upgradable: bool = True, playable: bool = True, burn: bool = False, ethereal: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.cost = cost
        self.original_cost = cost
        self.playable: bool = playable
        self.burn: bool = burn
        self.ethereal: bool = ethereal
        self.upgradable: bool = upgradable
        self.is_upgraded: bool = False
        self.keywords: Set[str] = set()
        self._name: str = '<Card Name>'
        self._description: str = '<Card Description>'
        self.upgrade_description: str = "<upgrade description>"

        if self.burn:
            self.keywords.add("burn")
        if self.ethereal:
            self.keywords.add("ethereal")

    @property
    def engine(self) -> Engine:
        """Return the engine this action belongs to."""
        return self.parent.engine

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def on_draw(self) -> None:
        """
        What should happen when this card is drawn. Can be overridden by Card subclasses.
        """
        pass

    def on_play(self) -> None:
        """
        What should happen when this card is played. Can be overridden by Card subclasses.
        """
        pass

    def on_turn_end(self) -> None:
        """
        What should happen at the end of the turn if this card hasn't been played.
        Can be overridden by Card subclasses.
        """
        self.cost = self.original_cost
        if self.ethereal:
            self.parent.burn.append(self)
        else:
            self.parent.discard.append(self)

    def upgrade(self) -> None:
        """
        upgrades the card if it is upgradable. Must be overridden by upgradable crds.
        """
        assert self.upgradable
        assert not self.is_upgraded
        self.is_upgraded = True

    def temporary_cost(self, new_cost: int) -> None:
        self.cost = new_cost

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return str(self) + ' ' + hex(id(self))


class BlockCard(Card):
    def __init__(self, *, amount: int, cost: int, burn: bool = False, ethereal: bool = False, **kwargs):
        super().__init__(cost=cost, playable=True, burn=burn, ethereal=ethereal, **kwargs)
        self.amount = amount
        self.keywords.add('block')

    def block(self) -> None:
        desc = f"{self.parent.name.capitalize()} gained {
            self.amount + self.parent.buffs[StatusType.AGILITY]
        } block."
        self.parent.block += self.amount + self.parent.buffs[StatusType.AGILITY]
        self.engine.message_log.add_message(
            text=desc,
            fg=colors.block,
            stack=False,
        )


class AttackCard(Card):
    def __init__(self, *, damage: int, cost: int, burn: bool = False, ethereal: bool = False, **kwargs):
        super().__init__(cost=cost, playable=True, burn=burn, ethereal=ethereal, **kwargs)
        self.damage = damage

    def attack(self, target: Fighter) -> bool:
        """
        Performs an attack action against target, including adding a messsage to
        the message log. Returns True if the attack deals HP damage, False otherwise.
        """
        attack_desc = f"{self.parent.name.capitalize()} attacks {target.name}"
        if self.parent.parent is self.engine.player:
            attack_color = colors.player_atk
        else:
            attack_color = colors.enemy_atk
        if target.buffs[StatusType.EVASION] > 0:
            self.engine.message_log.add_message(
                f"{attack_desc} but misses.", attack_color
            )
            target.buffs[StatusType.EVASION] -= 1
            return False
        else:
            damage = target.take_damage(
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH]) *
                (1.5 if target.debuffs[StatusType.EXPOSED] > 0 else 1)
            )
            if damage > 0:
                self.engine.message_log.add_message(
                    f"{attack_desc} for {damage} hit points.", attack_color
                )
                result = True
            else:
                self.engine.message_log.add_message(
                    f"{attack_desc} but does no damage.", attack_color
                )
                result = False
            if Talent.ATTACKS_INFLICT_BLEED in self.parent.talents:
                bleed = self.parent.talents[Talent.ATTACKS_INFLICT_BLEED]
                if bleed > 0:
                    self.engine.message_log.add_message(
                        f"{self.parent.name.capitalize()} inflicts {bleed} bleed on {target.name}.", colors.bleed
                    )
            return result


class TargetedCard(AttackCard):
    def __init__(self, damage: int, cost: int, burn: bool = False, ethereal: bool = False, **kwargs):
        super().__init__(damage=damage, cost=cost, burn=burn, ethereal=ethereal, **kwargs)
        self.target: Optional[Fighter] = None

    def on_play(self) -> None:
        """
        Sanity check that a targeted card isn't activated without setting a target first. Must be called by
        subclasses' on_play method.
        """
        assert self.target is not None


################
# Player Cards #
################

###############
# Rogue Cards #
###############


class Jab(TargetedCard):
    def __init__(self, **kwargs):
        super().__init__(damage=5, cost=1, **kwargs)
        self._name = "Jab"
        self._description = f"Deal {COLCTRL_FORE_RGB:c}{colors.balm[0]:c}" + \
                            f"{colors.balm[1]:c}{colors.balm[2]:c}<1>{COLCTRL_STOP:c} damage.\n\nCosts 1 Stamina."
        self.upgrade_description: str = "Increase damage from 5 to 8."

    @property
    def description(self) -> str:
        if self.target:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH]) *
                (1.5 if self.target.debuffs[StatusType.EXPOSED] > 0 else 1)
            }")
        else:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH])
            }")

    def on_play(self) -> None:
        super().on_play()
        self.attack(self.target)
        self.parent.discard.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.damage = 8


class Dodge(BlockCard):
    def __init__(self, **kwargs):
        super().__init__(amount=5, cost=1, **kwargs)
        self._name = "Dodge"
        self._description = f"Gain {COLCTRL_FORE_RGB:c}{colors.balm[0]:c}" + \
                            f"{colors.balm[1]:c}{colors.balm[2]:c}<1>{COLCTRL_STOP:c} block.\n\nCosts 1 Stamina."
        self.upgrade_description: str = "Increase block amount from 5 to 8."

    @property
    def description(self) -> str:
        return self._description.replace("<1>", f"{self.amount + self.parent.buffs[StatusType.AGILITY]}")

    def on_play(self) -> None:
        self.block()
        self.parent.discard.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.amount = 8


class SanguineStrike(TargetedCard):
    def __init__(self, **kwargs):
        super().__init__(damage=4, cost=2, **kwargs)
        self._name = "Sanguine Strike"
        self._bleed = 2
        self._description = f"Deal {COLCTRL_FORE_RGB:c}{colors.balm[0]:c}" + \
                            f"{colors.balm[1]:c}{colors.balm[2]:c}<1>{COLCTRL_STOP:c} damage. If damage dealt to " + \
                            f"HP inflict <2> bleed.\n\nCosts 2 Stamina."
        self.upgrade_description: str = "Increase damage from 4 to 5. Increase bleed amount from 2 to 4."
        self.keywords.add('bleed')

    @property
    def description(self) -> str:
        if self.target:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH]) *
                (1.5 if self.target.debuffs[StatusType.EXPOSED] > 0 else 1)
            }").replace("<2>", str(self._bleed))
        else:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH])
            }").replace("<2>", str(self._bleed))

    def on_play(self) -> None:
        super().on_play()
        if self.attack(self.target):
            self.target.debuffs[StatusType.BLEED] += self._bleed
            self.engine.message_log.add_message(
                f"{self.parent.name.capitalize()} inflicts {self._bleed} bleed on {self.target.name}.", colors.bleed
            )
        self.parent.discard.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.damage = 5
        self._bleed = 4


class SnakeBite(TargetedCard):
    def __init__(self, **kwargs):
        super().__init__(damage=3, cost=3, **kwargs)
        self._name = "Snake Bite"
        self._poison = 1
        self._description = f"Deal {COLCTRL_FORE_RGB:c}{colors.balm[0]:c}" + \
                            f"{colors.balm[1]:c}{colors.balm[2]:c}<1>{COLCTRL_STOP:c} damage. If damage dealt to " + \
                            f"HP inflict <2> poison.\n\nCosts <3> Stamina."
        self.upgrade_description: str = "Increase poison amount from 1 to 2. Reduce cost from 3 to 2."
        self.keywords.add('poison')

    @property
    def description(self) -> str:
        if self.target:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH]) *                 
                (1.5 if self.target.debuffs[StatusType.EXPOSED] > 0 else 1)
            }").replace("<2>", str(self._poison)).replace('<3>', str(self.cost))
        else:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH])
            }").replace("<2>", str(self._poison))

    def on_play(self) -> None:
        super().on_play()
        if self.attack(self.target):
            self.target.debuffs[StatusType.POISON] += self._poison
            self.engine.message_log.add_message(
                f"{self.parent.name.capitalize()} inflicts {self._poison} bleed on {self.target.name}.", colors.poison
            )
        self.parent.discard.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.cost = 2
        self.original_cost = 2
        self._poison = 2


class Muster(Card):
    def __init__(self, **kwargs):
        super().__init__(cost=1, **kwargs)
        self._name = "Muster"
        self.strength = 1
        self.agility = 1
        self._description = "Gain <1> strength and <2> agility.\n\nCosts 1 Stamina."
        self.upgrade_description: str = "Increase strength and agility amount from 1 to 2."
        self.keywords.add('strength')
        self.keywords.add('agility')

    @property
    def description(self) -> str:
        return self._description.replace("<1>", str(self.strength)).replace("<2>", str(self.agility))

    def on_play(self) -> None:
        self.parent.buffs[StatusType.STRENGTH] += self.strength
        self.parent.buffs[StatusType.AGILITY] += self.agility
        self.parent.discard.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.strength = 2
        self.agility = 2


class FlashBomb(Card):
    def __init__(self, **kwargs):
        super().__init__(cost=2, burn=True, **kwargs)
        self._name = "Flash Bomb"
        self._description = "Stun all enemies for 1 round.\n\nCosts <1> Stamina."
        self.upgrade_description: str = "Reduce cost from 2 to 1."

    @property
    def description(self) -> str:
        return self._description.replace("<1>", str(self.cost))

    def on_play(self) -> None:
        for enemy in self.engine.active_enemies.fighters:
            self.engine.message_log.add_message(
                f"{enemy.name.capitalize()} is stunned!", colors.debuff
            )
            enemy.stun()
            enemy.hand.append(Stunned())
        self.parent.burn.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.cost = 1
        self.original_cost = 1

class SmokeBomb(Card):
    def __init__(self, **kwargs):
        super().__init__(cost=2, burn=True, **kwargs)
        self.evasion = 2
        self._name = "Smoke Bomb"
        self._description = "Gain <1> Evasion.\n\nCosts 2 Stamina."
        self.upgrade_description: str = "Increase evasion amount from 2 to 3."
        self.keywords.add('evasion')

    @property
    def description(self) -> str:
        return self._description.replace("<1>", str(self.evasion))

    def on_play(self) -> None:
        self.parent.buffs[StatusType.EVASION] += self.evasion
        self.engine.message_log.add_message(
            f"{self.parent.name.capitalize()} gained {self.evasion} evasion.", colors.evasion
        )
        self.parent.burn.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.evasion = 3


class ShrapnelBomb(Card):
    def __init__(self, **kwargs):
        super().__init__(cost=2, burn=True, **kwargs)
        self._name = "Shrapnel Bomb"
        self.bleed = 3
        self._description = "Inflict <1> bleed on all enemies.\n\nCosts 2 Stamina."
        self.upgrade_description: str = "Increase bleed amount from 3 to 5."
        self.keywords.add('bleed')

    @property
    def description(self) -> str:
        return self._description.replace("<1>", str(self.bleed))

    def on_play(self) -> None:
        for enemy in self.engine.active_enemies.fighters:
            enemy.debuffs[StatusType.BLEED] += self.bleed
            self.engine.message_log.add_message(
                f"{enemy.name.capitalize()} gained {self.bleed} bleed!", colors.bleed
            )
        self.parent.burn.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.bleed = 5


class PrecisionStrike(TargetedCard):
    def __init__(self, **kwargs):
        super().__init__(damage=20, cost=2, ethereal=True, **kwargs)
        self._name = "Precision Strike"
        self._description = f"Ethereal. Deal {COLCTRL_FORE_RGB:c}{colors.balm[0]:c}" + \
                            f"{colors.balm[1]:c}{colors.balm[2]:c}<1>{COLCTRL_STOP:c} damage.\n\nCosts 2 Stamina."
        self.upgrade_description: str = "Increase damage from 20 to 40."

    @property
    def description(self) -> str:
        if self.target:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH]) *
                (1.5 if self.target.debuffs[StatusType.EXPOSED] > 0 else 1)
            }")
        else:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH])
            }")

    def on_play(self) -> None:
        super().on_play()
        self.attack(self.target)
        self.parent.discard.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.damage = 40


class SideEffects(TargetedCard):
    def __init__(self, **kwargs):
        super().__init__(damage=4, cost=1, **kwargs)
        self._weakness = 1
        self._name = "Side Effects"
        self._description = f"Deal {COLCTRL_FORE_RGB:c}{colors.balm[0]:c}" + \
                            f"{colors.balm[1]:c}{colors.balm[2]:c}<1>{COLCTRL_STOP:c} damage. If the target" +\
                            f" is poisoned, inflict <2> weakness.\n\nCosts 1 Stamina."
        self.upgrade_description: str = "Increase weakness amount from 1 to 2."
        self.keywords.add('weakness')
        self.keywords.add('poison')

    @property
    def description(self) -> str:
        if self.target:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH]) * 
                (1.5 if self.target.debuffs[StatusType.EXPOSED] > 0 else 1)
            }").replace("<2>", str(self._weakness))
        else:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH])
            }").replace("<2>", str(self._weakness))

    def on_play(self) -> None:
        super().on_play()
        self.attack(self.target)
        if self.target.debuffs[StatusType.POISON] > 0:
            self.target.debuffs[StatusType.WEAKNESS] += self._weakness
            self.engine.message_log.add_message(
                f"{self.parent.name.capitalize()} inflicts {self._weakness} weakness on {self.target.name}.",
                colors.weakness
            )
        self.parent.discard.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self._weakness = 2


class DanseMacabre(TargetedCard):
    def __init__(self, **kwargs):
        super().__init__(damage=4, cost=1, **kwargs)
        self._agility = 1
        self._name = "Danse Macabre"
        self._description = f"Deal {COLCTRL_FORE_RGB:c}{colors.balm[0]:c}" + \
                            f"{colors.balm[1]:c}{colors.balm[2]:c}<1>{COLCTRL_STOP:c} damage 2 times. Gain " +\
                            f"<2> Agility.\n\nCosts 1 Stamina."
        self.upgrade_description: str = "Increase damage from 4 to 6. Increase Agility from 1 to 2"
        self.keywords.add('agility')

    def description(self) -> str:
        if self.target:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH]) * 
                (1.5 if self.target.debuffs[StatusType.EXPOSED] > 0 else 1)
            }").replace("<2>", str(self._agility))
        else:
            return self._description.replace("<1>", f"{
                (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
                 self.parent.buffs[StatusType.STRENGTH])
            }").replace("<2>", str(self._agility))

    def on_play(self) -> None:
        super().on_play()
        self.attack(self.target)
        self.attack(self.target)
        self.parent.buffs[StatusType.AGILITY] += self._agility
        self.engine.message_log.add_message(
            text=f"{self.parent.name.capitalize()} gains {self._agility} agility", fg=colors.agility
        )
        self.parent.discard.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.damage = 6
        self._agility = 2


class Flourish(AttackCard):
    def __init__(self, **kwargs):
        super().__init__(damage=4, cost=1, **kwargs)
        self._exposed = 1
        self._name = "Flourish"
        self._description = f"Deal {COLCTRL_FORE_RGB:c}{colors.balm[0]:c}" + \
                            f"{colors.balm[1]:c}{colors.balm[2]:c}<1>{COLCTRL_STOP:c} damage to all enemies." +\
                            f"When dealing HP damage, inflict <2> Exposed\n\nCosts 1 Stamina."
        self.upgrade_description: str = "Increase damage from 4 to 7. Increase Exposed from 1 to 2"
        self.keywords.add('exposed')

    def description(self) -> str:
        return self._description.replace("<1>", f"{
            (self.damage * (0.5 if self.parent.debuffs[StatusType.WEAKNESS] > 0 else 1) +
             self.parent.buffs[StatusType.STRENGTH])
        }").replace("<2>", str(self._exposed))

    def on_play(self) -> None:
        super().on_play()
        for enemy in self.engine.active_enemies.fighters:
            if self.attack(enemy):
                enemy.debuffs[StatusType.EXPOSED] += self._exposed
                self.engine.message_log.add_message(
                    text=f"{enemy.name} gains {self._exposed} Exposed!",
                    fg=colors.exposed
                )
        self.parent.discard.append(self)

    def upgrade(self) -> None:
        super().upgrade()
        self.damage = 7
        self._exposed = 2


class CardTrick(Card):
    def __init__(self, **kwargs):
        super().__init__(cost=3, **kwargs)
        self._name = "Card Trick"
        self._description = "At the start of the turn, draw 1 extra card. It costs 0 this turn.\n\nCosts <1> stamina."
        self.upgrade_description = "Reduce cost from 3 to 1."

    @property
    def description(self) -> str:
        return self._description.replace("<1>", str(self.cost))

    def on_play(self) -> None:
        self.parent.talents[Talent.DRAW_EXTRA_FREE_CARD] += 1

    def upgrade(self) -> None:
        super().upgrade()
        self.cost = 1

# TODO: Add more cards

###############
# Enemy Cards #
###############

#################
# Janitor Cards #
#################


class Smack(TargetedCard):
    def __init__(self, **kwargs):
        super().__init__(damage=8, cost=0, **kwargs)
        self._name = "Smack"
        self._description = f"Deal {COLCTRL_FORE_RGB:c}{colors.red[0]:c}" + \
                            f"{colors.red[1]:c}{colors.red[2]:c}<1>{COLCTRL_STOP:c} damage."

    def on_draw(self) -> None:
        self.target = self.engine.player[0]

    @property
    def description(self) -> str:
        return self._description.replace("<1>", f"{
        (self.damage + self.parent.buffs[StatusType.STRENGTH]) *
        (1.5 if self.target.debuffs[StatusType.EXPOSED] > 0 else 1)
        }")

    def on_play(self) -> None:
        super().on_play()
        self.attack(self.target)
        self.parent.discard.append(self)


####################
# Lumberjack Cards #
####################


class Chop(TargetedCard):
    def __init__(self, **kwargs):
        super().__init__(damage=3, cost=0, **kwargs)
        self._name = "Chop"
        self._description = f"Deal {COLCTRL_FORE_RGB:c}{colors.red[0]:c}" + \
                            f"{colors.red[1]:c}{colors.red[2]:c}<1>{COLCTRL_STOP:c} damage twice."

    def on_draw(self) -> None:
        self.target = self.engine.player[0]

    @property
    def description(self) -> str:
        return self._description.replace("<1>", f"{
        (self.damage + self.parent.buffs[StatusType.STRENGTH]) *
        (1.5 if self.target.debuffs[StatusType.EXPOSED] > 0 else 1)
        }")

    def on_play(self) -> None:
        super().on_play()
        self.attack(self.target)
        self.attack(self.target)
        self.parent.discard.append(self)


class Stunned(Card):
    def __init__(self, **kwargs):
        super().__init__(cost=0, **kwargs)
        self._name = "Stunned"
        self._description = "The enemy skips a turn."
