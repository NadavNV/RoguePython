from __future__ import annotations

from typing import List, TYPE_CHECKING

from components.base_component import BaseComponent

if TYPE_CHECKING:
    from components.fighter import Fighter


class Level(BaseComponent):
    parent: Fighter

    def __init__(
            self,
            current_level: int = 1,
            current_xp: int = 0,
            level_up_base: int = 0,
            level_up_factor: int = 150,
            xp_given: int = 0,
    ):
        self.current_level = current_level
        self.current_xp = current_xp
        self.level_up_base = level_up_base
        self.level_up_factor = level_up_factor
        self.xp_given = xp_given

    @property
    def experience_to_next_level(self) -> int:
        return self.level_up_base + self.current_level * self.level_up_factor

    @property
    def requires_level_up(self) -> bool:
        return self.current_xp >= self.experience_to_next_level

    def add_xp(self, xp: int) -> None:
        if xp == 0 or self.level_up_base == 0:
            return

        self.current_xp += xp

        self.engine.message_log.add_message(f"You gain {xp} experience points.")

        if self.requires_level_up:
            self.engine.message_log.add_message(
                f"You advance to level {self.current_level + 1}"
            )

    def increase_level(self, stats: List[str]) -> None:
        self.current_xp -= self.experience_to_next_level
        self.current_level += 1
        for stat in stats:
            self.increase_stat(stat)

        fighter = self.parent
        fighter.proficiency = 1 + self.current_level % 4
        fighter.roll_hitpoints()

    def increase_stat(self, stat: str):
        if stat == "Strength":
            self.increase_strength()
        elif stat == "Perseverance":
            self.increase_perseverance()
        elif stat == "Agility":
            self.increase_agility()
        elif stat == "Magic":
            self.increase_magic()

    def increase_perseverance(self) -> None:
        self.parent.perseverance += 1
        amount = self.parent.perseverance * self.current_level
        self.parent.max_hp += amount
        self.parent.hp += amount

    def increase_strength(self) -> None:
        self.parent.strength += 1

    def increase_agility(self) -> None:
        self.parent.agility += 1

    def increase_magic(self) -> None:
        self.parent.magic += 1

    @property
    def proficiency(self) -> int:
        return 1 + self.current_level // 4
