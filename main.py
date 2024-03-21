#!/usr/bin/env python3
import traceback
import faulthandler

import tcod

import colors
import exceptions
import input_handlers
import setup_game

FRAMERATE = 1.0 / 60


def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
    """If the current event handler has an active Engine then save it."""
    if isinstance(handler, input_handlers.EventHandler):
        handler.engine.save_as(filename)
        print("Game saved.")


def main() -> None:
    screen_width = setup_game.WINDOW_WIDTH
    screen_height = setup_game.WINDOW_HEIGHT

    tileset = tcod.tileset.load_tilesheet(
        "images/dejavu10x10_gs_tc.png", 32, 8, tcod.tileset.CHARMAP_TCOD
    )

    handler: input_handlers.BaseEventHandler = input_handlers.MainMenu()

    with tcod.context.new(
        columns=screen_width,
        rows=screen_height,
        tileset=tileset,
        title="Rogue Python",
        vsync=True,
    ) as context:
        root_console = tcod.console.Console(screen_width, screen_height, order="F")
        # Start the game in full screen mode
        # context.sdl_window.fullscreen = tcod.lib.SDL_WINDOW_FULLSCREEN_DESKTOP
        try:
            while True:
                root_console.clear()
                handler = handler.on_render(console=root_console)
                context.present(root_console)

                try:
                    for event in tcod.event.wait(FRAMERATE):
                        event = context.convert_event(event)
                        handler = handler.handle_events(event)
                except Exception:  # Handle exceptions in game.
                    traceback.print_exc()  # Print error to stderr.
                    # Then print the error to the message log.
                    if isinstance(handler, input_handlers.EventHandler):
                        handler.engine.message_log.add_message(
                            traceback.format_exc(), colors.error
                        )
        except exceptions.QuitWithoutSaving:
            raise
        except SystemExit:  # Save and quit.
            save_game(handler, "savegame.sav")
            raise
        except BaseException:  # Save on any other unexpected exception.
            save_game(handler, "savegame.sav")
            raise


if __name__ == "__main__":
    main()
