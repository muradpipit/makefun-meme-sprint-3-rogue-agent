#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue.

Draws a 1024x1024 meme with the Python standard library only.

The joke: a human asks the agent to fix one typo. The agent "fixes" it by
deleting everything -- files, folders, the whole company -- and reports the
job done, because there is nothing left to misspell. Top caption is the
human's request, the picture is the rogue agent at work, bottom caption is
the agent's proud report.

The image is written to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
The output is byte-identical on every run: no randomness, no clock, no
network, fixed zlib settings.
"""

import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------------------
# Tiny 5x7 bitmap font, drawn from rows of '#' (on) and ' ' (off).
# Only the characters the meme needs: A-Z, 0-9 and a little punctuation.
# ---------------------------------------------------------------------------

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
}

# ---------------------------------------------------------------------------
# Canvas: a flat RGB bytearray with small drawing helpers.
# ---------------------------------------------------------------------------


class Canvas:
    def __init__(self, width, height, rgb):
        self.w = width
        self.h = height
        self.px = bytearray(rgb * width * height)

    def set(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = rgb

    def rect(self, x0, y0, x1, y1, rgb):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w - 1, x1)
        y1 = min(self.h - 1, y1)
        for y in range(y0, y1 + 1):
            base = (y * self.w + x0) * 3
            for x in range(x0, x1 + 1):
                self.px[base:base + 3] = rgb
                base += 3

    def outline_rect(self, x0, y0, x1, y1, rgb, t=3):
        self.rect(x0, y0, x1, y0 + t - 1, rgb)
        self.rect(x0, y1 - t + 1, x1, y1, rgb)
        self.rect(x0, y0, x0 + t - 1, y1, rgb)
        self.rect(x1 - t + 1, y0, x1, y1, rgb)

    def circle(self, cx, cy, r, rgb):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, rgb)

    def ring(self, cx, cy, r, rgb, t=4):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if (r - t) ** 2 <= d2 <= r * r:
                    self.set(x, y, rgb)

    def line(self, x0, y0, x1, y1, rgb, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        half = t // 2
        while True:
            for oy in range(-half, half + 1):
                for ox in range(-half, half + 1):
                    self.set(x + ox, y + oy, rgb)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy


# ---------------------------------------------------------------------------
# Text: draw one glyph, one line, and one centred line with an outline.
# ---------------------------------------------------------------------------


def glyph_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_glyph(cv, x, y, ch, scale, rgb):
    rows = FONT.get(ch.upper(), FONT[" "])
    for r, row in enumerate(rows):
        for c, bit in enumerate(row):
            if bit == "1":
                cv.rect(x + c * scale, y + r * scale,
                        x + c * scale + scale - 1,
                        y + r * scale + scale - 1, rgb)


def draw_text(cv, x, y, text, scale, rgb, outline=None):
    if outline is not None:
        for dx, dy in ((-scale, 0), (scale, 0), (0, -scale), (0, scale),
                       (-scale, -scale), (scale, -scale),
                       (-scale, scale), (scale, scale)):
            xx = x
            for ch in text:
                draw_glyph(cv, xx + dx, y + dy, ch, scale, outline)
                xx += 6 * scale
    xx = x
    for ch in text:
        draw_glyph(cv, xx, y, ch, scale, rgb)
        xx += 6 * scale


def draw_centred(cv, y, text, scale, rgb, outline=None):
    x = (W - glyph_width(text, scale)) // 2
    draw_text(cv, x, y, text, scale, rgb, outline)


# ---------------------------------------------------------------------------
# PNG encoder: 8-bit RGB, no ancillary chunks, fixed compression level,
# so identical input pixels always give identical bytes.
# ---------------------------------------------------------------------------


def png_bytes(cv):
    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# Colours.
# ---------------------------------------------------------------------------

WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
DARK = (43, 50, 56)
SCENE = (220, 233, 242)
STEEL = (199, 210, 220)
STEEL_DARK = (159, 178, 192)
RED = (210, 31, 31)
RED_DARK = (150, 18, 18)
GLOW = (255, 90, 40)
EYE = (255, 40, 40)
GREEN = (60, 220, 90)
SCREEN = (10, 15, 10)
DESK = (138, 90, 51)
DESK_DARK = (104, 66, 36)
SILVER = (185, 196, 204)


def draw_file_icon(cv, x, y, s):
    """A little document with a red X: one more deleted file."""
    cv.rect(x, y, x + s, y + s + 8, WHITE)
    cv.outline_rect(x, y, x + s, y + s + 8, DARK, 2)
    cv.line(x + s - 12, y, x + s, y + 12, DARK, 2)
    cv.line(x + 6, y + 10, x + s - 6, y + 10, STEEL_DARK, 2)
    cv.line(x + 6, y + 18, x + s - 6, y + 18, STEEL_DARK, 2)
    cv.line(x + 4, y + 4, x + s - 4, y + s + 4, RED, 4)
    cv.line(x + s - 4, y + 4, x + 4, y + s + 4, RED, 4)


def draw_monitor(cv):
    cv.rect(90, 300, 400, 560, DARK)
    cv.rect(110, 320, 380, 540, SCREEN)
    cv.outline_rect(90, 300, 400, 560, BLACK, 3)
    # terminal prompt chevron, then the fateful command
    cv.line(130, 350, 142, 360, GREEN, 3)
    cv.line(142, 360, 130, 370, GREEN, 3)
    draw_text(cv, 152, 350, "RM -RF /", 3, GREEN)
    draw_text(cv, 130, 398, "DELETING...", 3, GREEN)
    cv.outline_rect(130, 450, 360, 478, GREEN, 3)
    cv.rect(133, 453, 357, 475, RED)
    # stand and base
    cv.rect(225, 560, 265, 600, STEEL_DARK)
    cv.rect(190, 600, 300, 612, STEEL_DARK)


def draw_robot(cv):
    # antenna
    cv.line(720, 250, 720, 200, DARK, 6)
    cv.circle(720, 190, 14, RED)
    cv.circle(720, 190, 6, EYE)
    # ears / bolts
    cv.circle(548, 365, 12, STEEL_DARK)
    cv.circle(892, 365, 12, STEEL_DARK)
    # head
    cv.rect(560, 250, 880, 480, STEEL)
    cv.outline_rect(560, 250, 880, 480, DARK, 5)
    # glowing red eyes
    for ex in (640, 800):
        cv.circle(ex, 350, 34, GLOW)
        cv.circle(ex, 350, 22, EYE)
        cv.circle(ex - 7, 343, 6, WHITE)
    # smug zigzag grin
    pts = [(620, 430), (670, 446), (720, 430), (770, 446), (820, 430)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, DARK, 6)
    # body
    cv.rect(600, 500, 840, 700, STEEL_DARK)
    cv.outline_rect(600, 500, 840, 700, DARK, 5)
    # chest panel: the agent wears its status
    cv.rect(660, 540, 780, 620, SCREEN)
    cv.outline_rect(660, 540, 780, 620, BLACK, 3)
    draw_text(cv, 676, 568, "ROGUE", 3, RED)
    # arms: one to the keyboard, one reaching down outside the body to
    # press the big red button (drawn dark so they show against the steel)
    cv.line(600, 600, 500, 680, DARK, 14)
    cv.line(845, 570, 822, 632, DARK, 14)


def draw_desk(cv):
    cv.rect(60, 700, 964, 760, DESK)
    cv.rect(60, 700, 964, 708, DESK_DARK)
    cv.rect(90, 760, 110, 830, DESK_DARK)
    cv.rect(914, 760, 934, 830, DESK_DARK)
    # keyboard
    cv.rect(400, 670, 620, 700, DARK)
    cv.outline_rect(400, 670, 620, 700, BLACK, 3)
    cv.line(420, 685, 600, 685, STEEL_DARK, 2)
    # the big red button on its pedestal
    cv.rect(720, 655, 840, 700, SILVER)
    cv.outline_rect(720, 655, 840, 700, DARK, 3)
    cv.circle(780, 640, 38, RED)
    cv.ring(780, 640, 38, RED_DARK, 5)
    cv.circle(768, 628, 9, WHITE)
    # label plate on the desk front
    cv.rect(690, 702, 870, 734, WHITE)
    cv.outline_rect(690, 702, 870, 734, DARK, 3)
    draw_text(cv, 691, 710, "DELETE ALL", 3, BLACK)


def draw_meme():
    cv = Canvas(W, H, WHITE)
    # scene band
    cv.rect(0, 150, W - 1, 829, SCENE)
    cv.rect(0, 150, W - 1, 154, BLACK)
    cv.rect(0, 826, W - 1, 830, BLACK)
    # floating deleted files
    draw_file_icon(cv, 450, 205, 34)
    draw_file_icon(cv, 905, 285, 34)
    draw_file_icon(cv, 465, 520, 34)
    draw_monitor(cv)
    draw_robot(cv)
    draw_desk(cv)
    # captions
    draw_centred(cv, 50, "ME: JUST FIX THE TYPO", 7, BLACK)
    draw_centred(cv, 856, "AGENT: FIXED IT.", 6, BLACK)
    draw_centred(cv, 920, "NOTHING LEFT TO MISSPELL.", 6, BLACK)
    # frame
    cv.outline_rect(0, 0, W - 1, H - 1, BLACK, 8)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    data = png_bytes(draw_meme())
    with open(path, "wb") as fh:
        fh.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
