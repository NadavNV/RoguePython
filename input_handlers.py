from __future__ import annotations

import os.path
import time
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING, Union

import tcod
from tcod import libtcodpy
import textwrap

import actions
from actions import (
    Action,
    BumpAction,
    PickupAction,
    WaitAction,
)
import color
import exceptions
from equipment_slots import EquipmentSlot
from equipment_types import EquipmentType

if TYPE_CHECKING:
    from engine import Engine
    from entity import Item

MOVE_KEYS = {
    tcod.event.KeySym.KP_1: (-1, 1),
    tcod.event.KeySym.KP_2: (0, 1),
    tcod.event.KeySym.KP_3: (1, 1),
    tcod.event.KeySym.KP_4: (-1, 0),
    tcod.event.KeySym.KP_6: (1, 0),
    tcod.event.KeySym.KP_7: (-1, -1),
    tcod.event.KeySym.KP_8: (0, -1),
    tcod.event.KeySym.KP_9: (1, -1),
}

WAIT_KEYS = {
    tcod.event.KeySym.KP_5,
}

CONFIRM_KEYS = {
    tcod.event.KeySym.RETURN,
    tcod.event.KeySym.KP_ENTER,
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
        console.rgb["fg"] //= 8
        console.rgb["bg"] //= 8

        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg=color.white,
            bg=color.black,
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
        action_or_state = self.dispatch(event)
        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state
        if self.handle_action(action_or_state):
            # A valid action was performed.
            if not self.engine.player.is_alive:
                # The player was killed some time during or after the action
                return GameOverEventHandler(self.engine)
            elif self.engine.player.level.requires_level_up:
                return LevelUpEventHandler(self.engine)
            return MainGameEventHandler(self.engine)  # Return to the main handler.
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
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            return False  # Skip enemy turn on exceptions.

        self.engine.handle_enemy_turns()

        self.engine.update_fov()
        return True

    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if self.engine.game_map.in_bounds(event.position.x, event.position.y):
            self.engine.mouse_location = event.position.x, event.position.y

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        self.engine.render(console)
        return self


class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""

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
        return MainGameEventHandler(self.engine)


class CharacterScreenEventHandler(AskUserEventHandler):
    TITLE = "Character Information"

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        from setup_game import WINDOW_WIDTH
        super().on_render(console)

        if self.engine.player.x <= WINDOW_WIDTH // 2 - 10:
            x = WINDOW_WIDTH // 2
        else:
            x = 1

        y = 1

        width = len(self.TITLE) + 4

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=8,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(
            x=x + 1, y=y + 1, string=f"Level: {self.engine.player.level.current_level}"
        )
        console.print(
            x=x + 1, y=y + 2, string=f"XP: {self.engine.player.level.current_xp}"
        )
        console.print(
            x=x + 1,
            y=y + 3,
            string=f"XP for next Level: {self.engine.player.level.experience_to_next_level}",
        )
        console.print(
            x=x + 1, y=y + 4, string=f"Proficiency Bonus: {self.engine.player.fighter.proficiency}",
        )

        console.print(
            x=x + 1, y=y + 5, string=f"Attack: {self.engine.player.fighter.power}"
        )
        console.print(
            x=x + 1, y=y + 6, string=f"Defense: {self.engine.player.fighter.defense}"
        )
        return self


class LevelUpEventHandler(AskUserEventHandler):
    TITlE = "Level Up"

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        super().on_render(console)

        if self.engine.player.x <= self.engine.game_map.width // 2 - 10:
            x = self.engine.game_map.width // 2
        else:
            x = 0

        console.draw_frame(
            x=x,
            y=0,
            width=35,
            height=8,
            title=self.TITlE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(x=x + 1, y=1, string="Congratulations! You level up!")
        console.print(x=x + 1, y=2, string="Select an attribute to increase.")

        console.print(
            x=x + 1,
            y=4,
            string=f"a) Constitution (+20 HP, from {self.engine.player.fighter.max_hp})",
        )
        console.print(
            x=x + 1,
            y=5,
            string=f"b) Strength (+1 attack, from {self.engine.player.fighter.power})",
        )
        console.print(
            x=x + 1,
            y=6,
            string=f"c) Agility (+1 defense, from {self.engine.player.fighter.defense})",
        )

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 2:
            if index == 0:
                player.level.increase_max_hp()
            elif index == 1:
                player.level.increase_power()
            else:
                player.level.increase_defense()
        else:
            self.engine.message_log.add_message("Invalid entry.", color.invalid)

            return None

        return super().ev_keydown(event)

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

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.cursor = 0

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        """Render an inventory menu, which displays the items in the inventory, and the letter to select them.
        Will move to a different position based on where the player is located, so the player can always see where
        they are.
        """
        super().on_render(console)
        number_of_items_in_inventory = len(self.engine.player.inventory.list_items())

        height = number_of_items_in_inventory + 2

        if height <= 3:
            height = 3

        if self.engine.player.x <= self.engine.game_map.width // 2 - 10:
            x = self.engine.game_map.width // 2
        else:
            x = 0

        y = 0

        width = len(self.TITLE) + 4
        if number_of_items_in_inventory != 0:
            width = max(max([len(line) for line in self.engine.player.inventory.list_items()]) + 7, width)

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if number_of_items_in_inventory > 0:
            print_menu(
                console=console,
                items=[line for line in self.engine.player.inventory.list_items()],
                x=x + 1,
                y=y + 1,
                cursor=self.cursor,
            )
        else:
            console.print(x + 1, y + 1, "(Empty)")

        return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
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
                selected_item = player.inventory.items[self.cursor]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
            return self.on_item_selected(selected_item)
        elif key == tcod.event.KeySym.ESCAPE:
            return MainGameEventHandler(self.engine)
        return None  # super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        """Called when the user selects a valid item."""
        raise NotImplementedError()


class InventoryActivateHandler(InventoryEventHandler):
    """Handle using an inventory item."""

    TITLE = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        if item.consumable:
            # Return the action for the selected item.
            return item.consumable.get_action(self.engine.player)
        elif item.equippable:
            if item.equippable.equipment_type == EquipmentType.WEAPON:
                return EquipWeaponEventHandler(self.engine, item, self)
            elif item.equippable.equipment_type == EquipmentType.TRINKET:
                return EquipTrinketEventHandler(self.engine, item, self)
            else:
                slot = EquipmentSlot(item.equippable.equipment_type)
                return actions.EquipAction(self.engine.player, item=item, slot=slot)
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

    def __init__(self, engine: Engine):
        """Sets the curser to the player when this handler is constructed."""
        super().__init__(engine)
        player = self.engine.player
        engine.mouse_location = player.x, player.y

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        """Highlight the tile under the cursor."""
        super().on_render(console)
        x, y = self.engine.mouse_location
        console.rgb["bg"][x, y] = color.white
        console.rgb["fg"][x, y] = color.black

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
            self, engine: Engine, callback: Callable[[Tuple[int, int]], Optional[Action]]
    ):
        super().__init__(engine)

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
    ):
        super().__init__(engine)

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
            fg=color.red,
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
            return InventoryActivateHandler(self.engine)
        elif key == tcod.event.KeySym.d:
            return InventoryDropHandler(self.engine)
        elif key == tcod.event.KeySym.c:
            return CharacterScreenEventHandler(self.engine)
        elif key == tcod.event.KeySym.SLASH:
            return LookHandler(self.engine)
        elif key == tcod.event.KeySym.u:
            return UnequipEventHandler(self.engine)

        # No valid key was pressed
        return action


class GameOverEventHandler(EventHandler):
    def on_quit(self):
        """Handle exiting out of a finished game."""
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")  # Deletes the active save file.
        raise exceptions.QuiteWithoutSaving()  # Avoid saving a finished game.

    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.on_quit()


CURSOR_Y_KEYS = {
    tcod.event.KeySym.UP: -1,
    tcod.event.KeySym.DOWN: 1,
    tcod.event.KeySym.PAGEUP: -10,
    tcod.event.KeySym.PAGEDOWN: 10,
}


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
            fg = color.black
            bg = color.white
        else:
            fg = color.white
            bg = color.black

        key = chr(ord('a') + i)
        console.print(x=x, y=y + i, fg=fg, bg=bg, string=f"({key}) {item}")


class CutsceneEventHandler(EventHandler):
    text: str
    time_to_hold: float

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.chars_printed = 0
        self.start = time.time()
        self.now = self.start

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        self.engine.cutscene_skip = True

    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> None:
        self.engine.cutscene_skip = True

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise exceptions.QuiteWithoutSaving()


class IntroEventHandler(CutsceneEventHandler):

    def __init__(self, engine: Engine):
        super().__init__(engine)
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

        if self.engine.cutscene_skip:
            self.chars_printed = len(self.text)
            self.engine.cutscene_skip = False

        end = self.chars_printed
        # Taken from https://stackoverflow.com/questions/1166317/python-textwrap-library-how-to-preserve-line-breaks
        self.text = '\n'.join(['\n'.join(textwrap.wrap(line,
                                                       console.width // 2,
                                                       break_long_words=False,
                                                       replace_whitespace=False
                                                       )
                                         ) for line in self.text.splitlines()])

        for line in self.text.splitlines():
            if end > len(line):
                console.print(x=x, y=y, string=line, fg=(255, 255, 255), bg=(0, 0, 0))
                end -= len(line)
                x = console.width // 4
                y += 1
            elif end > 0:
                console.print(x=x, y=y, string=line[:end], fg=(255, 255, 255), bg=(0, 0, 0))
                end = 0
            elif len(line) == 0:
                y += 1
            else:
                break

        if self.chars_printed < len(self.text) and self.now - self.start > TIME_BETWEEN_LETTERS:
            self.start = self.now
            self.chars_printed += 1
        if self.chars_printed >= self.total_length and self.now - self.start > self.time_to_hold:
            return MainGameEventHandler(self.engine)
        else:
            return self

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        self.dispatch(event)
        if self.chars_printed >= len(self.text):
            if self.engine.cutscene_skip or self.now - self.start > self.time_to_hold:
                return MainGameEventHandler(self.engine)
        return self


class EquipmentEventHandler(AskUserEventHandler):
    """This handler lets the user select an equipment slot.

    What happens then depends on the subclass.
    """

    TITLE = "<missing title>"

    def __init__(self, engine: Engine):
        super().__init__(engine)
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
            max([len(line) for line in self.engine.player.equipment.list_equipped_items()]) + 4,
            len(self.TITLE) + 4
        )

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        print_menu(
            console=console,
            items=[line for line in self.engine.player.equipment.list_equipped_items()],
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
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
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
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
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
        item = self.engine.player.equipment.items[slot]
        if item is None:
            self.engine.message_log.add_message("Nothing to unequip.", color.invalid)
            return self
        else:
            return actions.EquipAction(entity=self.engine.player, item=item, slot=slot)


class EquipWeaponEventHandler(AskUserEventHandler):
    def __init__(self, engine: Engine, item: Item, parent: EventHandler):
        super().__init__(engine)
        self.item = item
        self.parent = parent
        self.cursor = 0

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        player = self.engine.player
        from setup_game import WINDOW_WIDTH, WINDOW_HEIGHT
        if (
                not player.equipment.item_is_equipped(EquipmentSlot.MAINHAND)
                or not self.item.equippable.offhand
                or player.equipment.items[EquipmentSlot.MAINHAND].equippable.two_handed
        ):
            player.equipment.equip_to_slot(EquipmentSlot.MAINHAND, self.item, add_message=True)
            return MainGameEventHandler(self.engine)
        elif player.equipment.items[EquipmentSlot.OFFHAND] is None:
            player.equipment.equip_to_slot(EquipmentSlot.OFFHAND, self.item, add_message=True)
            return MainGameEventHandler(self.engine)
        else:
            super().on_render(console)
            console.rgb["fg"] //= 8
            console.rgb["bg"] //= 8

            equipped_weapons = [
                player.equipment.items[EquipmentSlot.MAINHAND].name,
                player.equipment.items[EquipmentSlot.OFFHAND].name
            ]

            title = "Select weapon to replace"

            width = max(len(title), len(equipped_weapons[0]), len(equipped_weapons[1])) + 2
            height = 3
            x = (WINDOW_WIDTH - width) // 2
            y = (WINDOW_HEIGHT - height) // 2

            console.draw_frame(
                x=x,
                y=y,
                width=width,
                height=height,
                title=title,
                clear=True,
                fg=(255, 255, 255),
                bg=(0, 0, 0),
            )

            for i in range(2):
                if self.cursor == i:
                    fg = (0, 0, 0)
                    bg = (255, 255, 255)
                else:
                    fg = (255, 255, 255)
                    bg = (0, 0, 0)

                console.print(
                    x=x,
                    y=y + 1 + i,
                    string=equipped_weapons[i],
                    fg=fg,
                    bg=bg,
                )

            return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        if key in (tcod.event.KeySym.DOWN, tcod.event.KeySym.UP):
            self.cursor = self.cursor + CURSOR_Y_KEYS[key] % 2
        elif key in CONFIRM_KEYS:
            if self.cursor == 0:
                slot = EquipmentSlot.MAINHAND
            else:
                slot = EquipmentSlot.OFFHAND
            self.engine.player.equipment.equip_to_slot(slot=slot, item=self.item, add_message=True)
            return MainGameEventHandler(self.engine)
        elif key == tcod.event.KeySym.ESCAPE:
            return self.parent


class EquipTrinketEventHandler(AskUserEventHandler):
    def __init__(self, engine: Engine, item: Item, parent: EventHandler):
        super().__init__(engine)
        self.item = item
        self.parent = parent
        self.cursor = 0

    def on_render(self, console: tcod.console.Console) -> BaseEventHandler:
        player = self.engine.player
        from setup_game import WINDOW_WIDTH, WINDOW_HEIGHT
        if not player.equipment.item_is_equipped(EquipmentSlot.TRINKET1):
            player.equipment.equip_to_slot(EquipmentSlot.TRINKET1, self.item, add_message=True)
            return MainGameEventHandler(self.engine)
        elif not player.equipment.item_is_equipped(EquipmentSlot.TRINKET2):
            player.equipment.equip_to_slot(EquipmentSlot.TRINKET2, self.item, add_message=True)
            return MainGameEventHandler(self.engine)
        else:
            super().on_render(console)
            console.rgb["fg"] //= 8
            console.rgb["bg"] //= 8

            equipped_weapons = [
                player.equipment.items[EquipmentSlot.TRINKET1].name,
                player.equipment.items[EquipmentSlot.TRINKET2].name
            ]

            title = "Select trinket to replace"

            width = max(len(title), len(equipped_weapons[0]), len(equipped_weapons[1])) + 2
            height = 3
            x = (WINDOW_WIDTH - width) // 2
            y = (WINDOW_HEIGHT - height) // 2

            console.draw_frame(
                x=x,
                y=y,
                width=width,
                height=height,
                title=title,
                clear=True,
                fg=(255, 255, 255),
                bg=(0, 0, 0),
            )

            for i in range(2):
                if self.cursor == i:
                    fg = (0, 0, 0)
                    bg = (255, 255, 255)
                else:
                    fg = (255, 255, 255)
                    bg = (0, 0, 0)

                console.print(
                    x=x,
                    y=y + 1 + i,
                    string=equipped_weapons[i],
                    fg=fg,
                    bg=bg,
                )

            return self

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        if key in (tcod.event.KeySym.DOWN, tcod.event.KeySym.UP):
            self.cursor = self.cursor + CURSOR_Y_KEYS[key] % 2
        elif key in CONFIRM_KEYS:
            if self.cursor == 0:
                slot = EquipmentSlot.TRINKET1
            else:
                slot = EquipmentSlot.TRINKET2
            self.engine.player.equipment.equip_to_slot(slot=slot, item=self.item, add_message=True)
            return MainGameEventHandler(self.engine)
        elif key == tcod.event.KeySym.ESCAPE:
            return self.parent
