from __future__ import annotations

from typing import Set, TYPE_CHECKING

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
            return "Absorbs 1 attack damage per stack. Does not block damage-over-time effects like bleed or poison." +\
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
    def __init__(self, parent: Fighter, playable: bool = True, burn: bool = False, ethereal: bool = False):
        self.parent: Fighter = parent
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


class AttackCard(Card):
    def __init__(
            self,
            parent: Fighter,
            name: str,
            description: str,
            damage: int,
            playable: bool = True,
            burn: bool = False,
            ethereal: bool = False,
    ):
        super().__init__(parent=parent, playable=playable, burn=burn, ethereal=ethereal)
        self._name = name
        self._damage = damage
        self._description = description

    @property
    def damage(self) -> int:
        return self._damage

    @property
    def description(self) -> str:
        return self._description.replace('<damage>', f"{self.parent.buffs[StatusTypes.STRENGTH] + self._damage}")
