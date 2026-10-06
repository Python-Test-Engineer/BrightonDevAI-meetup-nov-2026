#!/usr/bin/env python3
"""Print a big, expressive ASCII-art 'HELLO'.

Each letter is drawn in 5-row block art and painted with its own
bright ANSI color, framed by a glowing banner.
"""

import sys

# The block/box glyphs and ANSI colors need UTF-8 output.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# Bright / high-intensity ANSI foreground colors.
COLORS = [
    "\033[91m",  # red
    "\033[93m",  # yellow
    "\033[92m",  # green
    "\033[96m",  # cyan
    "\033[95m",  # magenta
]
BORDER = "\033[1;97m"   # bold bright white
DIM = "\033[2;37m"      # dim grey
RESET = "\033[0m"

# 5-row block font for the letters we need.
FONT = {
    "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
}

WORD = "HELLO"
# Map the font's '#' cells to chunky blocks (U+2588, full block).
PIXEL = "\u2588\u2588"

# Box-drawing glyphs used to frame the banner.
TL, TR, BL, BR = "\u2554", "\u2557", "\u255a", "\u255d"
HZ, VT = "\u2550", "\u2551"
LT, RT = "\u2560", "\u2563"


def render(word):
    """Return the list of art rows for `word`, colorized per letter."""
    rows = [""] * 5
    for i, ch in enumerate(word):
        color = COLORS[i % len(COLORS)]
        glyph = FONT[ch]
        for r in range(5):
            # Rebuild the row from '#' pixels so every cell is one block wide.
            line = "".join(PIXEL if cell == "#" else "  " for cell in glyph[r])
            rows[r] += f"{color}{line}{RESET} "
    return rows


def main():
    art = render(WORD)
    width = 54

    print(f"{BORDER}{TL}{HZ * width}{TR}{RESET}")
    title = "BRIGHTON WEB DEV MEETUP  \u00b7  NOV 2026"
    print(f"{BORDER}{VT}{RESET}{title.center(width)}{BORDER}{VT}{RESET}")
    print(f"{BORDER}{LT}{HZ * width}{RT}{RESET}")
    print(f"{BORDER}{VT}{RESET}{' ' * width}{BORDER}{VT}{RESET}")
    for row in art:
        print(f"{BORDER}{VT}{RESET}{row.center(width + 9)}{BORDER}{VT}{RESET}")
    print(f"{BORDER}{VT}{RESET}{' ' * width}{BORDER}{VT}{RESET}")
    print(f"{BORDER}{BL}{HZ * width}{BR}{RESET}")
    tagline = "-> stay curious, keep shipping <-"
    print(f"{DIM}{tagline.center(width + 2)}{RESET}")


if __name__ == "__main__":
    main()
