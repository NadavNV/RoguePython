from typing import Tuple
import numpy as np # type: ignore

# Tile graphics strutctured type compatible with Console,tiles_tgb.
graphics_dt = np.dtype(
    [
        ("ch", np.int32),   #Unicode codepoint.
        ("fg", "3B"),       # 3 unsigned bytes, for RGB colors
        ("bg", "3B"),
    ]
)

# Tile struct used for statically define tile data
tile_dt = np.dtype(
    [
        ("walkable", bool),      # True if this tile can be walked over.
        ("transparent", bool),   # True if this tile doesn't block FoV.
        ("dark", graphics_dt),      # Graphics for when this tile is not in FoV.
    ]
)

def new_tile(
        *,  # Enforce the use of keywords, so that parameter order doesn't matter.
        walkable: int,
        transparent: int,
        dark: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
) -> np.ndarray:
    """Helper function for definint individual tile types"""
    return np.array((walkable, transparent, dark), dtype=tile_dt)

floor = new_tile(
    walkable=True, transparent=True, dark=(ord(" "), (255, 2555, 255), (50, 50, 150)),
)
wall = new_tile(
    walkable=False, transparent=False, dark=(ord(" "), (255, 255, 255), (0, 0, 100)),
)