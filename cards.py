from __future__ import annotations

from typing import TYPE_CHECKING

from components.fighter import Fighter

if TYPE_CHECKING:
    from engine import Engine


class Card:
    def __init__(self, parent: Fighter, playable: bool = True, burn: bool = False, ethereal: bool = False):
        self.parent = parent
        self.playable = playable
        self.burn = burn
        self.ethereal = ethereal

    @property
    def engine(self) -> Engine:
        """Return the engine this action belongs to."""
        return self.parent.engine

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
