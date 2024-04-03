from __future__ import annotations

from typing import Tuple, TYPE_CHECKING

from tcod.console import Console

if TYPE_CHECKING:
    from components.fighter import Fighter

import colors


class Resource:
    parent: Fighter
    name: str
    color: Tuple[int, int, int]

    def __init__(self, max_amount: int, current_amount: int) -> None:
        self.max_amount = max_amount
        self.current_amount = current_amount

    def spend(self, amount: int) -> None:
        self.current_amount = max(self.current_amount - amount, 0)

    def gain(self, amount: int):
        self.current_amount = min(self.current_amount + amount, self.max_amount)

    def on_turn_end(self) -> None:
        raise NotImplementedError()

    def render_bar(self, console: Console, x: int, y: int, width: int):
        filled_width = int(float(self.current_amount) / self.max_amount * width)

        console.draw_rect(
            x=x,
            y=y,
            width=width,
            height=1,
            ch=1,
            bg=colors.bar_empty
        )

        console.draw_rect(
            x=x, y=y, width=filled_width, height=1, ch=1, bg=self.color
        )

        console.print(
            x=x + 1,
            y=y,
            string=f"{self.name.capitalize()}: {self.current_amount}/{self.max_amount}", fg=colors.bar_text
        )


class Rage(Resource):
    def __init__(self):
        super().__init__(max_amount=100, current_amount=0)

        self.name = 'rage'
        self.color = colors.bar_rage_filled
        self.stable_amount = 0

    def on_turn_end(self) -> None:
        if not self.parent.engine.in_combat:
            if self.current_amount != self.stable_amount:
                self.current_amount -= (self.current_amount - self.stable_amount) // 3


class Stamina(Resource):
    def __init__(self):
        super().__init__(max_amount=100, current_amount=100)

        self.name = 'stamina'
        self.color = colors.bar_stamina_filled
        self.stamina_per_turn = 5

    def on_turn_end(self) -> None:
        self.gain(self.stamina_per_turn)


class Mana(Resource):
    def __init__(self):
        super().__init__(max_amount=10, current_amount=10)

        self.name = 'mana'
        self.color = colors.bar_mana_filled

    def on_turn_end(self) -> None:
        self.gain(self.parent.magic // 2)
