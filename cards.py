from __future__ import annotations

from typing import Optional, Set, TYPE_CHECKING

from tcod.constants import COLCTRL_FORE_RGB, COLCTRL_STOP

import colors
from components.fighter import Fighter
from status_types import StatusTypes

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


class Card:
    parent: Fighter = None

    def __init__(self, cost: int, playable: bool = True, burn: bool = False, ethereal: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.cost = cost
        self.playable: bool = playable
        self.burn: bool = burn
        self.ethereal: bool = ethereal
        self.keywords: Set[str] = set()
        self._name: str = '<Card Name>'
        self._description: str = '<Card Description>'

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
        pass

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return str(self) + ' ' + hex(id(self))


class BlockCard(Card):
    def __init__(self, *, amount: int, cost: int, burn: bool = False, ethereal: bool = False, **kwargs):
        super().__init__(cost=cost, playable=True, burn=burn, ethereal=ethereal, **kwargs)
        self.amount = amount

    def block(self) -> None:
        desc = f"{self.parent.name.capitalize()} gained {
            self.amount + self.parent.buffs[StatusTypes.AGILITY]
        } block."
        self.parent.block += self.amount + self.parent.buffs[StatusTypes.AGILITY]
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
        if target.buffs[StatusTypes.EVASION] > 0:
            self.engine.message_log.add_message(
                f"{attack_desc} but misses.", attack_color
            )
            target.buffs[StatusTypes.EVASION] -= 1
            return False
        else:
            damage = target.take_damage(
                (self.damage + self.parent.buffs[StatusTypes.STRENGTH]) *
                (1.5 if target.debuffs[StatusTypes.EXPOSED] > 0 else 1)
            )
            if damage > 0:
                self.engine.message_log.add_message(
                    f"{attack_desc} for {damage} hit points.", attack_color
                )
                return True
            else:
                self.engine.message_log.add_message(
                    f"{attack_desc} but does no damage.", attack_color
                )
                return False


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
        self._description = f"Quickly stab an enemy for {COLCTRL_FORE_RGB:c}{colors.balm[0]:c}" + \
                            f"{colors.balm[1]:c}{colors.balm[2]:c}<1>{COLCTRL_STOP:c} damage."

    @property
    def description(self) -> str:
        if self.target:
            return self._description.replace("<1>", f"{
            (self.damage + self.parent.buffs[StatusTypes.STRENGTH]) *
            (1.5 if self.target.debuffs[StatusTypes.EXPOSED] > 0 else 1)
            }")
        else:
            return self._description.replace("<1>", f"{
            self.damage + self.parent.buffs[StatusTypes.STRENGTH]
            }")

    def on_play(self) -> None:
        super().on_play()
        self.attack(self.target)


class Dodge(BlockCard):
    def __init__(self, **kwargs):
        super().__init__(amount=5, cost=1, **kwargs)
        self._name = "Dodge"
        self._description = f"Anticipate your opponent's attacks, gaining {COLCTRL_FORE_RGB:c}{colors.balm[0]:c}" + \
                            f"{colors.balm[1]:c}{colors.balm[2]:c}<1>{COLCTRL_STOP:c} block"

    @property
    def description(self) -> str:
        return self._description.replace("<1>", f"{self.amount + self.parent.buffs[StatusTypes.AGILITY]}")

    def on_play(self) -> None:
        self.block()

# TODO: Add more cards

###############
# Enemy Cards #
###############

#################
# Janitor Cards #
#################


class Smack(TargetedCard):
    def __init__(self, **kwargs):
        super().__init__(damage=5, cost=0, **kwargs)
        self._name = "Smack"
        self._description = f"Deal {COLCTRL_FORE_RGB:c}{colors.red[0]:c}" + \
                            f"{colors.red[1]:c}{colors.red[2]:c}<1>{COLCTRL_STOP:c} damage."

    def on_draw(self) -> None:
        self.target = self.engine.player[0]

    @property
    def description(self) -> str:
        return self._description.replace("<1>", f"{
        (self.damage + self.parent.buffs[StatusTypes.STRENGTH]) *
        (1.5 if self.target.debuffs[StatusTypes.EXPOSED] > 0 else 1)
        }")

    def on_play(self) -> None:
        super().on_play()
        self.attack(self.target)


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
        (self.damage + self.parent.buffs[StatusTypes.STRENGTH]) *
        (1.5 if self.target.debuffs[StatusTypes.EXPOSED] > 0 else 1)
        }")

    def on_play(self) -> None:
        super().on_play()
        self.attack(self.target)
        self.attack(self.target)
