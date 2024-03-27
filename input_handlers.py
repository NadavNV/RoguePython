from __future__ import annotations

import os.path
import time
import re
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING, Union

import numpy as np
import tcod
from tcod import libtcodpy
import textwrap
import traceback

import actions
import render_functions
from actions import (
    Action,
    BumpAction,
    PickupAction,
    WaitAction,
    TargetedAbility,
    ItemAction,
)
from components.equippable import Weapon
import colors
import exceptions
from equipment_slots import EquipmentSlot
from equipment_types import EquipmentType
from fighter_classes import FighterClass

if TYPE_CHECKING:
    from entity import Item
    from engine import Engine

MOVE_KEYS = {
    # Numpad keys
    tcod.event.KeySym.KP_1: (-1, 1),
    tcod.event.KeySym.KP_2: (0, 1),
    tcod.event.KeySym.KP_3: (1, 1),
    tcod.event.KeySym.KP_4: (-1, 0),
    tcod.event.KeySym.KP_6: (1, 0),
    tcod.event.KeySym.KP_7: (-1, -1),
    tcod.event.KeySym.KP_8: (0, -1),
    tcod.event.KeySym.KP_9: (1, -1),
    # Arrow keys
    tcod.event.KeySym.UP: (0, -1),
    tcod.event.KeySym.DOWN: (0, 1),
    tcod.event.KeySym.LEFT: (-1, 0),
    tcod.event.KeySym.RIGHT: (1, 0),
}

CURSOR_Y_KEYS = {
    tcod.event.KeySym.UP: -1,
    tcod.event.KeySym.KP_8: -1,
    tcod.event.KeySym.DOWN: 1,
    tcod.event.KeySym.KP_2: 1,
    tcod.event.KeySym.PAGEUP: -10,
    tcod.event.KeySym.PAGEDOWN: 10,
}

CURSOR_X_KEYS = {
    tcod.event.KeySym.LEFT: -1,
    tcod.event.KeySym.KP_4: -1,
    tcod.event.KeySym.RIGHT: 1,
    tcod.event.KeySym.KP_6: 1,
}

WAIT_KEYS = {
    tcod.event.KeySym.KP_5,
}

CONFIRM_KEYS = {
    tcod.event.KeySym.RETURN,
    tcod.event.KeySym.KP_ENTER,
}

SPAM_KEYS = {
    tcod.event.KeySym.s,
    tcod.event.KeySym.p,
    tcod.event.KeySym.a,
    tcod.event.KeySym.m,
}

TIME_BETWEEN_LETTERS = 1 / 16.0

ActionOrHandler = Union[Action, "BaseEventHandler"]
"""En event handler return value which can trigger an action or switch active handlers.

If a handler is returned then it will become the active handler for future events.
If an action is returned it will be attempted and if it's valid then
MainGameEventHandler will become the active handler."""


class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle an event and return the next active event handler."""
        state = self.dispatch(event)
        if isinstance(state, BaseEventHandler):
            return state
        assert not isinstance(state, Action), f"{self!r} can not handle actions."
        return self

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        raise NotImplementedError()

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()


class PopupMessage(BaseEventHandler):
    """Display a popup text window."""

    def __init__(self, parent_handler: BaseEventHandler, text: str):
        self.parent = parent_handler
        self.text = text

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        """Render the parent and dim the result, then print the message on top."""
        self.parent.on_render(console)
        console.rgb["fg"] //= 2
        console.rgb["bg"] //= 2

        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER,
        )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        """Any key returns to the parent handler."""
        return self.parent


class EventHandler(BaseEventHandler):
    def __init__(self, engine: Engine):
        self.engine = engine

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle events for input handlers with an engine."""
        try:
            action_or_state = self.dispatch(event)
            if isinstance(action_or_state, BaseEventHandler):
                return action_or_state
            if self.handle_action(action_or_state):
                # A valid action was performed.
                if not self.engine.player.is_alive:
                    print("Player is dead.")
                    # The player was killed some time during or after the action
                    return GameOverEventHandler(self.engine)
                elif self.engine.in_combat:
                    if not self.engine.active_enemies.is_alive:
                        self.engine.game_map.entities.remove(self.engine.active_enemies)
                        self.engine.in_combat = False
                        return LootEventHandler(engine=self.engine, parent=MainGameEventHandler(self.engine))
                    else:
                        return CombatEventHandler(self.engine)
                else:
                    return MainGameEventHandler(self.engine)  # Return to the main handler.
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(text=exc.args[0], fg=colors.impossible)
        return self

    def handle_action(self, action: Optional[Action]) -> bool:
        """Handle actions returned from event methods.

        Returns True if the action will advance a turn.
        """
        if action is None:
            return False

        try:
            action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], colors.impossible)
            return False  # Skip enemy turn on exceptions.

        self.engine.handle_enemy_turns()

        self.engine.update_fov()
        return True

    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if self.engine.game_map.in_bounds(event.position.x, event.position.y):
            self.engine.mouse_location = event.position.x, event.position.y

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        self.engine.render(console)
        if self.engine.player.fighters[0].level.requires_level_up:
            return LevelUpEventHandler(self.engine, parent=self)
        if self.engine.active_trader is not None:
            return TraderEventHandler(self.engine, MainGameEventHandler(self.engine))
        return self


class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""

    def __init__(self, engine: Engine, parent: EventHandler):
        super().__init__(engine)
        self.parent = parent

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """By default, any key exits this input handler."""
        if event.sym in {  # Ignore modifier keys.
            tcod.event.KeySym.LSHIFT,
            tcod.event.KeySym.RSHIFT,
            tcod.event.KeySym.LCTRL,
            tcod.event.KeySym.RCTRL,
            tcod.event.KeySym.LALT,
            tcod.event.KeySym.RALT,
        }:
            return None
        return self.on_exit()

    def ev_mousebuttondown(
            self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """By default, any mouse click exits this input handler."""
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        """Called when the user is trying to exit or cancel an action.

        By default, this returns to the main event handler.
        """
        return self.parent


class CharacterScreenEventHandler(AskUserEventHandler):
    TITLE = "Character Information"

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        super().on_render(console)
        console.rgb["fg"] //= 2
        console.rgb["bg"] //= 2

        player = self.engine.player[0]

        width = len(self.TITLE) + 4

        x = console.width // 2 - width
        y = 1

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=11,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        console.print_box(
            x=x,
            y=y,
            width=width,
            height=1,
            string=f"┤{self.TITLE}├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        console.print(x=x + 1, y=y + 1, string="Strength:")

        if player.equipment.strength_bonus > 0:
            text_color = colors.buff
        elif player.equipment.strength_bonus < 0:
            text_color = colors.debuff
        else:
            text_color = colors.white

        console.print(
            x=x + 15,
            y=y + 1,
            string=f"{player.strength + player.equipment.strength_bonus}",
            fg=text_color,
            bg=colors.black,
        )

        console.print(
            x=x + 19,
            y=y + 1,
            string=f"{(player.strength + player.equipment.strength_bonus) // 2:+}",
            fg=colors.white,
            bg=colors.black,
        )

        console.print(x=x + 1, y=y + 2, string="Perseverance:")

        if player.equipment.perseverance_bonus > 0:
            text_color = colors.buff
        elif player.equipment.perseverance_bonus < 0:
            text_color = colors.debuff
        else:
            text_color = colors.white

        console.print(
            x=x + 15,
            y=y + 2,
            string=f"{player.perseverance + player.equipment.perseverance_bonus}",
            fg=text_color,
            bg=colors.black,
        )

        console.print(
            x=x + 19,
            y=y + 2,
            string=f"{(player.perseverance + player.equipment.perseverance_bonus) // 2:+}",
            fg=colors.white,
            bg=colors.black,
        )

        console.print(x=x + 1, y=y + 3, string="Agility:")

        if player.equipment.agility_bonus > 0:
            text_color = colors.buff
        elif player.equipment.agility_bonus < 0:
            text_color = colors.debuff
        else:
            text_color = colors.white

        console.print(
            x=x + 15,
            y=y + 3,
            string=f"{player.agility + player.equipment.agility_bonus}",
            fg=text_color,
            bg=colors.black,
        )

        console.print(
            x=x + 19,
            y=y + 3,
            string=f"{(player.agility + player.equipment.agility_bonus) // 2:+}",
            fg=colors.white,
            bg=colors.black,
        )

        console.print(x=x + 1, y=y + 4, string="Magic:")

        if player.equipment.magic_bonus > 0:
            text_color = colors.buff
        elif player.equipment.magic_bonus < 0:
            text_color = colors.debuff
        else:
            text_color = colors.white

        console.print(
            x=x + 15,
            y=y + 4,
            string=f"{player.magic + player.equipment.magic_bonus}",
            fg=text_color,
            bg=colors.black,
        )

        console.print(
            x=x + 19,
            y=y + 4,
            string=f"{(player.magic + player.equipment.magic_bonus) // 2:+}",
            fg=colors.white,
            bg=colors.black,
        )

        console.print(
            x=x + 1, y=y + 6, string=f"Level: {player.level.current_level}"
        )
        console.print(
            x=x + 1, y=y + 7, string=f"XP: {player.level.current_xp}"
        )
        console.print(
            x=x + 1,
            y=y + 8,
            string=f"XP for next Level: {player.level.experience_to_next_level}",
        )
        console.print(
            x=x + 1, y=y + 9, string=f"Proficiency Bonus: {player.level.proficiency}",
        )

        # Longest line in this window
        width = len(f"Mainhand Attack Bonus: {player.mainhand_attack_bonus:+}") + 2

        x = console.width // 2
        y = 1

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=14,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        console.print_box(
            x=x,
            y=y,
            width=width,
            height=1,
            string=f"┤Equipment├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        equipment = player.equipment.list_equipped_items()
        for i in range(len(equipment)):
            console.print(
                x=x + 1,
                y=y + 1 + i,
                string=equipment[i],
                fg=colors.white,
                bg=colors.black
            )

        console.print(
            x=x + 1,
            y=y + len(equipment) + 3,
            string=f"Mainhand Attack Bonus: {player.equipment.mainhand_attack_bonus:+}",
            fg=colors.white,
            bg=colors.black
        )

        console.print(
            x=x + 1,
            y=y + len(equipment) + 4,
            string=f"Mainhand Damage: {player.equipment.mainhand_min_damage} - {player.equipment.mainhand_max_damage}",
            fg=colors.white,
            bg=colors.black
        )

        console.print(
            x=x + 1,
            y=y + len(equipment) + 5,
            string=f"Offhand Attack Bonus: {player.equipment.offhand_attack_bonus:+}",
            fg=colors.white,
            bg=colors.black
        )

        console.print(
            x=x + 1,
            y=y + len(equipment) + 6,
            string=f"Offhand Damage: {player.equipment.offhand_min_damage} - {player.equipment.offhand_max_damage}",
            fg=colors.white,
            bg=colors.black
        )

        return self


class LevelUpEventHandler(AskUserEventHandler):
    TITLE = "Level Up"
    WINDOW_WIDTH = len('perseverance') * 3 + 6
    WINDOW_HEIGHT = 12

    def __init__(self, engine: Engine, parent: EventHandler):
        super().__init__(engine=engine, parent=parent)
        self.stats = []

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        super().on_render(console)

        x = (console.width - self.WINDOW_WIDTH) // 2

        console.draw_frame(
            x=x,
            y=1,
            width=self.WINDOW_WIDTH,
            height=self.WINDOW_HEIGHT,
            clear=True,
            fg=colors.white,
            bg=colors.black,
        )
        console.print_box(
            x=x,
            y=1,
            width=self.WINDOW_WIDTH,
            height=1,
            string=f"┤{self.TITLE}├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        console.print(x=x + 1, y=2, string="Congratulations! You level up!")
        console.print(x=x + 1, y=3, string="Select attributes to increase.")

        console.print(
            x=x + 1,
            y=5,
            string=f"{"S - Strength":<17}Esc - Cancel",
        )
        console.print(
            x=x + 1,
            y=6,
            string=f"{"P - Perseverance":<17}Enter - Confirm",
        )
        console.print(
            x=x + 1,
            y=7,
            string="A - Agility",
        )

        console.print(
            x=x + 1,
            y=8,
            string="M - Magic",
        )

        console.print(
            x=x + 1,
            y=10,
            string=f"[{" ":<12},{" ":<12},{" ":<12}]"
        )

        for i in range(len(self.stats)):
            console.print_box(
                x=x + 2 + i * (len('perseverance') + 1),
                y=10,
                width=len('perseverance'),
                height=1,
                string=self.stats[i],
                fg=colors.white,
                bg=colors.black,
                alignment=libtcodpy.CENTER
            )

        width = len("┤Current Attributes├") + 4
        height = 8
        x = x - width-1
        y = 1

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            fg=colors.white,
            bg=colors.black
        )
        console.print_box(
            x=x,
            y=y,
            width=width,
            height=1,
            string="┤Current Attributes├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER,
        )

        console.print_box(
            x=x,
            y=y + 2,
            width=width,
            height=1,
            string=f"S: {self.engine.player[0].strength}",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER,
        )
        console.print_box(
            x=x,
            y=y + 3,
            width=width,
            height=1,
            string=f"P: {self.engine.player[0].perseverance}",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER,
        )
        console.print_box(
            x=x,
            y=y + 4,
            width=width,
            height=1,
            string=f"A: {self.engine.player[0].agility}",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER,
        )
        console.print_box(
            x=x,
            y=y + 5,
            width=width,
            height=1,
            string=f"M: {self.engine.player[0].magic}",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER,
        )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym

        if key == tcod.event.KeySym.ESCAPE:
            if len(self.stats) > 0:
                self.stats.pop(-1)
        elif key in SPAM_KEYS:
            if len(self.stats) >= 3:
                self.engine.message_log.add_message(text="Can only increase 3 attributes.", fg=colors.invalid)
            else:
                if key == tcod.event.KeySym.s:
                    self.stats.append("Strength")
                elif key == tcod.event.KeySym.p:
                    self.stats.append("Perseverance")
                elif key == tcod.event.KeySym.a:
                    self.stats.append("Agility")
                elif key == tcod.event.KeySym.m:
                    self.stats.append("Magic")

        elif key in CONFIRM_KEYS:
            if len(self.stats) < 3:
                self.engine.message_log.add_message(
                    text="You must choose 3 attributes to increase..",
                    fg=colors.invalid
                )
            else:
                self.engine.player[0].level.increase_level(self.stats)
                return self.parent

        return self

    def ev_mousebuttondown(
            self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """Don't allow the player to click to exit the menu, like normal."""
        return None


class InventoryEventHandler(AskUserEventHandler):
    """This handler lets the user select an item.

    What happens then depends on the subclass.
    """

    TITLE = "<missing title>"

    def __init__(self, engine: Engine, parent: EventHandler):
        super().__init__(engine, parent=parent)
        self.cursor = 0

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        """Render an inventory menu, which displays the items in the inventory, and the letter to select them.
        Will move to a different position based on where the player is located, so the player can always see where
        they are.
        """
        super().on_render(console)
        number_of_items_in_inventory = len(self.engine.player.inventory.list_items())

        height = number_of_items_in_inventory + 4

        if height <= 5:
            height = 5

        y = 0

        width = len(self.TITLE) + 4
        if number_of_items_in_inventory != 0:
            width = max(max([len(line) for line in self.engine.player.inventory.list_items()]) + 7, width)

        x = console.width // 2 - width

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        console.print_box(
            x=x,
            y=y,
            width=width,
            height=1,
            string=f"┤{self.TITLE}├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        if number_of_items_in_inventory > 0:
            print_menu(
                console=console,
                items=[line for line in self.engine.player.inventory.list_items()],
                x=x + 1,
                y=y + 1,
                cursor=self.cursor,
            )
            console.draw_frame(
                x=console.width // 2 + 1,
                y=0,
                width=console.width // 4,
                height=max(height, console.height // 3),
                fg=colors.white,
                bg=colors.black
            )
            console.print(
                x=console.width // 2 + 2,
                y=1,
                string=wrap(
                    text=self.engine.player.inventory.items[self.cursor][0].description,
                    width=console.width // 4 - 2
                ),
                fg=colors.white,
                bg=colors.black
            )

        else:
            console.print(x + 1, y + 1, "(Empty)")

        console.print(
            x=x + 1,
            y=y + height - 2,
            string=f"Gold: {self.engine.player.inventory.gold}",
            fg=colors.white,
            bg=colors.black
        )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index][0]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", colors.invalid)
                return None
            return self.on_item_selected(selected_item)
        elif key in (tcod.event.KeySym.UP, tcod.event.KeySym.DOWN) and len(player.inventory.items) != 0:
            adjust = CURSOR_Y_KEYS[key]
            if adjust < 0 and self.cursor == 0:
                self.cursor = len(player.inventory.items) - 1
            elif adjust > 0 and self.cursor == len(player.inventory.items) - 1:
                self.cursor = 0
            else:
                self.cursor += adjust
        elif key in CONFIRM_KEYS:
            try:
                selected_item = player.inventory.items[self.cursor][0]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", colors.invalid)
                return None
            return self.on_item_selected(selected_item)
        elif key == tcod.event.KeySym.ESCAPE:
            return self.parent
        return None  # super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Called when the user selects a valid item."""
        raise NotImplementedError()


class InventoryActivateHandler(InventoryEventHandler):
    """Handle using an inventory item."""

    TITLE = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        player = self.engine.player.fighters[0]
        if item.consumable:
            # Return the action for the selected item.
            return item.consumable.get_action(self.engine.player.fighters[0])
        elif item.equippable:
            if item.equippable.equipment_type == EquipmentType.WEAPON:

                if not player.equipment.item_is_equipped(EquipmentSlot.MAINHAND):
                    return actions.EquipAction(player, item=item, slot=EquipmentSlot.MAINHAND)
                elif isinstance(item.equippable, Weapon) and (
                        not item.equippable.offhand
                        or player.equipment.items[EquipmentSlot.MAINHAND].two_handed
                ):
                    player.equipment.unequip_from_slot(EquipmentSlot.MAINHAND, add_message=True)
                    return actions.EquipAction(player, item=item, slot=EquipmentSlot.MAINHAND)
                elif player.equipment.items[EquipmentSlot.OFFHAND] is None:
                    return actions.EquipAction(player, item=item, slot=EquipmentSlot.OFFHAND)
                else:
                    return EquipWeaponEventHandler(self.engine, item, self)
            elif item.equippable.equipment_type == EquipmentType.TRINKET:
                if not player.equipment.item_is_equipped(EquipmentSlot.TRINKET1):
                    return actions.EquipAction(player, item, EquipmentSlot.TRINKET1)
                elif not player.equipment.item_is_equipped(EquipmentSlot.TRINKET2):
                    return actions.EquipAction(player, item, EquipmentSlot.TRINKET2)
                return EquipTrinketEventHandler(self.engine, item, self)
            else:
                slot = EquipmentSlot(item.equippable.equipment_type)
                return actions.EquipAction(player, item=item, slot=slot)
        else:
            return None


class InventoryDropHandler(InventoryEventHandler):
    """Handle dropping an inventory item."""

    TITLE = "Select an item to drop"

    def on_item_selected(self, item: Item) -> Optional[Action]:
        """Drop this item."""
        return actions.DropItem(self.engine.player, item)


class SelectIndexHandler(AskUserEventHandler):
    """Handles asking the user for an index on the map."""

    def __init__(self, engine: Engine, parent: EventHandler):
        """Sets the curser to the player when this handler is constructed."""
        super().__init__(engine, parent=parent)
        player = self.engine.player
        engine.mouse_location = player.x, player.y

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        """Highlight the tile under the cursor."""
        super().on_render(console)
        x, y = self.engine.mouse_location
        console.rgb["bg"][x, y] = colors.white
        console.rgb["fg"][x, y] = colors.black

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """Check for key movement or confirmation keys."""
        key = event.sym
        if key in MOVE_KEYS:
            modifier = 1  # Holding modifier keys will speed up key movement.
            if event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
                modifier *= 5
            if event.mod & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
                modifier *= 10
            if event.mod & (tcod.event.KMOD_LALT | tcod.event.KMOD_RALT):
                modifier *= 20

            x, y = self.engine.mouse_location
            dx, dy = MOVE_KEYS[key]
            x += dx * modifier
            y += dy * modifier
            # Clamp the cursor index to the map size.
            x = max(0, min(x, self.engine.game_map.width - 1))
            y = max(0, min(y, self.engine.game_map.height - 1))
            self.engine.mouse_location = x, y
            return None
        elif key in CONFIRM_KEYS:
            return self.on_index_selected(*self.engine.mouse_location)
        return super().ev_keydown(event)

    def ev_mousebuttondown(
            self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """Left click confirms a selection."""
        if self.engine.game_map.in_bounds(*event.position):
            if event.button == 1:
                return self.on_index_selected(*event.position)
        return super().ev_mousebuttondown(event)

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Called when an index is selected."""
        raise NotImplementedError()


class LookHandler(SelectIndexHandler):
    """Let the player look around using the keyboard."""

    def on_index_selected(self, x: int, y: int) -> MainGameEventHandler:
        """Return to main handler."""
        return MainGameEventHandler(self.engine)


class SingleRangedAttackHandler(SelectIndexHandler):
    """Handles targeting a single enemy. Only the enemy selected will be affected."""

    def __init__(
            self, engine: Engine, callback: Callable[[Tuple[int, int]], Optional[Action]], parent: EventHandler
    ):
        super().__init__(engine, parent)

        self.callback = callback

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))


class AreaRangedAttackHandler(SelectIndexHandler):
    """Handles targeting an area within a given radius. Any entity within the area will be affected."""

    def __init__(
            self,
            engine: Engine,
            radius: int,
            callback: Callable[[Tuple[int, int]], Optional[Action]],
            parent: EventHandler,
    ):
        super().__init__(engine, parent)

        self.radius = radius
        self.callback = callback

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        """Highlight the tile under the cursor."""
        super().on_render(console)

        x, y = self.engine.mouse_location

        # Draw a rectangle around the targeted area, so the player can see the affected tiles.
        console.draw_frame(
            x=x - self.radius - 1,
            y=y - self.radius - 1,
            width=self.radius ** 2,
            height=self.radius ** 2,
            fg=colors.red,
            clear=False,
        )

        return self

    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))


class MainGameEventHandler(EventHandler):

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        action: Optional[Action] = None

        key = event.sym
        modifier = event.mod

        player = self.engine.player

        if key == tcod.event.KeySym.PERIOD and modifier & (
                tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT
        ):
            return actions.TakeStairsAction(player)

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            action = BumpAction(player, dx, dy)
        elif key in WAIT_KEYS:
            action = WaitAction(player)
        elif key == tcod.event.KeySym.ESCAPE:
            raise SystemExit()
        elif key == tcod.event.KeySym.v:
            return HistoryViewer(self.engine)

        elif key == tcod.event.KeySym.g:
            action = PickupAction(player)

        elif key == tcod.event.KeySym.i:
            return InventoryActivateHandler(self.engine, parent=self)
        elif key == tcod.event.KeySym.d:
            return InventoryDropHandler(self.engine, parent=self)
        elif key == tcod.event.KeySym.c:
            return CharacterScreenEventHandler(self.engine, parent=self)
        elif key == tcod.event.KeySym.SLASH:
            return LookHandler(self.engine, parent=self)
        elif key == tcod.event.KeySym.u:
            return UnequipEventHandler(self.engine, parent=self)

        # No valid key was pressed
        return action


class GameOverEventHandler(EventHandler):
    @staticmethod
    def on_quit():
        """Handle exiting out of a finished game."""
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")  # Deletes the active save file.
        raise exceptions.QuitWithoutSaving()  # Avoid saving a finished game.

    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.on_quit()

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        self.engine.in_combat = False
        MainGameEventHandler(self.engine).on_render(console)
        return self


class HistoryViewer(EventHandler):
    """Print the history on a larger window which can be navigated."""

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.log_length = len(engine.message_log.messages)
        self.cursor = self.log_length - 1

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        super().on_render(console)  # Draw the main state as the background.

        log_console = tcod.console.Console(console.width - 6, console.height - 6)

        # Draw a frame with a custom banner title.
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(
            0, 0, log_console.width, 1, "┤Message history├", alignment=libtcodpy.CENTER
        )

        # Render the message log using the cursor parameters
        self.engine.message_log.render_messages(
            log_console,
            1,
            1,
            log_console.width - 2,
            log_console.height - 2,
            self.engine.message_log.messages[: self.cursor + 1],
        )
        log_console.blit(console, 3, 3)

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[MainGameEventHandler]:
        # Fancy conditional movement to make it feel right.
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0 and self.cursor == 0:
                # Only move from the top to the bottom when you're on the edge.
                self.cursor = self.log_length - 1
            elif adjust > 0 and self.cursor == self.log_length - 1:
                self.cursor = 0
            else:
                # Otherwise move while staying clamped to the bounds of the history log.
                self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
        elif event.sym == tcod.event.KeySym.HOME:
            self.cursor = 0  # Move directly to the top message.
        elif event.sym == tcod.event.KeySym.END:
            self.cursor = self.log_length - 1  # Move directly to the last message.
        else:  # Any other key moves back to the main game state.
            return MainGameEventHandler(self.engine)
        return None


def print_menu(console: tcod.console.Console, items: List[str], x: int, y: int, cursor: int) -> None:
    """Prints a menu of choices to the given 'console' at location 'x', 'y'.

    'items' is the list of menu items, 'cursor' is the currently selected item, which
    will be printed differently.
    """
    for i, item in enumerate(items):
        if i == cursor:
            fg = colors.black
            bg = colors.white
        else:
            fg = colors.white
            bg = colors.black

        key = chr(ord('a') + i)
        console.print(x=x, y=y + i, fg=fg, bg=bg, string=f"({key}) {item}")


class CutsceneEventHandler(BaseEventHandler):
    text: str
    time_to_hold: float
    cutscene_skip: bool

    def __init__(self):
        self.chars_printed = 0
        self.start = time.time()
        self.now = self.start
        self.cutscene_skip = False

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        self.cutscene_skip = True

    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> None:
        self.cutscene_skip = True

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise exceptions.QuitWithoutSaving()


def wrap(text: str, width: int):
    """"Returns 'text' split into lines up to the given width"""
    # Taken from https://stackoverflow.com/questions/1166317/python-textwrap-library-how-to-preserve-line-breaks
    return '\n'.join(['\n'.join(textwrap.wrap(line,
                                              width,
                                              break_long_words=False,
                                              replace_whitespace=False
                                              )
                                ) for line in text.splitlines()])


class IntroEventHandler(CutsceneEventHandler):

    def __init__(self):
        super().__init__()
        self.time_to_hold = 5  # Seconds to wait after printing the whole message.
        self.text = ("A sudden jolt wakes you from your sleep. Your cage seems to have fallen, and the lid has come" +
                     " loose." + "\n\nYou are free.\n\n" + "You are a python. You've spent your whole life in this " +
                     "laboratory, being experimented on by an army of insane scientists. You've known nothing but" +
                     " agony your  whole life, but those experiments also granted you great strength, two human-like " +
                     "arms, and even a hint  of something that can only be described as magic." + "\n" + "Now is your" +
                     " chance. Now is the time to use these abilities to exact your vengeance on everyone in the " +
                     "building. It's time to escape the role you were given.""" + "\n\nIt's time to go ROGUE, PYTHON.")
        self.total_length = len(self.text)

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        console.clear()
        self.now = time.time()

        x = console.width // 4
        y = console.height // 4

        if self.cutscene_skip:
            self.chars_printed = len(self.text)
            self.cutscene_skip = False

        end = self.chars_printed
        self.text = wrap(self.text, console.width // 2)

        for line in self.text.splitlines():
            if end > len(line):
                console.print(x=x, y=y, string=line, fg=colors.white, bg=colors.black)
                end -= len(line)
                x = console.width // 4
                y += 1
            elif end > 0:
                console.print(x=x, y=y, string=line[:end], fg=colors.white, bg=colors.black)
                end = 0
            elif len(line) == 0:
                y += 1
            else:
                break

        if self.chars_printed < len(self.text) and self.now - self.start > TIME_BETWEEN_LETTERS:
            self.start = self.now
            self.chars_printed += 1
        if self.chars_printed >= self.total_length and self.now - self.start > self.time_to_hold:
            return ClassSelectEventHandler()
        else:
            return self

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        self.dispatch(event)
        if self.chars_printed >= self.total_length:
            if self.cutscene_skip or self.now - self.start > self.time_to_hold:
                return ClassSelectEventHandler()
        return self


class EquipmentEventHandler(AskUserEventHandler):
    """This handler lets the user select an equipment slot.

    What happens then depends on the subclass.
    """

    TITLE = "<missing title>"

    def __init__(self, engine: Engine, parent: EventHandler):
        super().__init__(engine, parent)
        self.cursor = 0

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        """Render an inventory menu, which displays the items in the inventory, and the letter to select them.
        Will move to a different position based on where the player is located, so the player can always see where
        they are.
        """
        super().on_render(console)

        height = len(EquipmentSlot) + 2

        if height <= 3:
            height = 3

        if self.engine.player.x <= self.engine.game_map.width // 2 - 10:
            x = self.engine.game_map.width // 2
        else:
            x = 0

        y = 0

        width = max(
            max([len(line) for line in self.engine.player.fighters[0].equipment.list_equipped_items()]) + 4,
            len(self.TITLE) + 4
        )

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            clear=True,
            fg=colors.white,
            bg=colors.black,
        )
        console.print_box(
            x=x,
            y=y,
            width=width,
            height=1,
            string=f"┤{self.TITLE}├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        print_menu(
            console=console,
            items=[line for line in self.engine.player.fighters[0].equipment.list_equipped_items()],
            x=x + 1,
            y=y + 1,
            cursor=self.cursor,
        )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index < len(EquipmentSlot):
            try:
                selected_item = index
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", colors.invalid)
                return None
            return self.on_item_selected(selected_item)
        elif key in (tcod.event.KeySym.UP, tcod.event.KeySym.DOWN):
            adjust = CURSOR_Y_KEYS[key]
            if adjust < 0 and self.cursor == 0:
                self.cursor = len(EquipmentSlot) - 1
            elif adjust > 0 and self.cursor == len(EquipmentSlot) - 1:
                self.cursor = 0
            else:
                self.cursor += adjust
        elif key in CONFIRM_KEYS:
            try:
                selected_item = EquipmentSlot(self.cursor + 1)
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", colors.invalid)
                return None
            return self.on_item_selected(selected_item)
        elif key == tcod.event.KeySym.ESCAPE:
            return MainGameEventHandler(self.engine)
        return None

    def on_item_selected(self, slot: EquipmentSlot) -> Optional[ActionOrHandler]:
        """Called when the user selects a valid item."""
        raise NotImplementedError()


class UnequipEventHandler(EquipmentEventHandler):
    TITLE = "Select an item to unequip"

    def on_item_selected(self, slot: EquipmentSlot) -> Optional[ActionOrHandler]:
        item = self.engine.player.fighters[0].equipment.items[slot]
        if item is None:
            self.engine.message_log.add_message("Nothing to unequip.", colors.invalid)
            return self
        else:
            return actions.EquipAction(entity=self.engine.player, item=item.parent, slot=slot)


class ChooseSlotEventHandler(AskUserEventHandler):
    TITLE = "<missing title>"

    def __init__(self, engine: Engine, item: Item, parent: EventHandler):
        super().__init__(engine, parent)
        self.item = item
        self.cursor = 0

    def on_slot_selected(self, slot: EquipmentSlot) -> Optional[ActionOrHandler]:
        """Called when the user selects a slot."""
        raise NotImplementedError()

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        # Renders the previews UI but dimmed
        self.parent.on_render(console)
        console.rgb["fg"] //= 2
        console.rgb["bg"] //= 2

        return self


class EquipWeaponEventHandler(ChooseSlotEventHandler):
    TITLE = "Select weapon to replace"

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        player = self.engine.player.fighters[0]
        super().on_render(console)

        equipped_weapons = [
            player.equipment.items[EquipmentSlot.MAINHAND].name,
            player.equipment.items[EquipmentSlot.OFFHAND].name
        ]

        width = max(len(self.TITLE), len(equipped_weapons[0]), len(equipped_weapons[1])) + 2
        height = 4
        x = (console.width - width) // 2
        y = (console.height - height) // 2

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            clear=True,
            fg=colors.white,
            bg=colors.black,
        )
        console.print_box(
            x=x,
            y=y,
            width=width,
            height=1,
            string=f"┤{self.TITLE}├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        for i in range(2):
            if self.cursor == i:
                fg = (0, 0, 0)
                bg = (255, 255, 255)
            else:
                fg = (255, 255, 255)
                bg = (0, 0, 0)

            console.print(
                x=x + 1,
                y=y + 1 + i,
                string=equipped_weapons[i],
                fg=fg,
                bg=bg,
            )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        if key in (tcod.event.KeySym.DOWN, tcod.event.KeySym.UP):
            self.cursor = (self.cursor + CURSOR_Y_KEYS[key]) % 2
        elif key in CONFIRM_KEYS:
            if self.cursor == 0:
                slot = EquipmentSlot.MAINHAND
            else:
                slot = EquipmentSlot.OFFHAND
            return self.on_slot_selected(slot)
        elif key == tcod.event.KeySym.ESCAPE:
            return self.parent

    def on_slot_selected(self, slot: EquipmentSlot) -> Optional[ActionOrHandler]:
        self.engine.player.fighters[0].equipment.unequip_from_slot(slot, add_message=True)
        return actions.EquipAction(self.engine.player, self.item, slot)


class EquipTrinketEventHandler(ChooseSlotEventHandler):
    TITLE = "Select trinket to replace"

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        player = self.engine.player.fighters[0]
        super().on_render(console)

        equipped_trinkets = [
            player.equipment.items[EquipmentSlot.TRINKET1].name,
            player.equipment.items[EquipmentSlot.TRINKET2].name
        ]

        width = max(len(self.TITLE), len(equipped_trinkets[0]), len(equipped_trinkets[1])) + 2
        height = 4
        x = (console.width - width) // 2
        y = (console.height - height) // 2

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        console.print_box(
            x=x,
            y=y,
            width=width,
            height=1,
            string=f"┤{self.TITLE}├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        for i in range(2):
            if self.cursor == i:
                fg = (0, 0, 0)
                bg = (255, 255, 255)
            else:
                fg = (255, 255, 255)
                bg = (0, 0, 0)

            console.print(
                x=x + 1,
                y=y + 1 + i,
                string=equipped_trinkets[i],
                fg=fg,
                bg=bg,
            )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        if key in (tcod.event.KeySym.DOWN, tcod.event.KeySym.UP):
            self.cursor = (self.cursor + CURSOR_Y_KEYS[key]) % 2
        elif key in CONFIRM_KEYS:
            if self.cursor == 0:
                slot = EquipmentSlot.TRINKET1
            else:
                slot = EquipmentSlot.TRINKET2
            return self.on_slot_selected(slot)
        elif key == tcod.event.KeySym.ESCAPE:
            return self.parent

    def on_slot_selected(self, slot: EquipmentSlot) -> Optional[ActionOrHandler]:
        self.engine.player.fighters[0].equipment.unequip_from_slot(slot, add_message=True)
        return actions.EquipAction(self.engine.player, self.item, slot)


class ClassSelectEventHandler(BaseEventHandler):
    warrior_icon = "images/warrior_icon.png"
    rogue_icon = "images/rogue_icon.png"
    mage_icon = "images/mage_icon.png"

    def __init__(self):
        self.cursor = 1  # Start with Rogue highlighted

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:

        console.draw_frame(
            x=0,
            y=0,
            width=console.width,
            height=console.height * 2 // 3,
            fg=colors.white,
            bg=colors.black,
        )
        console.print_box(
            x=0,
            y=0,
            width=console.width,
            height=1,
            string=f"┤Choose a class├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        sprite = colors.image_to_rgb(ClassSelectEventHandler.warrior_icon)

        console.draw_semigraphics(
            sprite,
            x=console.width // 4 - console.width // 16,
            y=console.height // 8
        )

        sprite = colors.image_to_rgb(ClassSelectEventHandler.rogue_icon)

        console.draw_semigraphics(
            sprite,
            x=console.width // 2 - console.width // 16 + 1,
            y=console.height // 8
        )

        sprite = colors.image_to_rgb(ClassSelectEventHandler.mage_icon)

        console.draw_semigraphics(
            sprite,
            x=console.width * 3 // 4 - console.width // 16,
            y=console.height // 8
        )

        if self.cursor + 1 == FighterClass.WARRIOR.value:
            fg = (0, 0, 0)
            bg = (255, 255, 255)
        else:
            fg = (255, 255, 255)
            bg = (0, 0, 0)

        console.print(
            x=console.width // 4,
            y=console.height // 8 + console.width // 4 - 5,
            string='[W]arrior',
            fg=fg,
            bg=bg,
            alignment=libtcodpy.CENTER
        )

        if self.cursor + 1 == FighterClass.ROGUE.value:
            fg = (0, 0, 0)
            bg = (255, 255, 255)
        else:
            fg = (255, 255, 255)
            bg = (0, 0, 0)

        console.print(
            x=console.width // 2,
            y=console.height // 8 + console.width // 4 - 5,
            string='[R]ogue',
            fg=fg,
            bg=bg,
            alignment=libtcodpy.CENTER
        )

        if self.cursor + 1 == FighterClass.MAGE.value:
            fg = (0, 0, 0)
            bg = (255, 255, 255)
        else:
            fg = (255, 255, 255)
            bg = (0, 0, 0)

        console.print(
            x=console.width * 3 // 4,
            y=console.height // 8 + console.width // 4 - 5,
            string='[M]age',
            fg=fg,
            bg=bg,
            alignment=libtcodpy.CENTER
        )

        console.draw_frame(
            x=0,
            y=console.height * 2 // 3,
            height=console.height // 3,
            width=console.width,
            fg=(255, 255, 255),
            bg=(0, 0, 0)
        )
        console.print_box(
            x=0,
            y=console.height * 2 // 3,
            width=console.width,
            height=1,
            string=f"┤Class Description├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        class_descriptions = [
            ("The warrior prefers using brute strength in combat to vanquish their enemies. Being less agile than" +
             " most, they tend to use heavy armor and shields for protection. They are proficient with all " +
             "strength-based and finesse weapons, and they have abilities that can take down multiple enemies " +
             "at once.\n\nPREFERRED STAT: Strength.\n\nPROFICIENCIES: Swords, Axes, Maces."),
            ("The rogue is a cunning fighter, using their speed and a few nasty tricks to take down individual " +
             "enemies very quickly. They use their incredible agility to avoid incoming attacks and strike their " +
             "enemies where they are weakest. They are proficient with agility-based and finesse weapons. " +
             "\n\nPREFERRED STAT: Agility.\n\nPROFICIENCIES: Short Sword, Dagger, Rapier, Scimitar."),
            ("Wielders of powerful arcane forces, the mage their spells to control the battlefield and " +
             "dispose of their enemies. They can freeze their foes, set the aflame, or strike them with " +
             "lightning. They need to spend mana to cast their spells, but they are also more proficient than " +
             "others at using scrolls to cast spells.\n\nPREFERRED STAT: Magic.\n\nPROFICIENCIES: Wands, Staves," +
             " Scrolls.")
        ]
        console.print(
            x=1,
            y=console.height * 2 // 3 + 2,
            string=wrap(class_descriptions[self.cursor], console.width - 2),
            fg=(255, 255, 255),
            bg=(0, 0, 0)
        )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        from setup_game import new_game
        key = event.sym
        if key in CURSOR_X_KEYS:
            self.cursor = (self.cursor + CURSOR_X_KEYS[key]) % len(FighterClass)
        elif key in CONFIRM_KEYS:
            return MainGameEventHandler(new_game(FighterClass(self.cursor + 1)))
        elif key == tcod.event.KeySym.ESCAPE:
            return MainMenu()
        elif key == tcod.event.KeySym.w:
            return MainGameEventHandler(new_game(FighterClass.WARRIOR))
        elif key == tcod.event.KeySym.r:
            return MainGameEventHandler(new_game(FighterClass.ROGUE))
        elif key == tcod.event.KeySym.m:
            return MainGameEventHandler(new_game(FighterClass.MAGE))


class MainMenu(BaseEventHandler):
    """Handle the main menu rendering and input."""

    # Load the background image and remove the alpha channel.
    background_image = colors.image_to_rgb('images/menu_background.png')

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        """Render the main menu on a background image."""
        console.draw_semigraphics(MainMenu.background_image, 0, 0)

        menu_width = 24
        for i, text in enumerate(
                ["[N] Play a new game", "[C] Continue last game", "[Q] Quit"]
        ):
            console.print(
                console.width // 2,
                console.height // 2 - 2 + i,
                text.ljust(menu_width),
                fg=colors.black,
                bg=colors.white,
                alignment=libtcodpy.CENTER,
                bg_blend=libtcodpy.BKGND_ALPHA(64),
            )

        return self

    def ev_keydown(
            self, event: tcod.event.KeyDown
    ) -> Optional[BaseEventHandler]:
        from setup_game import load_game
        if event.sym in (tcod.event.KeySym.q, tcod.event.KeySym.ESCAPE):
            raise SystemExit()
        elif event.sym == tcod.event.KeySym.c:
            try:
                engine = load_game("savegame.sav")
                if engine.in_combat:
                    return CombatEventHandler(engine)
                else:
                    return MainGameEventHandler(engine)
            except FileNotFoundError:
                return PopupMessage(self, "No saved game to load.")
            except Exception as exc:
                traceback.print_exc()  # Print to stderr.
                return PopupMessage(self, f"Failed to load save:\n{exc}")
        elif event.sym == tcod.event.KeySym.n:
            return IntroEventHandler()

        return None


class CombatEventHandler(EventHandler):
    cursor: np.ndarray = np.array([0, 0])

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.cursor = np.array([0, 0])

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        super().on_render(console=console)
        render_functions.render_combat_ui(console=console, cursor=self.cursor)

        number_of_enemies = len(self.engine.active_enemies)

        frame_width = console.width * 2 // 3

        for i in range(number_of_enemies):
            render_functions.render_enemy(
                enemy=self.engine.active_enemies.fighters[i],
                console=console,
                x=frame_width * (i + 1) // (number_of_enemies + 1) - console.width // 16,
                y=console.height // 8,
            )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        key = event.sym

        if key in CURSOR_X_KEYS:
            self.cursor[0] = (self.cursor[0] + CURSOR_X_KEYS[key]) % 2
        elif key in CURSOR_Y_KEYS:
            self.cursor[1] = (self.cursor[1] + CURSOR_Y_KEYS[key]) % 2
        elif key == tcod.event.KeySym.ESCAPE:
            raise SystemExit()
        elif key in CONFIRM_KEYS:
            if np.array_equal(self.cursor, (0, 1)):
                return PopupMessage(parent_handler=self, text="You can't run, you don't have legs!")
            elif np.array_equal(self.cursor, (0, 0)):
                return SelectTargetEventHandler(
                    engine=self.engine,
                    action=self.engine.player.fighters[0].abilities[-1],  # Melee attack is always the least priority
                    parent=self,
                )
            elif np.array_equal(self.cursor, (1, 0)):
                return SelectAbilityEventHandler(self.engine, parent=self)
            elif np.array_equal(self.cursor, (1, 1)):
                return InventoryActivateHandler(self.engine, parent=self)


class SelectTargetEventHandler(AskUserEventHandler):

    def __init__(self, engine: Engine, parent: EventHandler, action: Union[TargetedAbility, ItemAction]):
        super().__init__(engine, parent)
        self.cursor = 0
        self.number_of_enemies = len(self.engine.active_enemies)
        self.engine.message_log.add_message(text="Select an enemy to target", stack=False)
        self.action = action

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        self.parent.on_render(console)

        frame_width = console.width * 2 // 3

        for i in range(self.number_of_enemies):
            if self.cursor == i:
                console.draw_frame(
                    x=frame_width * (i + 1) // (self.number_of_enemies + 1) - console.width // 16 - 1,
                    y=console.height // 8 - 1,
                    width=console.width // 8 + 2,
                    height=console.width // 4 + 2,
                    clear=False,
                    fg=colors.white,
                    bg=colors.black,
                )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym

        if key in CURSOR_X_KEYS:
            self.cursor = (self.cursor + CURSOR_X_KEYS[key]) % self.number_of_enemies
        elif key in CONFIRM_KEYS:
            try:
                target = self.engine.active_enemies[self.cursor]
                if target.is_alive:
                    self.action.target = target
                    return self.action
                else:
                    self.engine.message_log.add_message("Can't target dead enemies.", colors.invalid)
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", colors.invalid)
                return self
        elif key == tcod.event.KeySym.ESCAPE:
            return self.parent


class SelectAbilityEventHandler(AskUserEventHandler):
    TITLE = "Select an ability to use"

    def __init__(self, engine: Engine, parent: EventHandler):
        super().__init__(engine, parent)
        self.cursor = 0
        self.number_of_abilities = len(self.engine.player[0].abilities)

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        self.parent.on_render(console)
        console.rgb['fg'] //= 2
        console.rgb['bg'] //= 2

        self.number_of_abilities = len(self.engine.player[0].abilities)

        if self.number_of_abilities == 0:
            width = len(self.TITLE) + 4
            height = 3
        else:
            width = len(self.TITLE) + 4
            for ability in self.engine.player[0].abilities:
                width = max(width, len(ability.name) + 2)
            height = len(self.engine.player[0].abilities) + 2

        console.draw_frame(
            x=console.width // 4,
            y=console.height // 8,
            width=width,
            height=height,
            fg=colors.white,
            bg=colors.black
        )
        console.print_box(
            x=console.width // 4,
            y=console.height // 8,
            width=width,
            height=1,
            string=f"┤{self.TITLE}├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        for i, ability in enumerate(self.engine.player[0].abilities):
            if self.cursor == i:
                fg = colors.black
                bg = colors.white
            else:
                fg = colors.white
                bg = colors.black

            console.print(
                x=console.width // 4 + 1,
                y=console.height // 8 + 1 + i,
                string=ability.name,
                fg=fg,
                bg=bg
            )

        if self.number_of_abilities != 0:
            x = console.width // 4 + 1 + width
            y = console.height // 8
            # Show a description of the ability
            console.draw_frame(
                x=x,
                y=y,
                width=console.width // 4 + 2,
                height=max(height, console.height // 3),
                fg=colors.white,
                bg=colors.black
            )

            text = wrap(self.engine.player[0].abilities[self.cursor].description, console.width // 4)

            console.print(
                x=x + 1,
                y=y + 1,
                string=text,
                fg=colors.white,
                bg=colors.black
            )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym

        if key in CURSOR_Y_KEYS:
            self.cursor = (self.cursor + CURSOR_Y_KEYS[key]) % self.number_of_abilities
        elif key in CONFIRM_KEYS:
            ability = self.engine.player[0].abilities[self.cursor]
            if ability.cooldown_remaining <= 0:
                if isinstance(ability, TargetedAbility):
                    return SelectTargetEventHandler(engine=self.engine, parent=self, action=ability)
                else:
                    return ability
            else:
                self.engine.message_log.add_message("Ability on cooldown.", colors.invalid)
                return self
        elif key == tcod.event.KeySym.ESCAPE:
            return self.parent


class LootEventHandler(AskUserEventHandler):
    TEXT = "Choose which items to pick up:"

    def __init__(self, engine: Engine, parent: EventHandler) -> None:
        super().__init__(engine=engine, parent=parent)
        self.items: List[Item] = []
        self.gold = 0
        for enemy in self.engine.active_enemies.fighters:
            # for equippable in enemy.equipment.items.values():
            #     if equippable is not None:
            #         self.items.append(equippable.parent)
            for stack in enemy.inventory.items:
                self.items += stack
            self.gold += enemy.inventory.gold
        self.cursor = 0
        self.height = 8 + len(self.items)
        self.width = 4 + max(
            len(self.TEXT),
            len(f"You also pick up {self.gold} gold pieces!")
        )

        if len(self.items) != 0:
            self.width = max(
                self.width,
                max([len(item.name) for item in self.items]) + 4,
            )

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        if self.gold == 0 and len(self.items) == 0:
            return PopupMessage(MainGameEventHandler(self.engine), "There is no loot!")
        self.parent.on_render(console)
        console.rgb["fg"] //= 2
        console.rgb["bg"] //= 2

        x = (console.width - self.width) // 2
        y = (console.height - self.height) // 2

        console.draw_frame(
            x=x,
            y=y,
            width=self.width,
            height=self.height,
            fg=colors.white,
            bg=colors.black
        )
        console.print_box(
            x=x,
            y=y,
            width=self.width,
            height=1,
            string=f"┤Loot├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        console.print_box(
            x=x,
            y=y + 2,
            width=self.width,
            height=1,
            string=self.TEXT,
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        for i, item in enumerate(self.items):
            if self.cursor == i:
                fg = colors.black
                bg = colors.white
            else:
                fg = colors.white
                bg = colors.black
            console.print(
                x=x + 2,
                y=y + 4 + i,
                string=item.name,
                fg=fg,
                bg=bg
            )
        if self.gold > 0:
            console.print_box(
                x=x,
                y=y + self.height - 3,
                width=self.width,
                height=1,
                string=f"You also pick up {self.gold} gold pieces!",
                fg=colors.white,
                bg=colors.black,
                alignment=libtcodpy.CENTER
            )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        inventory = self.engine.player[0].inventory

        if key in CONFIRM_KEYS:
            if len(self.items) > 0:
                item = self.items.pop(self.cursor)
                try:
                    inventory.add_item(item)
                    self.cursor = min(self.cursor, len(self.items) - 1)
                    if len(self.items) == 0:
                        inventory.gold += self.gold
                        return self.parent
                except exceptions.Impossible:
                    self.items.insert(self.cursor, item)
                    self.engine.message_log.add_message(
                        text="You don't have room for that item.",
                        fg=colors.impossible,
                        stack=True
                    )
            else:
                inventory.gold += self.gold
                return self.parent

        elif key in CURSOR_Y_KEYS:
            self.cursor = (self.cursor + CURSOR_Y_KEYS[key]) % len(self.items)
            return self
        elif key == tcod.event.KeySym.ESCAPE:
            inventory.gold += self.gold

            for item in self.items:
                item.x = self.engine.active_enemies.x
                item.y = self.engine.active_enemies.y
                self.engine.game_map.entities.add(item)

            return self.parent

        return self

    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        return self


class TraderEventHandler(AskUserEventHandler):
    def __init__(self, engine: Engine, parent: EventHandler) -> None:
        super().__init__(engine=engine, parent=parent)
        self.trader = self.engine.active_trader
        self.cursor = [0, 0]

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        self.parent.on_render(console)
        console.rgb["fg"] //= 2
        console.rgb["bg"] //= 2

        player = self.engine.player[0]
        items = player.inventory.list_items()

        if len(items) == 0:
            self.cursor[0] = 1

        # Show player inventory
        width = max(max([len(item) for item in items]), len("Choose item to sell:")) + 4
        height = len(items) + 8
        x = console.width // 2 - width
        y = 1
        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            fg=colors.white,
            bg=colors.black
        )
        console.print_box(
            x=x,
            y=y,
            width=width,
            height=1,
            string="┤Inventory├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        console.print(
            x=x + 2,
            y=y + 2,
            string="Choose item to sell:",
            fg=colors.white,
            bg=colors.black
        )

        for i, item in enumerate(items):
            if self.cursor[0] == 0 and self.cursor[1] == i:
                fg = colors.black
                bg = colors.white
            else:
                fg = colors.white
                bg = colors.black
            console.print(
                x=x + 2,
                y=y + 4 + i,
                string=f"{item}",
                fg=fg,
                bg=bg
            )

        console.print(
            x=x + 2,
            y=y + height - 3,
            string=f"Gold: {player.inventory.gold}",
            fg=colors.white,
            bg=colors.black,
        )

        # Show trader inventory
        items = self.trader.inventory.list_items()

        if len(items) == 0:
            self.cursor[0] = 0

        width = max(max([len(item) for item in items]), len("Choose item to buy:")) + 4
        height = len(items) + 6
        x = console.width // 2 + 1
        y = 1
        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            fg=colors.white,
            bg=colors.black
        )
        console.print_box(
            x=x,
            y=y,
            width=width,
            height=1,
            string="┤Trader├",
            fg=colors.white,
            bg=colors.black,
            alignment=libtcodpy.CENTER
        )

        console.print(
            x=x + 2,
            y=y + 2,
            string="Choose item to buy:",
            fg=colors.white,
            bg=colors.black
        )

        for i, item in enumerate(items):
            if self.cursor[0] == 1 and self.cursor[1] == i:
                fg = colors.black
                bg = colors.white
            else:
                fg = colors.white
                bg = colors.black
            console.print(
                x=x + 2,
                y=y + 4 + i,
                string=f"{item}",
                fg=fg,
                bg=bg
            )

        # Show item description
        if self.cursor[0] == 0:
            text = player.inventory.items[self.cursor[1]][0].description
        else:
            text = self.trader.inventory.items[self.cursor[1]][0].description
            # item_name = re.match(
            #     pattern="(?P<name>[A-Za-z ]*) ?(?P<amount>\\(x[0-9]*\\))?",
            #     string=items[self.cursor[1]]
            # ).group(1).strip()
            # text = self.trader.get_item_by_name(item_name).description

        text = wrap(text, width - 2)

        console.draw_frame(
            x=x,
            y=y + height,
            width=width,
            height=2 + len(text.splitlines()),
            fg=colors.white,
            bg=colors.black
        )

        console.print(
            x=x + 1,
            y=y + height + 1,
            string=text,
            fg=colors.white,
            bg=colors.black
        )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym

        player_items = self.engine.player[0].inventory.items
        trader_items = self.trader.inventory.items
        if key in CURSOR_X_KEYS:
            if len(player_items) != 0 and len(trader_items) != 0:
                self.cursor[1] = 0
                self.cursor[0] = (self.cursor[0] + CURSOR_X_KEYS[key]) % 2
        elif key in CURSOR_Y_KEYS:
            if self.cursor[0] == 0 and len(player_items) != 0:
                self.cursor[1] = (self.cursor[1] + CURSOR_Y_KEYS[key]) % len(player_items)
            elif self.cursor[0] == 1 and len(trader_items) != 0:
                self.cursor[1] = (self.cursor[1] + CURSOR_Y_KEYS[key]) % len(trader_items)
        elif key in CONFIRM_KEYS:
            if self.cursor[0] == 0:
                item = player_items[self.cursor[1]][0]
                self.engine.player[0].inventory.remove_item(item)
                try:
                    self.engine.player[0].inventory.gold += self.trader.buy_item(item=item)
                    self.cursor[1] = min(self.cursor[1], len(self.engine.player[0].inventory.items) - 1)
                except exceptions.Impossible as exc:
                    self.engine.message_log.add_message("Trader inventory is full", fg=colors.impossible)
                    self.engine.player[0].inventory.add_item(item)
            else:
                item = trader_items[self.cursor[1]]
                if self.engine.player[0].inventory.gold < item.buy_price:
                    self.engine.message_log.add_message(text="Not enough gold", fg=colors.error)
                else:
                    try:
                        self.engine.player[0].inventory.add_item(self.trader.sell_item(item))
                        self.engine.player[0].inventory.gold -= item.buy_price
                        self.cursor[1] = min(self.cursor[1], len(self.trader.list_items()) - 1)
                    except exceptions.Impossible as exc:
                        self.engine.message_log.add_message(exc.args)

        elif key == tcod.event.KeySym.ESCAPE:
            self.engine.active_trader = None
            return self.parent


if __name__ == "__main__":
    screen_width = 112
    screen_height = 70

    handler = ClassSelectEventHandler()

    tileset = tcod.tileset.load_tilesheet(
        "images/dejavu10x10_gs_tc.png", 32, 8, tcod.tileset.CHARMAP_TCOD
    )
    with tcod.context.new_terminal(
            screen_width,
            screen_height,
            tileset=tileset,
            title="Rogue Python",
            vsync=True,
    ) as context:
        root_console = tcod.console.Console(screen_width, screen_height, order="F")
        try:
            while True:
                root_console.clear()
                handler = handler.on_render(console=root_console)
                context.present(root_console)
                for test_event in tcod.event.wait():
                    test_event = context.convert_event(test_event)
                    handler = handler.handle_events(test_event)
        except SystemExit:
            raise
