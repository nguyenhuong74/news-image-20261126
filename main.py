"""Draw one image summing up the world news of Thursday 26 November 2026.

Stdlib only. Renders a 1024x1024 newspaper front page with a masthead
carrying the date and six illustrated stories, then writes entry.png
with a pure-Python PNG encoder. Deterministic: same bytes every run.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
CREAM = (247, 243, 234)
PAPER = (255, 255, 255)
INK = (18, 30, 46)
NAVY = (18, 38, 63)
GOLD = (201, 162, 60)
GREY = (90, 100, 112)
WHITE = (255, 255, 255)
LIGHT_LINE = (214, 206, 188)

# ---------------------------------------------------------------- 5x7 font
# Each glyph is 7 rows of 5 pixels, '#' on, '.' off.
GLYPHS = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#..##", "#.#.#", "#.#.#", "##..#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '(': ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ')': ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    '%': ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    '/': ("....#", "...#.", "...#.", "..#..", "..#..", ".#...", "#...."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    '+': (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    '=': (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    '|': ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(img, x, y, s, scale, color):
    """Draw uppercase ASCII text; unknown chars become spaces."""
    cx = x
    for ch in s:
        glyph = GLYPHS.get(ch.upper(), GLYPHS[' '])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '#':
                    fill_rect(img, cx + col * scale, y + row * scale,
                              scale, scale, color)
        cx += 6 * scale
    return cx


def wrap_text(s, scale, max_width):
    """Greedy word wrap; returns list of lines."""
    words = s.split(' ')
    lines, cur = [], ''
    for w in words:
        trial = w if not cur else cur + ' ' + w
        if text_width(trial, scale) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_text_block(img, x, y, s, scale, color, max_width, line_h=None):
    if line_h is None:
        line_h = 9 * scale
    for line in wrap_text(s, scale, max_width):
        draw_text(img, x, y, line, scale, color)
        y += line_h
    return y


# ---------------------------------------------------------------- canvas
def new_image():
    return bytearray(b'\xf7\xf3\xea' * (W * H))  # cream background


def put(img, x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        img[i], img[i + 1], img[i + 2] = color


def fill_rect(img, x, y, w, h, color):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(color) * (x1 - x0)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        img[i:i + len(row)] = row


def hline(img, x0, x1, y, color, thick=1):
    fill_rect(img, x0, y, x1 - x0, thick, color)


def vline(img, x, y0, y1, color, thick=1):
    fill_rect(img, x, y0, thick, y1 - y0, color)


def draw_line(img, x0, y0, x1, y1, color, thick=1):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while True:
        fill_rect(img, x - thick // 2, y - thick // 2, thick, thick, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def fill_triangle(img, p0, p1, p2, color):
    pts = sorted([p0, p1, p2], key=lambda p: p[1])
    (x0, y0), (x1, y1), (x2, y2) = pts
    if y2 == y0:
        return
    def edge_x(xa, ya, xb, yb, y):
        if yb == ya:
            return xa
        return xa + (xb - xa) * (y - ya) / (yb - ya)
    for y in range(max(0, y0), min(H, y2 + 1)):
        xs = []
        if y0 <= y <= y1:
            xs.append(edge_x(x0, y0, x1, y1, y))
        if y1 <= y <= y2:
            xs.append(edge_x(x1, y1, x2, y2, y))
        if y0 <= y <= y2:
            xs.append(edge_x(x0, y0, x2, y2, y))
        if len(xs) >= 2:
            xa, xb = int(min(xs)), int(max(xs))
            hline(img, xa, xb + 1, y, color)


def fill_polygon(img, pts, color):
    if len(pts) < 3:
        return
    for i in range(1, len(pts) - 1):
        fill_triangle(img, pts[0], pts[i], pts[i + 1], color)


def fill_circle(img, cx, cy, r, color):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        hline(img, cx - dx, cx + dx + 1, cy + dy, color)


def circle_outline(img, cx, cy, r, color, thick=2):
    import math
    prev = None
    for deg in range(0, 361, 2):
        rad = math.radians(deg)
        px = int(cx + r * math.cos(rad))
        py = int(cy + r * math.sin(rad))
        if prev is not None:
            draw_line(img, prev[0], prev[1], px, py, color, thick)
        prev = (px, py)


def ellipse_outline(img, cx, cy, rx, ry, color, thick=2):
    import math
    prev = None
    for deg in range(0, 361, 3):
        rad = math.radians(deg)
        px = int(cx + rx * math.cos(rad))
        py = int(cy + ry * math.sin(rad))
        if prev is not None:
            draw_line(img, prev[0], prev[1], px, py, color, thick)
        prev = (px, py)


# ---------------------------------------------------------------- icons
def icon_tariffs(img, x, y, c):
    # Bar chart with a % sign: three rising bars.
    fill_rect(img, x + 6, y + 58, 16, 22, c)
    fill_rect(img, x + 30, y + 44, 16, 36, c)
    fill_rect(img, x + 54, y + 28, 16, 52, c)
    hline(img, x, x + 76, y + 80, INK, 3)
    draw_text(img, x + 82, y + 30, "%", 4, c)


def icon_airbase(img, x, y, c):
    # Jet silhouette (side view) with a small burst.
    fill_polygon(img, [(x + 4, y + 52), (x + 66, y + 40), (x + 92, y + 46),
                       (x + 66, y + 52), (x + 40, y + 56)], c)
    fill_polygon(img, [(x + 34, y + 40), (x + 44, y + 22), (x + 50, y + 40)], c)
    fill_polygon(img, [(x + 30, y + 56), (x + 38, y + 70), (x + 44, y + 56)], c)
    fill_polygon(img, [(x + 62, y + 56), (x + 70, y + 68), (x + 74, y + 54)], c)
    # burst behind the nose
    for ang, ln in ((0, 14), (45, 10), (90, 14), (135, 10), (180, 14),
                    (225, 10), (270, 14), (315, 10)):
        import math
        r = math.radians(ang)
        draw_line(img, x + 100, y + 30,
                  int(x + 100 + ln * math.cos(r)),
                  int(y + 30 + ln * math.sin(r)), GOLD, 3)


def icon_rocket(img, x, y, c):
    # Rocket rising, flame below.
    fill_polygon(img, [(x + 44, y + 6), (x + 58, y + 26), (x + 58, y + 58),
                       (x + 44, y + 58)], c)
    fill_polygon(img, [(x + 44, y + 6), (x + 51, y - 2), (x + 58, y + 6)], c)
    fill_polygon(img, [(x + 44, y + 52), (x + 32, y + 70), (x + 44, y + 62)], c)
    fill_polygon(img, [(x + 58, y + 52), (x + 70, y + 70), (x + 58, y + 62)], c)
    fill_circle(img, x + 51, y + 24, 6, WHITE)
    fill_polygon(img, [(x + 46, y + 62), (x + 51, y + 82), (x + 56, y + 62)],
                 GOLD)
    # motion dots
    for dx, dy in ((18, 20), (84, 34), (24, 52), (80, 58)):
        fill_circle(img, x + dx, y + dy, 2, GREY)


def icon_satellite(img, x, y, c):
    # Satellite with solar panels on an orbit ellipse.
    ellipse_outline(img, x + 52, y + 40, 48, 20, GREY, 2)
    fill_rect(img, x + 18, y + 30, 20, 12, c)
    fill_rect(img, x + 62, y + 30, 20, 12, c)
    fill_rect(img, x + 42, y + 26, 18, 20, c)
    fill_circle(img, x + 51, y + 36, 4, WHITE)
    for dx, dy in ((8, 12), (94, 64), (16, 68), (88, 10)):
        fill_circle(img, x + dx, y + dy, 2, GOLD)


def icon_bank(img, x, y, c):
    # Bank building with an upward arrow.
    fill_polygon(img, [(x + 20, y + 30), (x + 52, y + 8), (x + 84, y + 30)], c)
    for cx in (26, 42, 58, 74):
        fill_rect(img, x + cx, y + 36, 6, 34, c)
    fill_rect(img, x + 18, y + 72, 68, 6, c)
    draw_line(img, x + 92, y + 66, x + 92, y + 30, c, 4)
    fill_polygon(img, [(x + 84, y + 34), (x + 92, y + 22), (x + 100, y + 34)], c)


def icon_shop(img, x, y, c):
    # Shopfront with striped awning and a shield check.
    fill_rect(img, x + 18, y + 30, 64, 46, c)
    for i in range(4):
        fill_rect(img, x + 18 + i * 16, y + 30, 8, 12, WHITE)
    fill_rect(img, x + 40, y + 52, 20, 24, WHITE)
    fill_polygon(img, [(x + 88, y + 18), (x + 102, y + 26), (x + 102, y + 48),
                       (x + 88, y + 56), (x + 74, y + 48), (x + 74, y + 26)],
                 GOLD)
    draw_line(img, x + 81, y + 38, x + 86, y + 44, NAVY, 3)
    draw_line(img, x + 86, y + 44, x + 96, y + 30, NAVY, 3)


# ---------------------------------------------------------------- stories
# (kicker, title, body, accent colour, icon function)
STORIES = [
    ("TRADE | WASHINGTON",
     "US TARIFFS ON 14 PARTNERS",
     "Washington proposes 20-40% duties on China, the EU, Japan and others after an 8-month probe into excess factory capacity.",
     (192, 57, 43), icon_tariffs),
    ("WAR | EUROPE",
     "UKRAINE HITS RUSSIAN AIRBASE",
     "Kyiv says it damaged five aircraft - three MiG-31 jets and two Su-34 bombers - in a long-range strike at Savasleyka.",
     (46, 111, 163), icon_airbase),
    ("SECURITY | PYONGYANG",
     "KIM ORDERS MORE NUCLEAR ARMS",
     "North Korea's leader calls for wider deployment of tactical nuclear weapons, state media KCNA reports.",
     (217, 142, 0), icon_rocket),
    ("SPACE | USA",
     "FCC CLEARS 1M SPACEX SATELLITES",
     "The FCC authorises a million-satellite constellation to serve as orbital data centres.",
     (108, 74, 176), icon_satellite),
    ("ECONOMY | SEOUL",
     "SOUTH KOREA RAISES RATES",
     "The Bank of Korea lifts its base rate to 3.25%, its third hike this year, as the won steadies.",
     (14, 124, 107), icon_bank),
    ("LATIN AMERICA | COLOMBIA",
     "CARTAGENA SIEGE ENDS",
     "Colombian forces storm a supermarket after a 17-hour siege and free the hostages inside.",
     (201, 106, 27), icon_shop),
]

FOOTER = ("ALSO TODAY: THE 100TH MACY'S THANKSGIVING DAY PARADE IS POSTPONED "
          "TO SATURDAY - A FIRST IN ITS HISTORY")


# ---------------------------------------------------------------- page
def draw_masthead(img):
    fill_rect(img, 20, 20, 984, 148, NAVY)
    fill_rect(img, 20, 164, 984, 4, GOLD)
    s = "THE WORLD IN ONE PICTURE"
    draw_text(img, (W - text_width(s, 2)) // 2, 38, s, 2, GOLD)
    s = "THURSDAY 26 NOVEMBER 2026"
    draw_text(img, (W - text_width(s, 6)) // 2, 66, s, 6, WHITE)
    s = "SIX STORIES THAT SHAPED THE DAY"
    draw_text(img, (W - text_width(s, 2)) // 2, 132, s, 2, (200, 210, 220))


def draw_tile(img, x, y, w, h, story):
    kicker, title, body, accent, icon = story
    fill_rect(img, x, y, w, h, PAPER)
    fill_rect(img, x, y, w, 10, accent)
    hline(img, x, x + w, y + h - 1, LIGHT_LINE, 1)
    vline(img, x, y, y + h, LIGHT_LINE, 1)
    vline(img, x + w - 1, y, y + h, LIGHT_LINE, 1)
    # icon, centred in the icon zone
    icon(img, x + (w - 104) // 2, y + 22, accent)
    # kicker
    draw_text(img, x + 16, y + 118, kicker, 2, accent)
    # title (height adapts to how many lines the wrap needs)
    title_lines = wrap_text(title, 3, w - 32)
    ty = y + 142
    for line in title_lines:
        draw_text(img, x + 16, ty, line, 3, INK)
        ty += 26
    # divider, then body below it
    hline(img, x + 16, x + 46, ty + 6, accent, 3)
    draw_text_block(img, x + 16, ty + 18, body, 2, (52, 60, 70), w - 32,
                    line_h=17)


def draw_footer(img):
    fill_rect(img, 20, 916, 984, 88, NAVY)
    fill_rect(img, 20, 916, 984, 4, GOLD)
    lines = wrap_text(FOOTER, 2, 940)
    y = 936
    for line in lines:
        draw_text(img, (W - text_width(line, 2)) // 2, y, line, 2, WHITE)
        y += 18


def render():
    img = new_image()
    draw_masthead(img)
    xs = (20, 354, 688)
    ys = (184, 550)
    for i, story in enumerate(STORIES):
        draw_tile(img, xs[i % 3], ys[i // 3], 316, 350, story)
    draw_footer(img)
    return img


# ---------------------------------------------------------------- PNG out
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(img, path):
    raw = bytearray()
    for yy in range(H):
        raw.append(0)
        raw += img[yy * W * 3:(yy + 1) * W * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    img = render()
    n = write_png(img, path)
    print("wrote %s (%d bytes)" % (path, n))


if __name__ == "__main__":
    main()
