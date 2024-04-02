from __future__ import annotations

from typing import TYPE_CHECKING

import colors

if TYPE_CHECKING:
    from components.fighter import Fighter

from components.base_component import BaseComponent


class StatusEffect(BaseComponent):
    parent: Fighter

    def __init__(self, caster: Fighter, target: Fighter, duration: int) -> None:
        self.parent = target
        self.caster = caster
        self.duration = duration

    def on_apply(self) -> None:
        pass

    def per_turn(self) -> None:
        self.duration -= 1

    def on_remove(self) -> None:
        pass


class Bleed(StatusEffect):
    def __init__(self, caster: Fighter, target: Fighter, amount: int, duration: int) -> None:
        super().__init__(caster=caster, target=target, duration=duration)
        self.amount = amount

    def per_turn(self) -> None:
        super().per_turn()
        self.parent.take_damage(self.amount)
        self.engine.message_log.add_message(
            text=f"{self.parent.name.capitalize()} bleeds for {self.amount} damage!",
            fg=colors.player_atk
        )
