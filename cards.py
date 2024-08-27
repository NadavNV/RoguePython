from __future__ import annotations

from typing import List, TYPE_CHECKING

from components.fighter import Fighter
from status_types import StatusTypes

if TYPE_CHECKING:
    from engine import Engine


class Card:
    def __init__(self, parent: Fighter, playable: bool = True, burn: bool = False, ethereal: bool = False):
        self.parent = parent
        self.playable = playable
        self.burn = burn
        self.ethereal = ethereal
        self.keywords = []
        self._name = '<Card Name>'
        self._description = '<Card Description>'

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
