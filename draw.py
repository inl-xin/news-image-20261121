#!/usr/bin/env python3
"""Draw the make.fun news-image-20261121 entry v3 (1024x1024) with PIL.

v1: same page style as the 20 Nov v14 file (pink accent, coloured
illustration backgrounds, cream paper, uppercase bold card titles,
thick black card borders, flat pixel-style art, pink number dots,
serif masthead date with pink underline, green land / pale blue sea
map), but rebuilt for the 21 Nov brief (23 stories: 21 drawn panels
+ 2 ALSO briefs) with 7 layout optimisations:
  1. grid: heroes 3 equal columns; secondary rows fixed 5 equal
     columns; the last row holds the remaining 2 panels as 2 equal
     columns (no blank cell); uniform 8px gaps, uniform 8px margins
     (panel widths differ by at most 1px, because 1008px of content
     minus 8px gaps is not divisible by 3 or 5).
  2. heroes: 128px tall = 1.5x the 85px secondary height; hero art
     116px (vs 62px secondary) and hero titles 15px (vs 11px).
     Left-image/right-text layout is kept: the art block is made
     taller/wider inside the card instead of moving it on top, so
     "art = 55% of card height" is adapted as art filling ~91% of
     the hero card height (vs ~73% for secondary cards).
  3. numbers strip: 6 cells, each two lines -- a big pink number
     (~18px bold) centred above a small uppercase label (~8px),
     centred, with vertical divider lines between cells.
  4. summaries: at least 10px, 1.3x leading, at most 2 lines,
     ellipsised if longer (trunc2); summaries were rewritten short
     while keeping every key number and fact.
  5. number dots: one size (r=11) on every card, fixed 6px inset
     from the art's top-right corner.
  6. illustration backgrounds: one fixed colour per region, taken
     from the region bar (ASIA / EUROPE / MIDDLE EAST / AMERICAS /
     AFRICA / OCEANIA / GLOBAL).
  7. map: Natural Earth 110m land polygons (embedded lon/lat,
     Equal Earth projection, lat clipped to [-50, 75] -- no
     Antarctica, Greenland cut at 75N), 576px wide (~10% narrower
     than v20's 640px); dots projected from real lat/lon through
     the same projection, nudged only where two centres would
     overlap or a dot would fall in the sea (see MAP_DOT_NUDGE);
     dot 20 Pago Pago sits at the left edge by the dateline
     (lon -170.7), dot 18 Banda Sea sits in the sea as it should.
  v2: map rewritten from Natural Earth 110m GeoJSON (embedded in
     NE_LAND); no hand-drawn continents any more, and the old
     white internal country borders are gone (they were hand-drawn
     in the schematic frame and cannot be re-projected).
  v3: map drawn at 60% -- frame 346px wide (was 576), land at
     60% of its v2 size centred in the frame; the frame stays
     252px tall so it stays flush with the info box, which takes
     the freed width (MAP KEY now 4 columns x 5 rows, ALSO text
     wider). Dots, graticule and header scale with the map.
  v4: all 20 illustrations redrawn as three-layer scenes
     (background / midground / foreground + horizon, main
     subject at one third, top-right kept clear of the badge),
     panel 13 is now F1 Las Vegas qualifying (Anthropic out),
     and the map dots are enlarged to r=7 with 9px numbers, with
     new de-collision nudges (MAP_DOT_NUDGE) so no two dots
     overlap at the larger size.
  v5: 21 drawn panels (3 heroes + 18 secondary): panel 21 is
     US measles (CDC update Fri 20 Nov, first reported Sat
     21 Nov -- 5,838 cases, highest since 1991, 646 in
     hospital, 6 dead), so the last secondary row is now 3
     equal columns (331/330/331) instead of 2 x 500px; the map
     gains dot 21 Atlanta (CDC HQ). The US map cluster is
     crowded at 60% scale, so dots 1/11/13 got small new
     nudges (verified: every dot still on land, closest pair
     14.3px -- discs are 14px, so no overlap) and the MAP KEY
     is now 3 columns x 7 rows. AMERICAS is 6, 23 stories,
     21 drawn.
Content: only verified 21 Nov 2026 stories from
NEWS_BRIEF_2026-11-21.md. Deterministic: fixed fonts, fixed
geometry, no randomness, no network.
Run:  python3 draw.py [output_path]   (default: entry.png next to this file)
main.py (stdlib-only) just copies entry.png to the output dir.
"""
import math
import os
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
DJ = "/usr/share/fonts/truetype/dejavu/"
SERIF_B = DJ + "DejaVuSerif-Bold.ttf"
SERIF = DJ + "DejaVuSerif.ttf"
SANS_B = DJ + "DejaVuSans-Bold.ttf"
SANS = DJ + "DejaVuSans.ttf"

PAPER = "#FFF9F0"
CARD = "#FFFFFF"
INK = "#141414"
INK2 = "#333333"
GREY = "#8A8A8A"
RED = "#E63946"
RED2 = "#FF2E63"
NAVY = "#1B4F9C"
GREEN = "#1FA36B"
OCHRE = "#FFB703"
SKY = "#AEE9FF"
SAND = "#FFE9A8"
SEA = "#2EA8FF"
PINK = "#FF8FB1"
PINK2 = "#FF6FA5"
YELLOW = "#FFD93D"
MINT = "#5EE6A8"
ORANGE = "#FF8A3D"
LAV = "#C9B6FF"


def F(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, font, max_w):
    """Greedy word wrap; returns list of lines fitting max_w."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_block(draw, xy, lines, font, fill, leading=None):
    x, y = xy
    leading = leading or int(font.size * 1.18)
    for ln in lines:
        draw.text((x, y), ln, font=font, fill=fill)
        y += leading
    return y


def _justify_line(draw, x, y, line, font, fill, max_w, justify,
                  max_extra=5.0):
    """Draw one line; if justify, spread its words edge to edge.

    Extra space (max_w minus the natural width) is shared evenly
    between the inter-word gaps, so the first word starts at x and
    the last word ends at x + max_w. Single-word lines and lines
    with no slack fall back to plain left-aligned drawing.
    v14: justification is capped -- a line is only stretched when
    it has at least 3 words AND the extra space per gap is at most
    max_extra px. Short lines (2 words, or a nearly-empty line)
    used to be stretched to absurd 25-40px word gaps in the narrow
    100px text columns; they now stay left-aligned instead.
    """
    words = line.split()
    if not justify or len(words) < 3:
        draw.text((x, y), line, font=font, fill=fill)
        return
    space_w = draw.textlength(" ", font=font)
    widths = [draw.textlength(w, font=font) for w in words]
    natural = sum(widths) + space_w * (len(words) - 1)
    extra = max_w - natural
    if extra <= 0.5:
        draw.text((x, y), line, font=font, fill=fill)
        return
    per = extra / (len(words) - 1)
    if per > max_extra:
        # Too much slack for this line: stretching would leave
        # visibly gappy word spacing, so keep it left-aligned.
        draw.text((x, y), line, font=font, fill=fill)
        return
    cx = x
    for i, w in enumerate(words):
        draw.text((cx, y), w, font=font, fill=fill)
        if i < len(words) - 1:
            cx += widths[i] + space_w + per


def justified_block(draw, xy, lines, font, fill, max_w, leading=None):
    """Draw wrapped lines justified: every line but the last is
    stretched to max_w by _justify_line; the last line is left
    aligned. Lines come from wrap(), so each already fits max_w
    naturally and justification only ever widens word gaps --
    nothing can overflow or overlap."""
    x, y = xy
    leading = leading or int(font.size * 1.18)
    for i, ln in enumerate(lines):
        _justify_line(draw, x, y, ln, font, fill, max_w,
                      justify=(i < len(lines) - 1))
        y += leading
    return y


def badge(d, x, y, n, r=11):
    """Pink numbered disc, white ring, white number. v1 (21 Nov):
    ONE size for every card (r=11, 22px disc), always placed by the
    caller at a fixed 6px inset from the art's top-right corner."""
    d.ellipse([x, y, x + 2 * r, y + 2 * r], fill=RED2,
              outline="#FFFFFF", width=2)
    f = F(SANS_B, 12)
    t = str(n)
    tw = d.textlength(t, font=f)
    d.text((x + r - tw / 2, y + r - 8), t, font=f, fill="#FFFFFF")


def trunc2(d, text, font, max_w):
    """Wrap text to at most 2 lines; if it does not fit, cut the
    second line short and end it with an ellipsis. Summaries are
    written short enough to fit naturally; this is only a safety
    net so a long summary can never overflow its card."""
    lines = wrap(d, text, font, max_w)
    if len(lines) <= 2:
        return lines
    words = " ".join(lines[1:]).split()
    cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t + "\u2026", font=font) <= max_w:
            cur = t
        else:
            break
    return [lines[0], cur + "\u2026"]


def panel(d, x, y, w, h, art, n, tag, head, sub, fn, bg, head_size=13,
          sub_size=10, tag_size=10):
    """One story panel, v8 horizontal layout kept: a SQUARE art block
    on the left (vertically centred), the numbered badge on the art's
    top-right corner, and tag / headline / sub-headline stacked on
    the right. v1 (21 Nov) changes:
    * bg: the region colour, painted by the art function itself, so
      every panel from one region shares one illustration background.
    * badge: uniform r=11, fixed 6px inset from the art's top-right
      corner (ax+art-6-22, ay+6) on every card.
    * sub: at least 10px, leading 1.3x, at most 2 lines (trunc2
      ellipsises anything longer); headline capped at 3 lines.
    Text sizes were measured so the longest headline (3 lines) +
    longest sub-headline (2 lines) still fit inside h."""
    d.rectangle([x, y, x + w, y + h], fill=CARD, outline=INK, width=3)
    ax, ay = x + 4, y + (h - art) // 2
    fn(d, ax, ay, art, art, bg)
    badge(d, ax + art - 6 - 22, ay + 6, n)
    tx = ax + art + 6
    tw = x + w - 6 - tx
    f_head = F(SANS_B, head_size)
    head_lines = wrap(d, head, f_head, tw)[:3]
    f_sub = F(SANS, sub_size)
    sub_lines = trunc2(d, sub, f_sub, tw)
    # Centre the text block vertically when the card has slack
    # (heroes and the wide last row); cards whose text already
    # fills the height are unaffected (dy = 0).
    block_h = (tag_size + 3 + len(head_lines) * int(head_size * 1.12)
               + 2 + len(sub_lines) * int(sub_size * 1.3))
    dy = max(0, (h - block_h) // 2 - 5)
    f = F(SANS_B, tag_size)
    d.text((tx, y + 5 + dy), tag, font=f, fill=RED)
    yy = text_block(d, (tx, y + 5 + tag_size + 3 + dy), head_lines,
                    f_head, INK, leading=int(head_size * 1.12))
    justified_block(d, (tx, yy + 2), sub_lines, f_sub, INK2, max_w=tw,
                    leading=int(sub_size * 1.3))


# NOTE (cleanup): the 20 Nov helpers (flag/smoke/flame/waves) and the
# 20 Nov art_* functions used to live here. None of them is called by
# the 21 Nov panels, so they were deleted; what follows is only the
# 21 Nov art, which is everything this entry actually draws.

# Two of those helpers turned out to still be used by the 21 Nov art
# (waves under the tankers and the drone, flame on the missile and
# tanker scenes), so they are rewritten here in their new home; flag
# and smoke stay deleted, nothing calls them any more.

def flame(d, fx, base_y, fh):
    """One flat flame: orange outer triangle, red edge, yellow core."""
    outer = [(fx - 8, base_y), (fx, base_y - fh), (fx + 8, base_y)]
    d.polygon(outer, fill="#E86A1A", outline="#B03A2E", width=1)
    inner = [(fx - 4, base_y), (fx, base_y - fh // 2), (fx + 4, base_y)]
    d.polygon(inner, fill="#FFD23F")


def waves(d, x, y, w, h, col="#FFFFFF"):
    """Three white wave arcs spaced across a sea band."""
    step = w // 3
    for i in range(3):
        wx = x + 10 + i * step
        d.arc([wx, y, wx + 26, y + 12], 180, 360, fill=col, width=2)


# ---------------------------------------------------------------- 21 Nov art
# New flat pixel-style illustrations for 2026-11-21, same helpers and
# drawing idiom as the v20 art functions. Every function draws into a
# SQUARE box (w == h) and takes bg = the region colour (see REGION_BG
# in main): the first rectangle is always the region background, so
# all panels from one region share one illustration background.
# Text inside art is kept to one short label at most, sized from w
# so it reads at both the 116px hero size and the 62px secondary size.

# ---------------------------------------------------------------- 21 Nov art
# v4: every illustration redrawn as a small scene -- place + event --
# in the same flat pixel style (coloured region background, thick
# 2px ink outlines, pink only as an accent). Rules applied to all
# 20, so the page reads as one set:
# * three layers (background / midground / foreground) + one
#   horizon line; the ground/sea band sits below the horizon.
# * the main subject sits at about one third across, and the
#   top-right of the art (where the number badge sits) is kept
#   to plain sky/background only -- nothing important hides
#   under the badge.
# * every object gets a flat shadow in a deeper shade of its own
#   colour (an offset block or an ellipse on the ground).
# * besides the region background, each picture uses only 3-4
#   colours (ink outlines and white details aside); pink is an
#   accent, never a main fill.
# * small details: windows, smoke, wave arcs, sparkle lines.
# * fixed symbols by story type: conflict = explosion starburst,
#   economy = K-line candles + red arrow, weather = cloud +
#   spiral, politics = podium + gavel, disaster = warning
#   triangle. People are faceless silhouettes; a prop (mic,
#   helmet, gavel, flag) says who they are.
# Every function draws into a SQUARE box (w == h) and takes bg =
# the region colour: the first rectangle is always the region
# background, so all panels from one region share one
# illustration background. Text inside art is at most one short
# label, sized from w so it reads at both 116px (hero) and 62px.

def burst(d, cx, cy, r, ray="#FFD23D"):
    """Explosion starburst (conflict symbol): 8 rays + orange core
    with a red ring. r is the ray length in px."""
    for a in range(0, 360, 45):
        rad = math.radians(a)
        d.line([cx, cy, cx + r * math.cos(rad),
                cy + r * math.sin(rad)], fill=ray, width=2)
    d.ellipse([cx - r * 0.45, cy - r * 0.45, cx + r * 0.45,
               cy + r * 0.45], fill="#E86A1A", outline=RED2, width=1)


def cloud(d, x, y, w):
    """Soft white cloud, w px wide, no outline."""
    d.ellipse([x, y, x + w * 0.45, y + w * 0.30], fill="#FFFFFF")
    d.ellipse([x + w * 0.25, y - w * 0.12, x + w * 0.70,
               y + w * 0.22], fill="#FFFFFF")
    d.ellipse([x + w * 0.55, y, x + w, y + w * 0.30], fill="#FFFFFF")


def spiral(d, cx, cy, r):
    """Cyclone spiral (weather symbol): three white arcs + red eye."""
    for rr, a0 in ((r, 20), (r * 0.7, 110), (r * 0.45, 200)):
        d.arc([cx - rr, cy - rr, cx + rr, cy + rr], a0, a0 + 220,
              fill="#FFFFFF", width=3)
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=RED2)


def warn(d, cx, cy, s):
    """Warning triangle (disaster symbol): white triangle, red
    outline, red '!'. s is the half-width in px."""
    d.polygon([(cx, cy - s), (cx + s, cy + s * 0.7),
               (cx - s, cy + s * 0.7)], fill="#FFFFFF", outline=RED2,
              width=2)
    f = F(SANS_B, max(8, int(s * 0.9)))
    t = "!"
    d.text((cx - d.textlength(t, font=f) / 2, cy - s * 0.35), t,
           font=f, fill=RED2)


def fig(d, cx, base_y, s, col=INK):
    """Faceless silhouette: head circle + shoulder trapezoid, no
    face. base_y is the feet line, s the height in px."""
    d.ellipse([cx - s * 0.18, base_y - s * 0.95, cx + s * 0.18,
               base_y - s * 0.59], fill=col, outline=INK, width=2)
    d.polygon([(cx - s * 0.30, base_y), (cx - s * 0.26, base_y - s * 0.55),
               (cx + s * 0.26, base_y - s * 0.55),
               (cx + s * 0.30, base_y)], fill=col, outline=INK, width=2)


def ground_band(d, x, y, w, h, hy, col):
    """Horizon line + the ground/sea band below it. hy is the
    horizon as a fraction of h."""
    d.rectangle([x, y + hy * h, x + w, y + h], fill=col)
    d.line([x, y + hy * h, x + w, y + hy * h], fill=INK, width=2)


def windows(d, x, y, w, h, cols, rows, col="#FFFFFF"):
    """Small window panes in a cols x rows grid over a w x h area."""
    cw, ch = w / cols, h / rows
    for i in range(cols):
        for j in range(rows):
            d.rectangle([x + i * cw + cw * 0.25, y + j * ch + ch * 0.25,
                         x + (i + 1) * cw - cw * 0.25,
                         y + (j + 1) * ch - ch * 0.25], fill=col)


def spark(d, cx, cy, s=5, col="#FFD23D"):
    """Four-point sparkle: two crossed short lines."""
    d.line([cx - s, cy, cx + s, cy], fill=col, width=2)
    d.line([cx, cy - s, cx, cy + s], fill=col, width=2)


def art_stocks(d, x, y, w, h, bg):
    """1 US stocks plunge: navy skyline, red falling K-line candles
    with a red down arrow, -3.7% tag on the ground."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    # background: distant navy skyline behind the horizon
    for bx, bw, bh in ((0.06, 0.14, 0.22), (0.22, 0.12, 0.30),
                       (0.36, 0.14, 0.18)):
        d.rectangle([x + bx * w, y + 0.64 * h - bh * h,
                     x + (bx + bw) * w, y + 0.64 * h], fill="#1B4F9C",
                    outline=INK, width=2)
        windows(d, x + (bx + 0.02) * w, y + 0.64 * h - bh * h + 0.03 * h,
                (bw - 0.04) * w, (bh - 0.05) * h, 2, 2)
    ground_band(d, x, y, w, h, 0.64, "#E88AA8")
    # midground: falling red candles (economy symbol) + trend arrow
    for i, bh in enumerate((0.34, 0.28, 0.22, 0.16)):
        bx = x + (0.08 + i * 0.11) * w
        d.line([bx + 0.035 * w, y + 0.26 * h, bx + 0.035 * w, y + 0.30 * h],
               fill="#8E2B20", width=2)
        d.rectangle([bx, y + 0.30 * h, bx + 0.07 * w,
                     y + (0.30 + bh) * h], fill=RED2,
                    outline="#8E2B20", width=2)
    d.line([(x + 0.10 * w, y + 0.24 * h), (x + 0.52 * w, y + 0.58 * h)],
           fill=RED2, width=4)
    d.polygon([(x + 0.52 * w, y + 0.58 * h), (x + 0.42 * w, y + 0.56 * h),
               (x + 0.50 * w, y + 0.66 * h)], fill=RED2)
    spark(d, x + 0.56 * w, y + 0.52 * h)
    # foreground: -3.7% tag on the ground
    d.rectangle([x + 0.08 * w, y + 0.76 * h, x + 0.48 * w, y + 0.92 * h],
                fill="#FFFFFF", outline=INK, width=2)
    d.text((x + 0.12 * w, y + 0.79 * h), "-3.7%",
           font=F(SANS_B, max(8, int(w * 0.11))), fill=RED2)


def art_btc(d, x, y, w, h, bg):
    """2 Bitcoin crash then rebound: V-shaped chart (red down,
    green up) over a big gold coin on the ground, +9% tag."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.06 * w, y + 0.08 * h, 0.30 * w)
    # midground: V chart, kept left of the badge corner
    d.line([(x + 0.08 * w, y + 0.28 * h), (x + 0.33 * w, y + 0.58 * h)],
           fill=RED2, width=4)
    d.line([(x + 0.33 * w, y + 0.58 * h), (x + 0.54 * w, y + 0.30 * h)],
           fill=GREEN, width=4)
    d.polygon([(x + 0.54 * w, y + 0.30 * h), (x + 0.46 * w, y + 0.30 * h),
               (x + 0.52 * w, y + 0.38 * h)], fill=GREEN)
    ground_band(d, x, y, w, h, 0.64, "#5BC8BC")
    # foreground: big gold coin + one small coin, with shadows
    d.ellipse([x + 0.14 * w, y + 0.82 * h, x + 0.46 * w, y + 0.90 * h],
              fill="#4AA89E")
    cx, cy = x + 0.30 * w, y + 0.78 * h
    d.ellipse([cx - 0.17 * h + 0.02 * h, cy - 0.17 * h + 0.02 * h,
               cx + 0.17 * h + 0.02 * h, cy + 0.17 * h + 0.02 * h],
              fill="#B26A00")
    d.ellipse([cx - 0.17 * h, cy - 0.17 * h, cx + 0.17 * h,
               cy + 0.17 * h], fill="#F7931A", outline="#B26A00", width=2)
    f = F(SANS_B, max(10, int(w * 0.18)))
    t = "B"
    d.text((cx - d.textlength(t, font=f) / 2, cy - 0.11 * h), t, font=f,
           fill="#FFFFFF")
    sx, sy = x + 0.58 * w, y + 0.74 * h
    d.ellipse([sx - 0.09 * h, sy - 0.09 * h, sx + 0.09 * h,
               sy + 0.09 * h], fill="#F7931A", outline="#B26A00", width=2)
    f2 = F(SANS_B, max(8, int(w * 0.10)))
    d.text((sx - d.textlength(t, font=f2) / 2, sy - 0.06 * h), t,
           font=f2, fill="#FFFFFF")
    spark(d, x + 0.50 * w, y + 0.66 * h, col="#FFFFFF")
    # +9% rebound tag, bottom right
    d.rectangle([x + 0.66 * w, y + 0.78 * h, x + 0.94 * w, y + 0.92 * h],
                fill="#FFFFFF", outline=INK, width=2)
    d.text((x + 0.70 * w, y + 0.80 * h), "+9%",
           font=F(SANS_B, max(8, int(w * 0.10))), fill=GREEN)


def art_missile(d, x, y, w, h, bg):
    """3 Russian missile hits Kryvyi Rih: city blocks, missile
    streak, explosion starbursts, smoke, rubble."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    # background: white distant blocks behind the horizon
    for bx, bw, bh in ((0.62, 0.14, 0.14), (0.78, 0.12, 0.18)):
        d.rectangle([x + bx * w, y + 0.64 * h - bh * h,
                     x + (bx + bw) * w, y + 0.64 * h], fill="#FFFFFF",
                    outline=INK, width=2)
    ground_band(d, x, y, w, h, 0.64, "#6FB1E8")
    # midground: warm city blocks with windows
    for bx, bw, bh in ((0.06, 0.20, 0.20), (0.30, 0.18, 0.28),
                       (0.52, 0.20, 0.16)):
        d.rectangle([x + bx * w, y + 0.64 * h - bh * h,
                     x + (bx + bw) * w, y + 0.64 * h], fill="#FFC98A",
                    outline=INK, width=2)
        windows(d, x + (bx + 0.02) * w, y + 0.64 * h - bh * h + 0.03 * h,
                (bw - 0.04) * w, (bh - 0.05) * h, 2, 2)
    # missile streaking down from the top left to the burst
    d.line([x + 0.12 * w, y + 0.10 * h, x + 0.30 * w, y + 0.34 * h],
           fill="#FFFFFF", width=3)
    d.polygon([(x + 0.30 * w, y + 0.34 * h), (x + 0.36 * w, y + 0.36 * h),
               (x + 0.32 * w, y + 0.42 * h)], fill=INK)
    burst(d, x + 0.33 * w, y + 0.44 * h, 0.13 * h)
    burst(d, x + 0.56 * w, y + 0.52 * h, 0.09 * h)
    cloud(d, x + 0.08 * w, y + 0.20 * h, 0.20 * w)
    # foreground: rubble triangles on the ground
    for rx, rw in ((0.14, 0.10), (0.44, 0.12)):
        d.polygon([(x + rx * w, y + 0.92 * h),
                   (x + (rx + rw / 2) * w, y + 0.78 * h),
                   (x + (rx + rw) * w, y + 0.92 * h)], fill=INK)


def art_saudi(d, x, y, w, h, bg):
    """4 Saudi intercepts 3 Houthi missiles: Riyadh tower, side
    blocks, three white interception bursts in the sky."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    # background: red sun + white distant blocks
    d.ellipse([x + 0.07 * w, y + 0.07 * h, x + 0.21 * w, y + 0.21 * h],
              fill=RED2, outline="#8E2B20", width=2)
    for bx, bw, bh in ((0.66, 0.14, 0.14), (0.82, 0.12, 0.18)):
        d.rectangle([x + bx * w, y + 0.64 * h - bh * h,
                     x + (bx + bw) * w, y + 0.64 * h], fill="#FFFFFF",
                    outline=INK, width=2)
    ground_band(d, x, y, w, h, 0.64, "#EDC200")
    # midground: tall blue tower with pointed top + side blocks
    d.rectangle([x + 0.30 * w, y + 0.34 * h, x + 0.46 * w, y + 0.64 * h],
                fill="#8ED8FF", outline=INK, width=2)
    d.polygon([(x + 0.30 * w, y + 0.34 * h), (x + 0.38 * w, y + 0.26 * h),
               (x + 0.46 * w, y + 0.34 * h)], fill="#8ED8FF",
              outline=INK, width=2)
    windows(d, x + 0.33 * w, y + 0.38 * h, 0.10 * w, 0.22 * h, 2, 3)
    d.polygon([(x + 0.38 * w, y + 0.26 * h), (x + 0.50 * w, y + 0.29 * h),
               (x + 0.38 * w, y + 0.32 * h)], fill=RED2, outline=INK,
              width=1)
    for bx, bw, bh in ((0.08, 0.18, 0.16), (0.54, 0.16, 0.12)):
        d.rectangle([x + bx * w, y + 0.64 * h - bh * h,
                     x + (bx + bw) * w, y + 0.64 * h], fill="#FFC98A",
                    outline=INK, width=2)
        windows(d, x + (bx + 0.02) * w, y + 0.64 * h - bh * h + 0.03 * h,
                (bw - 0.04) * w, (bh - 0.05) * h, 2, 1)
    # three interception bursts, kept left of the badge corner
    for ex, ey in ((0.14, 0.30), (0.33, 0.14), (0.50, 0.28)):
        d.line([x + ex * w, y + (ey + 0.10) * h, x + ex * w,
                y + (ey + 0.18) * h], fill="#8A8A8A", width=2)
        burst(d, x + ex * w, y + ey * h, 0.09 * h, ray="#FFFFFF")


def art_drone(d, x, y, w, h, bg):
    """5 Iran downs US MQ-9 drone over Hormuz: smoke trail, drone
    falling nose-down over a wave band, splash below."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.06 * w, y + 0.08 * h, 0.26 * w)
    ground_band(d, x, y, w, h, 0.64, SEA)
    waves(d, x, y + 0.68 * h, w, 8)
    waves(d, x + 0.20 * w, y + 0.80 * h, w - 0.20 * w, 6)
    # smoke trail from the top left down to the drone
    for sx, sy, sr in ((0.10, 0.16, 0.05), (0.17, 0.24, 0.06),
                       (0.24, 0.32, 0.07)):
        d.ellipse([x + (sx - sr) * w, y + (sy - sr) * h,
                   x + (sx + sr) * w, y + (sy + sr) * h], fill="#FFFFFF",
                  outline="#8A8A8A", width=1)
    # midground: MQ-9 nose-down at one third across
    cx, cy = x + 0.33 * w, y + 0.46 * h
    d.polygon([(cx - 0.26 * w, cy - 0.10 * h), (cx + 0.24 * w, cy + 0.04 * h),
               (cx + 0.18 * w, cy + 0.12 * h), (cx - 0.28 * w, cy - 0.02 * h)],
              fill="#8A8A8A", outline=INK, width=2)
    d.polygon([(cx - 0.06 * w, cy - 0.02 * h), (cx + 0.02 * w, cy - 0.20 * h),
               (cx + 0.08 * w, cy - 0.02 * h)], fill="#6A6A6A",
              outline=INK, width=1)
    d.polygon([(cx - 0.06 * w, cy + 0.02 * h), (cx + 0.02 * w, cy + 0.20 * h),
               (cx + 0.08 * w, cy + 0.02 * h)], fill="#6A6A6A",
              outline=INK, width=1)
    flame(d, cx + 0.20 * w, cy + 0.16 * h, 8)
    # foreground: splash starburst in the sea + distant boat
    burst(d, x + 0.58 * w, y + 0.80 * h, 0.09 * h, ray="#FFFFFF")
    d.polygon([(x + 0.72 * w, y + 0.60 * h), (x + 0.92 * w, y + 0.60 * h),
               (x + 0.88 * w, y + 0.66 * h), (x + 0.76 * w, y + 0.66 * h)],
              fill="#3A3A3A", outline=INK, width=2)
    d.line([x + 0.82 * w, y + 0.60 * h, x + 0.82 * w, y + 0.50 * h],
           fill=INK, width=2)


def art_tanker(d, x, y, w, h, bg):
    """6 Two tankers struck near Hormuz: container tanker with
    smoke and flame at the stern, second tanker behind, waves."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.08 * w, y + 0.08 * h, 0.26 * w)
    # background: white headland at the horizon, left
    d.polygon([(x + 0.04 * w, y + 0.66 * h), (x + 0.14 * w, y + 0.52 * h),
               (x + 0.24 * w, y + 0.66 * h)], fill="#FFFFFF",
              outline=INK, width=2)
    ground_band(d, x, y, w, h, 0.66, SEA)
    waves(d, x, y + 0.70 * h, w, 8)
    # midground: tanker at one third across, stern left
    d.polygon([(x + 0.08 * w, y + 0.60 * h), (x + 0.58 * w, y + 0.60 * h),
               (x + 0.54 * w, y + 0.74 * h), (x + 0.12 * w, y + 0.74 * h)],
              fill="#3A3A3A", outline=INK, width=2)
    for i, col in enumerate((RED2, "#FFFFFF", RED2)):
        d.rectangle([x + (0.16 + i * 0.12) * w, y + 0.48 * h,
                     x + (0.26 + i * 0.12) * w, y + 0.60 * h], fill=col,
                    outline=INK, width=1)
    d.rectangle([x + 0.48 * w, y + 0.38 * h, x + 0.56 * w, y + 0.60 * h],
                fill="#FFFFFF", outline=INK, width=2)
    windows(d, x + 0.49 * w, y + 0.40 * h, 0.06 * w, 0.16 * h, 1, 3,
            col="#3A3A3A")
    for px in (0.20, 0.32, 0.44):
        d.ellipse([x + px * w - 2, y + 0.65 * h - 2, x + px * w + 2,
                   y + 0.65 * h + 2], fill="#FFFFFF")
    # smoke + flame at the stern
    cloud(d, x + 0.06 * w, y + 0.26 * h, 0.18 * w)
    flame(d, x + 0.12 * w, y + 0.60 * h, 10)
    # foreground: second tanker, small, lower right
    d.polygon([(x + 0.66 * w, y + 0.78 * h), (x + 0.92 * w, y + 0.78 * h),
               (x + 0.89 * w, y + 0.86 * h), (x + 0.69 * w, y + 0.86 * h)],
              fill="#3A3A3A", outline=INK, width=2)
    d.rectangle([x + 0.72 * w, y + 0.70 * h, x + 0.80 * w, y + 0.78 * h],
                fill=RED2, outline=INK, width=1)


def art_front(d, x, y, w, h, bg):
    """7 Ukraine frontline: trench zigzag, sandbags, a faceless
    soldier silhouette, explosion bursts, drone dots overhead."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    # background: distant treeline triangles along the horizon
    for tx in (0.06, 0.18, 0.62, 0.74, 0.86):
        d.polygon([(x + tx * w, y + 0.62 * h),
                   (x + (tx + 0.06) * w, y + 0.48 * h),
                   (x + (tx + 0.12) * w, y + 0.62 * h)], fill="#8A6D3B",
                  outline=INK, width=1)
    ground_band(d, x, y, w, h, 0.62, "#8A6D3B")
    # drone dots overhead, top left
    for dx, dy in ((0.12, 0.16), (0.45, 0.12)):
        d.ellipse([x + dx * w - 3, y + dy * h - 3, x + dx * w + 3,
                   y + dy * h + 3], fill="#FFFFFF", outline=RED2, width=1)
    burst(d, x + 0.25 * w, y + 0.40 * h, 0.11 * h)
    burst(d, x + 0.50 * w, y + 0.32 * h, 0.09 * h)
    cloud(d, x + 0.44 * w, y + 0.16 * h, 0.18 * w)
    # midground: sandbags + trench zigzag across the ground
    for sx in (0.10, 0.22, 0.34, 0.46):
        d.ellipse([x + sx * w, y + 0.64 * h, x + (sx + 0.10) * w,
                   y + 0.70 * h], fill="#FFFFFF", outline=INK, width=1)
    d.line([(x + 0.06 * w, y + 0.78 * h), (x + 0.26 * w, y + 0.70 * h),
            (x + 0.46 * w, y + 0.78 * h), (x + 0.66 * w, y + 0.70 * h),
            (x + 0.94 * w, y + 0.78 * h)], fill="#3A2A18", width=3)
    # foreground: faceless soldier silhouette crouching in the trench
    fig(d, x + 0.33 * w, y + 0.92 * h, 0.30 * h)
    d.pieslice([x + 0.27 * w, y + 0.62 * h, x + 0.39 * w, y + 0.72 * h],
               180, 360, fill="#3A2A18", outline=INK, width=2)


def art_nato(d, x, y, w, h, bg):
    """8 Poland fallout: NATO compass disc, a faceless speaker
    behind a podium, Polish flag at the foot."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.06 * w, y + 0.08 * h, 0.26 * w)
    ground_band(d, x, y, w, h, 0.64, "#6FB1E8")
    # midground: navy compass disc (NATO star) at one third across
    cx, cy = x + 0.33 * w, y + 0.38 * h
    d.ellipse([cx - 0.21 * h - 0.02 * h, cy - 0.21 * h + 0.02 * h,
               cx + 0.21 * h - 0.02 * h, cy + 0.21 * h + 0.02 * h],
              fill="#123A6E")
    d.ellipse([cx - 0.21 * h, cy - 0.21 * h, cx + 0.21 * h,
               cy + 0.21 * h], fill="#1B4F9C", outline="#FFFFFF", width=3)
    d.polygon([(cx, cy - 0.17 * h), (cx + 0.05 * h, cy - 0.05 * h),
               (cx + 0.17 * h, cy), (cx + 0.05 * h, cy + 0.05 * h),
               (cx, cy + 0.17 * h), (cx - 0.05 * h, cy + 0.05 * h),
               (cx - 0.17 * h, cy), (cx - 0.05 * h, cy - 0.05 * h)],
              fill="#FFFFFF")
    d.ellipse([cx - 0.04 * h, cy - 0.04 * h, cx + 0.04 * h,
               cy + 0.04 * h], fill="#1B4F9C")
    for sx, sy in ((0.10, 0.30), (0.56, 0.22), (0.60, 0.48)):
        d.ellipse([x + sx * w - 2, y + sy * h - 2, x + sx * w + 2,
                   y + sy * h + 2], fill="#FFFFFF")
    # foreground: speaker silhouette behind a navy podium
    fig(d, x + 0.33 * w, y + 0.74 * h, 0.22 * h, col="#1B4F9C")
    d.rectangle([x + 0.16 * w, y + 0.74 * h, x + 0.50 * w, y + 0.94 * h],
                fill="#1B4F9C", outline=INK, width=2)
    d.rectangle([x + 0.20 * w, y + 0.78 * h, x + 0.46 * w, y + 0.90 * h],
                fill="#FFFFFF", outline=INK, width=1)
    d.ellipse([x + 0.30 * w, y + 0.80 * h, x + 0.36 * w, y + 0.86 * h],
              fill=RED2)
    # Polish flag on a pole, lower right
    d.line([x + 0.66 * w, y + 0.60 * h, x + 0.66 * w, y + 0.88 * h],
           fill=INK, width=2)
    d.rectangle([x + 0.66 * w, y + 0.62 * h, x + 0.90 * w, y + 0.71 * h],
                fill="#FFFFFF", outline=INK, width=1)
    d.rectangle([x + 0.66 * w, y + 0.71 * h, x + 0.90 * w, y + 0.80 * h],
                fill="#DC143C", outline=INK, width=1)


def art_denmark(d, x, y, w, h, bg):
    """9 Denmark expels Russian attache: Danish flag, exit door
    with a red arrow out, suitcase on the ground."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.40 * w, y + 0.06 * h, 0.22 * w)
    # background: white skyline + spire at the horizon, right
    d.rectangle([x + 0.62 * w, y + 0.50 * h, x + 0.76 * w, y + 0.64 * h],
                fill="#FFFFFF", outline=INK, width=2)
    d.polygon([(x + 0.78 * w, y + 0.64 * h), (x + 0.82 * w, y + 0.40 * h),
               (x + 0.86 * w, y + 0.64 * h)], fill="#FFFFFF",
              outline=INK, width=2)
    ground_band(d, x, y, w, h, 0.64, "#6FB1E8")
    # midground: Danish flag on a pole, left
    d.line([x + 0.22 * w, y + 0.14 * h, x + 0.22 * w, y + 0.60 * h],
           fill=INK, width=2)
    fx, fy = x + 0.22 * w, y + 0.14 * h
    d.rectangle([fx, fy, fx + 0.28 * w, fy + 0.20 * h], fill="#C8102E",
                outline=INK, width=2)
    d.rectangle([fx + 0.08 * w, fy, fx + 0.12 * w, fy + 0.20 * h],
                fill="#FFFFFF")
    d.rectangle([fx, fy + 0.08 * h, fx + 0.28 * w, fy + 0.12 * h],
                fill="#FFFFFF")
    # exit door, right, with a red arrow pointing out of it
    dx = x + 0.56 * w
    d.rectangle([dx, y + 0.48 * h, dx + 0.28 * w, y + 0.86 * h],
                fill="#FFFFFF", outline=INK, width=2)
    d.line([dx + 0.05 * w, y + 0.66 * h, dx + 0.22 * w, y + 0.66 * h],
           fill=RED2, width=3)
    d.polygon([(dx + 0.22 * w, y + 0.66 * h), (dx + 0.16 * w, y + 0.60 * h),
               (dx + 0.16 * w, y + 0.72 * h)], fill=RED2)
    d.ellipse([dx + 0.22 * w, y + 0.60 * h, dx + 0.25 * w, y + 0.63 * h],
              fill=INK)
    # foreground: suitcase with a shadow, bottom left
    d.ellipse([x + 0.08 * w, y + 0.88 * h, x + 0.34 * w, y + 0.94 * h],
              fill="#5A8AC8")
    sx = x + 0.10 * w
    d.rectangle([sx, y + 0.70 * h, sx + 0.22 * w, y + 0.88 * h],
                fill="#8A6D3B", outline=INK, width=2)
    d.rectangle([sx + 0.07 * w, y + 0.64 * h, sx + 0.15 * w, y + 0.70 * h],
                outline=INK, width=2)


def art_qatar(d, x, y, w, h, bg):
    """10 Germany-Qatar 15bn deal: German and Qatari flags, two
    faceless figures shaking hands, 15BN tag."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.06 * w, y + 0.06 * h, 0.22 * w)
    # background: white distant blocks at the horizon
    for bx, bw, bh in ((0.66, 0.14, 0.14), (0.82, 0.12, 0.18)):
        d.rectangle([x + bx * w, y + 0.64 * h - bh * h,
                     x + (bx + bw) * w, y + 0.64 * h], fill="#FFFFFF",
                    outline=INK, width=2)
    ground_band(d, x, y, w, h, 0.64, "#6FB1E8")
    # midground: German flag (left) + Qatari flag (centre)
    for fx, flag in ((0.06, "de"), (0.38, "qa")):
        d.line([x + fx * w, y + 0.12 * h, x + fx * w, y + 0.60 * h],
               fill=INK, width=2)
    gx, gy = x + 0.06 * w, y + 0.12 * h
    for i, c in enumerate((INK, "#DD0000", "#FFCE00")):
        d.rectangle([gx, gy + i * 0.07 * h, gx + 0.26 * w,
                     gy + (i + 1) * 0.07 * h], fill=c, outline=INK,
                    width=1)
    qx, qy = x + 0.38 * w, y + 0.12 * h
    d.rectangle([qx, qy, qx + 0.16 * w, qy + 0.21 * h], fill="#8A1538",
                outline=INK, width=2)
    for i in range(3):
        d.polygon([(qx, qy + i * 0.07 * h),
                   (qx + 0.05 * w, qy + (i + 0.5) * 0.07 * h),
                   (qx, qy + (i + 1) * 0.07 * h)], fill="#FFFFFF")
    # foreground: two faceless figures shaking hands
    fig(d, x + 0.24 * w, y + 0.74 * h, 0.28 * h)
    fig(d, x + 0.44 * w, y + 0.74 * h, 0.28 * h)
    d.line([x + 0.28 * w, y + 0.58 * h, x + 0.40 * w, y + 0.58 * h],
           fill=INK, width=3)
    spark(d, x + 0.34 * w, y + 0.52 * h, col="#FFFFFF")
    # 15BN tag on the ground
    d.rectangle([x + 0.10 * w, y + 0.78 * h, x + 0.58 * w, y + 0.94 * h],
                fill="#FFFFFF", outline=INK, width=2)
    d.text((x + 0.15 * w, y + 0.81 * h), "\u20ac15BN",
           font=F(SANS_B, max(8, int(w * 0.11))), fill=RED2)


def art_trump21(d, x, y, w, h, bg):
    """11 Trump limits contractor info: columns, faceless speaker
    behind a podium, mic, gavel (politics symbol)."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    # background: white columns, kept below the badge corner
    for ccx in (0.10, 0.86):
        d.rectangle([x + ccx * w - 0.04 * w, y + 0.46 * h,
                     x + ccx * w + 0.04 * w, y + 0.72 * h],
                    fill="#FFFFFF", outline=INK, width=2)
        d.rectangle([x + ccx * w - 0.06 * w, y + 0.42 * h,
                     x + ccx * w + 0.06 * w, y + 0.46 * h],
                    fill="#FFFFFF", outline=INK, width=2)
    ground_band(d, x, y, w, h, 0.72, "#E88AA8")
    # midground: faceless speaker silhouette (navy suit, red tie)
    cx = x + 0.33 * w
    d.ellipse([cx - 0.08 * h, y + 0.42 * h, cx + 0.08 * h, y + 0.58 * h],
              fill="#E8C9A0", outline=INK, width=2)
    d.polygon([(cx - 0.16 * h, y + 0.58 * h), (cx + 0.16 * h, y + 0.58 * h),
               (cx + 0.20 * h, y + 0.72 * h), (cx - 0.20 * h, y + 0.72 * h)],
              fill="#1B4F9C", outline=INK, width=2)
    d.polygon([(cx - 0.03 * h, y + 0.58 * h), (cx + 0.03 * h, y + 0.58 * h),
               (cx, y + 0.68 * h)], fill=RED2)
    # foreground: podium + mic + gavel
    d.rectangle([cx - 0.20 * w, y + 0.72 * h, cx + 0.20 * w, y + 0.95 * h],
                fill="#FFFFFF", outline=INK, width=2)
    d.ellipse([cx - 0.05 * h, y + 0.78 * h, cx + 0.05 * h, y + 0.88 * h],
              fill=RED2, outline=INK, width=1)
    d.line([cx + 0.14 * w, y + 0.72 * h, cx + 0.24 * w, y + 0.56 * h],
           fill="#C0C0C0", width=2)
    d.ellipse([cx + 0.20 * w, y + 0.52 * h, cx + 0.28 * w, y + 0.60 * h],
              fill=INK)
    # gavel resting on the podium's left corner
    d.rectangle([cx - 0.18 * w, y + 0.68 * h, cx - 0.10 * w, y + 0.72 * h],
                fill=INK)
    d.line([cx - 0.14 * w, y + 0.70 * h, cx - 0.08 * w, y + 0.76 * h],
           fill=INK, width=2)


def art_deal(d, x, y, w, h, bg):
    """12 Trump pushes Ukraine deal by January: US and Ukrainian
    flags, signed document with a red signature and wax seal."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.06 * w, y + 0.06 * h, 0.22 * w)
    ground_band(d, x, y, w, h, 0.64, "#E88AA8")
    # midground: US flag (left) + Ukrainian flag (centre), both
    # kept left of the badge corner
    ux, uy = x + 0.06 * w, y + 0.10 * h
    for i in range(7):
        d.rectangle([ux, uy + i * 0.03 * h, ux + 0.26 * w,
                     uy + (i + 1) * 0.03 * h],
                    fill="#FFFFFF" if i % 2 else "#B22234")
    d.rectangle([ux, uy, ux + 0.10 * w, uy + 0.09 * h], fill="#3C3B6E")
    qx, qy = x + 0.38 * w, y + 0.10 * h
    d.rectangle([qx, qy, qx + 0.16 * w, qy + 0.10 * h], fill="#005BBB",
                outline=INK, width=1)
    d.rectangle([qx, qy + 0.10 * h, qx + 0.16 * w, qy + 0.20 * h],
                fill="#FFD500", outline=INK, width=1)
    # foreground: signed document with shadow, pens, wax seal
    d.rectangle([x + 0.18 * w, y + 0.44 * h, x + 0.56 * w, y + 0.82 * h],
                fill="#D8D8D8")
    d.rectangle([x + 0.16 * w, y + 0.42 * h, x + 0.54 * w, y + 0.80 * h],
                fill="#FFFFFF", outline=INK, width=2)
    for ly in (0.50, 0.56, 0.62):
        d.line([x + 0.20 * w, y + ly * h, x + 0.50 * w, y + ly * h],
               fill="#8A8A8A", width=2)
    d.line([(x + 0.20 * w, y + 0.74 * h), (x + 0.28 * w, y + 0.70 * h),
            (x + 0.36 * w, y + 0.75 * h), (x + 0.48 * w, y + 0.69 * h)],
           fill=RED2, width=2)
    d.ellipse([x + 0.44 * w, y + 0.70 * h, x + 0.52 * w, y + 0.78 * h],
              fill=RED2, outline=INK, width=1)
    d.line([x + 0.58 * w, y + 0.84 * h, x + 0.72 * w, y + 0.72 * h],
           fill="#1B4F9C", width=3)
    d.line([x + 0.60 * w, y + 0.86 * h, x + 0.74 * w, y + 0.76 * h],
           fill=RED2, width=3)


def art_f1(d, x, y, w, h, bg):
    """13 F1 Las Vegas qualifying: Vegas skyline, checkered flag,
    red F1 car on the track, 1:33.893 tag. Antonelli fastest,
    5-place penalty hands pole to Verstappen."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    # background: dark Vegas skyline + Stratosphere needle, left
    d.rectangle([x + 0.16 * w, y + 0.46 * h, x + 0.30 * w, y + 0.62 * h],
                fill="#3A3A3A", outline=INK, width=2)
    windows(d, x + 0.18 * w, y + 0.48 * h, 0.10 * w, 0.12 * h, 2, 2)
    d.rectangle([x + 0.56 * w, y + 0.50 * h, x + 0.68 * w, y + 0.62 * h],
                fill="#3A3A3A", outline=INK, width=2)
    d.rectangle([x + 0.10 * w, y + 0.32 * h, x + 0.12 * w, y + 0.62 * h],
                fill="#3A3A3A", outline=INK, width=1)
    d.ellipse([x + 0.07 * w, y + 0.28 * h, x + 0.15 * w, y + 0.34 * h],
              fill="#3A3A3A", outline=INK, width=1)
    # checkered flag on a pole, top left
    d.line([x + 0.34 * w, y + 0.14 * h, x + 0.34 * w, y + 0.46 * h],
           fill=INK, width=2)
    for i in range(3):
        for j in range(2):
            d.rectangle([x + (0.34 + i * 0.06) * w, y + (0.14 + j * 0.06) * h,
                         x + (0.40 + i * 0.06) * w,
                         y + (0.20 + j * 0.06) * h],
                        fill=INK if (i + j) % 2 == 0 else "#FFFFFF",
                        outline=INK, width=1)
    # track: dark asphalt band with a red/white kerb on its edge
    ground_band(d, x, y, w, h, 0.62, "#3A3A3A")
    for i in range(8):
        d.rectangle([x + (0.06 + i * 0.11) * w, y + 0.62 * h,
                     x + (0.17 + i * 0.11) * w, y + 0.66 * h],
                    fill=RED2 if i % 2 == 0 else "#FFFFFF")
    for dx in (0.10, 0.34, 0.58, 0.82):
        d.line([x + dx * w, y + 0.82 * h, x + (dx + 0.08) * w,
                y + 0.82 * h], fill="#FFFFFF", width=3)
    # midground: red F1 car at one third across, with its shadow
    d.ellipse([x + 0.10 * w, y + 0.64 * h, x + 0.56 * w, y + 0.70 * h],
              fill="#262626")
    cx = x + 0.33 * w
    d.polygon([(cx - 0.23 * w, y + 0.60 * h), (cx - 0.17 * w, y + 0.54 * h),
               (cx - 0.03 * w, y + 0.52 * h), (cx + 0.11 * w, y + 0.54 * h),
               (cx + 0.21 * w, y + 0.58 * h), (cx + 0.19 * w, y + 0.62 * h),
               (cx - 0.21 * w, y + 0.62 * h)], fill=RED2, outline=INK,
              width=2)
    d.rectangle([cx + 0.17 * w, y + 0.46 * h, cx + 0.21 * w, y + 0.54 * h],
                fill=RED2, outline=INK, width=1)
    d.ellipse([cx - 0.04 * h, y + 0.48 * h, cx + 0.04 * h, y + 0.56 * h],
              fill="#FFFFFF", outline=INK, width=1)
    for wx in (cx - 0.15 * w, cx + 0.13 * w):
        d.ellipse([wx - 0.055 * h, y + 0.60 * h, wx + 0.055 * h,
                   y + 0.71 * h], fill=INK, outline="#FFFFFF", width=1)
    # speed lines behind the car, right side below the badge corner
    for sy in (0.52, 0.57):
        d.line([x + 0.58 * w, y + sy * h, x + 0.72 * w, y + sy * h],
               fill="#FFD23D", width=2)
    spark(d, x + 0.60 * w, y + 0.48 * h, col="#FFFFFF")
    # foreground: 1:33.893 tag on the track
    d.rectangle([x + 0.08 * w, y + 0.80 * h, x + 0.72 * w, y + 0.96 * h],
                fill="#FFFFFF", outline=INK, width=2)
    d.text((x + 0.12 * w, y + 0.82 * h), "1:33.893",
           font=F(SANS_B, max(8, int(w * 0.11))), fill=RED2)


def art_nvidia(d, x, y, w, h, bg):
    """14 Nvidia -14% to a 52-week low: green NVDA chip with pins,
    red down arrow, red falling bars on the ground."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    # background: white circuit traces, top left
    d.line([x + 0.06 * w, y + 0.10 * h, x + 0.40 * w, y + 0.10 * h],
           fill="#FFFFFF", width=2)
    d.line([x + 0.40 * w, y + 0.10 * h, x + 0.40 * w, y + 0.22 * h],
           fill="#FFFFFF", width=2)
    d.ellipse([x + 0.06 * w - 3, y + 0.10 * h - 3, x + 0.06 * w + 3,
               y + 0.10 * h + 3], fill="#FFFFFF")
    ground_band(d, x, y, w, h, 0.64, "#E88AA8")
    # midground: green chip with a deeper-green shadow, upper left
    d.rectangle([x + 0.10 * w, y + 0.16 * h, x + 0.52 * w, y + 0.44 * h],
                fill="#1A8A4D")
    d.rectangle([x + 0.08 * w, y + 0.14 * h, x + 0.50 * w, y + 0.42 * h],
                fill="#22B573", outline="#FFFFFF", width=3)
    for py in (0.20, 0.28, 0.36):
        d.line([x + 0.04 * w, y + py * h, x + 0.08 * w, y + py * h],
               fill="#FFFFFF", width=2)
        d.line([x + 0.50 * w, y + py * h, x + 0.54 * w, y + py * h],
               fill="#FFFFFF", width=2)
    d.text((x + 0.14 * w, y + 0.24 * h), "NVDA",
           font=F(SANS_B, max(8, int(w * 0.11))), fill="#FFFFFF")
    # red down arrow (economy symbol), lower right
    d.line([x + 0.66 * w, y + 0.48 * h, x + 0.66 * w, y + 0.74 * h],
           fill=RED2, width=5)
    d.polygon([(x + 0.66 * w, y + 0.84 * h), (x + 0.56 * w, y + 0.68 * h),
               (x + 0.76 * w, y + 0.68 * h)], fill=RED2)
    # foreground: small red falling bars, bottom left
    for i, bh in enumerate((0.16, 0.12, 0.08)):
        bx = x + (0.08 + i * 0.12) * w
        d.rectangle([bx, y + 0.92 * h - bh * h, bx + 0.08 * w,
                     y + 0.92 * h], fill=RED2, outline="#8E2B20", width=1)


def art_liq(d, x, y, w, h, bg):
    """15 Crypto liquidations top $2.53bn: red down chart line,
    three gold coins falling with motion streaks."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.06 * w, y + 0.08 * h, 0.26 * w)
    ground_band(d, x, y, w, h, 0.64, "#5BC8BC")
    # midground: red down chart line (economy symbol)
    d.line([(x + 0.08 * w, y + 0.24 * h), (x + 0.52 * w, y + 0.56 * h)],
           fill=RED2, width=4)
    d.polygon([(x + 0.52 * w, y + 0.56 * h), (x + 0.42 * w, y + 0.54 * h),
               (x + 0.50 * w, y + 0.64 * h)], fill=RED2)
    # foreground: falling gold coins with shadows + motion streaks
    for (ccx, ccy, cr) in ((0.33, 0.44, 0.15), (0.14, 0.70, 0.10),
                           (0.54, 0.74, 0.09)):
        cx, cy = x + ccx * w, y + ccy * h
        d.ellipse([cx - cr * h, cy + cr * h * 0.9, cx + cr * h,
                   cy + cr * h * 1.2], fill="#4AA89E")
        d.ellipse([cx - cr * h + 0.015 * h, cy - cr * h + 0.015 * h,
                   cx + cr * h + 0.015 * h, cy + cr * h + 0.015 * h],
                  fill="#B26A00")
        d.ellipse([cx - cr * h, cy - cr * h, cx + cr * h, cy + cr * h],
                  fill="#F7931A", outline="#B26A00", width=2)
        f = F(SANS_B, max(8, int(cr * h * 0.9)))
        t = "B"
        d.text((cx - d.textlength(t, font=f) / 2, cy - cr * h * 0.55), t,
               font=f, fill="#FFFFFF")
    for sx, sy in ((0.20, 0.30), (0.48, 0.60)):
        d.line([x + sx * w, y + sy * h, x + (sx + 0.10) * w,
                y + (sy + 0.06) * h], fill="#FFFFFF", width=2)


def art_tokyo(d, x, y, w, h, bg):
    """16 Asian markets tumble: red sun, orange Tokyo tower,
    white side blocks, red falling bars."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    # background: red sun + small cloud, top left/centre
    d.ellipse([x + 0.07 * w, y + 0.07 * h, x + 0.25 * w, y + 0.25 * h],
              fill=RED2, outline="#8E2B20", width=2)
    cloud(d, x + 0.38 * w, y + 0.08 * h, 0.18 * w)
    ground_band(d, x, y, w, h, 0.64, "#5ED8A0")
    # midground: Tokyo tower at one third across, with its shadow
    d.ellipse([x + 0.16 * w, y + 0.62 * h, x + 0.50 * w, y + 0.68 * h],
              fill="#4AB882")
    cx = x + 0.33 * w
    d.polygon([(cx - 0.20 * w, y + 0.64 * h), (cx - 0.04 * w, y + 0.28 * h),
               (cx + 0.04 * w, y + 0.28 * h), (cx + 0.20 * w, y + 0.64 * h)],
              fill="#E86A1A", outline="#8E2B20", width=2)
    d.line([cx, y + 0.28 * h, cx, y + 0.20 * h], fill="#8E2B20", width=2)
    for ly in (0.40, 0.50, 0.58):
        d.line([cx - 0.15 * w, y + ly * h, cx + 0.15 * w, y + ly * h],
               fill="#FFFFFF", width=2)
    # side blocks with windows
    for bx, bw, bh in ((0.06, 0.12, 0.14), (0.56, 0.14, 0.18)):
        d.rectangle([x + bx * w, y + 0.64 * h - bh * h,
                     x + (bx + bw) * w, y + 0.64 * h], fill="#FFFFFF",
                    outline=INK, width=2)
        windows(d, x + (bx + 0.02) * w, y + 0.64 * h - bh * h + 0.03 * h,
                (bw - 0.04) * w, (bh - 0.05) * h, 2, 1)
    # foreground: red falling bars (economy symbol), bottom right
    for i, bh in enumerate((0.14, 0.10, 0.06)):
        bx = x + (0.72 + i * 0.08) * w
        d.rectangle([bx, y + 0.92 * h - bh * h, bx + 0.05 * w,
                     y + 0.92 * h], fill=RED2, outline="#8E2B20", width=1)


def art_frankfurt(d, x, y, w, h, bg):
    """17 European stocks close lower: big euro sign, white
    skyline, red down arrow, red falling bars."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    # background: big navy euro sign, top left
    d.text((x + 0.08 * w, y + 0.04 * h), "\u20ac",
           font=F(SANS_B, max(16, int(w * 0.34))), fill="#1B4F9C")
    cloud(d, x + 0.38 * w, y + 0.08 * h, 0.18 * w)
    ground_band(d, x, y, w, h, 0.64, "#6FB1E8")
    # midground: white skyline with navy windows
    for bx, bw, bh in ((0.06, 0.16, 0.20), (0.26, 0.14, 0.28),
                       (0.44, 0.16, 0.16), (0.62, 0.14, 0.24)):
        d.rectangle([x + bx * w, y + 0.64 * h - bh * h,
                     x + (bx + bw) * w, y + 0.64 * h], fill="#FFFFFF",
                    outline=INK, width=2)
        windows(d, x + (bx + 0.02) * w, y + 0.64 * h - bh * h + 0.03 * h,
                (bw - 0.04) * w, (bh - 0.05) * h, 2, 2, col="#1B4F9C")
    # foreground: red down arrow (economy symbol) + falling bars
    d.line([x + 0.86 * w, y + 0.46 * h, x + 0.86 * w, y + 0.70 * h],
           fill=RED2, width=4)
    d.polygon([(x + 0.86 * w, y + 0.78 * h), (x + 0.78 * w, y + 0.66 * h),
               (x + 0.94 * w, y + 0.66 * h)], fill=RED2)
    for i, bh in enumerate((0.12, 0.09, 0.06)):
        bx = x + (0.08 + i * 0.10) * w
        d.rectangle([bx, y + 0.92 * h - bh * h, bx + 0.06 * w,
                     y + 0.92 * h], fill=RED2, outline="#8E2B20", width=1)


def art_quake_banda(d, x, y, w, h, bg):
    """18 Banda Sea M6.8 quake: warning triangle, cracked slab on
    the sea, island at the horizon, seismograph strip."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.06 * w, y + 0.08 * h, 0.26 * w)
    cloud(d, x + 0.38 * w, y + 0.06 * h, 0.18 * w)
    # background: brown island hill at the horizon, right
    d.polygon([(x + 0.60 * w, y + 0.60 * h), (x + 0.72 * w, y + 0.48 * h),
               (x + 0.84 * w, y + 0.60 * h)], fill="#C9A86A",
              outline=INK, width=2)
    ground_band(d, x, y, w, h, 0.60, SEA)
    waves(d, x, y + 0.64 * h, w, 8)
    waves(d, x + 0.20 * w, y + 0.74 * h, w - 0.20 * w, 6)
    # midground: warning triangle (disaster symbol) + cracked slab
    warn(d, x + 0.30 * w, y + 0.32 * h, 0.12 * h)
    d.rectangle([x + 0.12 * w, y + 0.60 * h, x + 0.54 * w, y + 0.72 * h],
                fill="#C9A86A", outline=INK, width=2)
    d.line([(x + 0.22 * w, y + 0.60 * h), (x + 0.30 * w, y + 0.66 * h),
            (x + 0.26 * w, y + 0.72 * h)], fill=INK, width=2)
    d.line([(x + 0.40 * w, y + 0.60 * h), (x + 0.36 * w, y + 0.66 * h),
            (x + 0.44 * w, y + 0.72 * h)], fill=INK, width=2)
    # foreground: seismograph strip with a red zigzag
    d.rectangle([x + 0.08 * w, y + 0.80 * h, x + 0.92 * w, y + 0.94 * h],
                fill="#FFFFFF", outline=INK, width=2)
    d.line([(x + 0.12 * w, y + 0.87 * h), (x + 0.24 * w, y + 0.87 * h),
            (x + 0.30 * w, y + 0.82 * h), (x + 0.36 * w, y + 0.92 * h),
            (x + 0.44 * w, y + 0.83 * h), (x + 0.50 * w, y + 0.91 * h),
            (x + 0.58 * w, y + 0.87 * h), (x + 0.88 * w, y + 0.87 * h)],
           fill=RED2, width=2)


def art_quake_qinghai(d, x, y, w, h, bg):
    """19 Qinghai quake: warning triangle, snow-capped mountains,
    cracked ground, red seismograph zigzag."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    # background: warning triangle (disaster symbol), top left
    warn(d, x + 0.14 * w, y + 0.18 * h, 0.11 * h)
    cloud(d, x + 0.40 * w, y + 0.08 * h, 0.20 * w)
    # midground: two snow-capped mountains at one third across
    d.polygon([(x + 0.04 * w, y + 0.62 * h), (x + 0.30 * w, y + 0.22 * h),
               (x + 0.56 * w, y + 0.62 * h)], fill="#8A8A8A",
              outline=INK, width=2)
    d.polygon([(x + 0.30 * w, y + 0.22 * h), (x + 0.22 * w, y + 0.34 * h),
               (x + 0.30 * w, y + 0.30 * h), (x + 0.38 * w, y + 0.34 * h)],
              fill="#FFFFFF")
    d.polygon([(x + 0.44 * w, y + 0.62 * h), (x + 0.68 * w, y + 0.30 * h),
               (x + 0.92 * w, y + 0.62 * h)], fill="#6A6A6A",
              outline=INK, width=2)
    d.polygon([(x + 0.68 * w, y + 0.30 * h), (x + 0.62 * w, y + 0.40 * h),
               (x + 0.68 * w, y + 0.37 * h), (x + 0.74 * w, y + 0.40 * h)],
              fill="#FFFFFF")
    # foreground: cracked brown ground + red seismograph zigzag
    ground_band(d, x, y, w, h, 0.62, "#C9A86A")
    d.line([(x + 0.30 * w, y + 0.62 * h), (x + 0.38 * w, y + 0.70 * h),
            (x + 0.32 * w, y + 0.78 * h)], fill=INK, width=2)
    d.line([(x + 0.62 * w, y + 0.62 * h), (x + 0.56 * w, y + 0.70 * h),
            (x + 0.66 * w, y + 0.78 * h)], fill=INK, width=2)
    d.line([(x + 0.08 * w, y + 0.88 * h), (x + 0.26 * w, y + 0.88 * h),
            (x + 0.32 * w, y + 0.83 * h), (x + 0.38 * w, y + 0.93 * h),
            (x + 0.46 * w, y + 0.84 * h), (x + 0.52 * w, y + 0.92 * h),
            (x + 0.60 * w, y + 0.88 * h), (x + 0.92 * w, y + 0.88 * h)],
           fill=RED2, width=2)


def art_xavier21(d, x, y, w, h, bg):
    """20 Cyclone Xavier weakens to Cat 1: cloud + weakening
    spiral, palm island, emergency flag, waves."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.06 * w, y + 0.08 * h, 0.26 * w)
    # midground: weakening spiral (weather symbol) at one third
    spiral(d, x + 0.33 * w, y + 0.32 * h, 0.15 * h)
    ground_band(d, x, y, w, h, 0.64, SEA)
    waves(d, x, y + 0.68 * h, w, 8)
    waves(d, x + 0.20 * w, y + 0.80 * h, w - 0.20 * w, 6)
    # foreground: palm island with a shadow, emergency flag right
    d.ellipse([x + 0.08 * w, y + 0.76 * h, x + 0.52 * w, y + 0.90 * h],
              fill="#5EE6A8", outline="#1FA36B", width=3)
    d.polygon([(x + 0.28 * w, y + 0.78 * h), (x + 0.31 * w, y + 0.78 * h),
               (x + 0.32 * w, y + 0.62 * h), (x + 0.29 * w, y + 0.62 * h)],
              fill="#1FA36B")
    for a in (-40, 0, 40):
        rad = math.radians(a - 90)
        d.line([x + 0.30 * w, y + 0.62 * h,
                x + 0.30 * w + 0.11 * w * math.cos(rad),
                y + 0.62 * h + 0.09 * h * math.sin(rad)], fill="#1FA36B",
               width=3)
    d.line([x + 0.72 * w, y + 0.58 * h, x + 0.72 * w, y + 0.86 * h],
           fill=INK, width=2)
    d.polygon([(x + 0.72 * w, y + 0.58 * h), (x + 0.86 * w, y + 0.63 * h),
               (x + 0.72 * w, y + 0.68 * h)], fill=RED2, outline=INK,
              width=1)


def art_measles(d, x, y, w, h, bg):
    """21 US measles: white clinic with a red cross, warning
    triangle (health/disaster symbol), masked doctor silhouette,
    virus dots, 5,838 tag. CDC update Fri 20 Nov, first
    reported Sat 21 Nov."""
    d.rectangle([x, y, x + w, y + h], fill=bg)
    cloud(d, x + 0.06 * w, y + 0.07 * h, 0.24 * w)
    # background: white clinic block with a red-cross sign, right
    d.rectangle([x + 0.62 * w, y + 0.46 * h, x + 0.92 * w, y + 0.64 * h],
                fill="#FFFFFF", outline=INK, width=2)
    windows(d, x + 0.65 * w, y + 0.50 * h, 0.24 * w, 0.10 * h, 3, 1)
    d.rectangle([x + 0.72 * w, y + 0.36 * h, x + 0.82 * w, y + 0.46 * h],
                fill="#FFFFFF", outline=INK, width=2)
    cx = x + 0.77 * w
    d.rectangle([cx - 0.02 * w, y + 0.38 * h, cx + 0.02 * w, y + 0.44 * h],
                fill=RED2)
    d.rectangle([cx - 0.05 * w, y + 0.40 * h, cx + 0.05 * w, y + 0.42 * h],
                fill=RED2)
    ground_band(d, x, y, w, h, 0.64, "#E88AA8")
    # midground: warning triangle at one third across
    warn(d, x + 0.33 * w, y + 0.34 * h, 0.11 * h)
    # virus dots with spikes, right of the triangle
    for vx, vy in ((0.52, 0.28), (0.58, 0.44)):
        vcx, vcy = x + vx * w, y + vy * h
        for a in range(0, 360, 45):
            rad = math.radians(a)
            d.line([vcx, vcy, vcx + 0.07 * h * math.cos(rad),
                    vcy + 0.07 * h * math.sin(rad)], fill=RED2, width=2)
        d.ellipse([vcx - 0.045 * h, vcy - 0.045 * h, vcx + 0.045 * h,
                   vcy + 0.045 * h], fill=RED2, outline="#8E2B20", width=1)
    # foreground: masked doctor silhouette at one third, with shadow
    d.ellipse([x + 0.24 * w, y + 0.88 * h, x + 0.42 * w, y + 0.94 * h],
              fill="#D67A96")
    fig(d, x + 0.33 * w, y + 0.94 * h, 0.30 * h, col="#FFFFFF")
    # surgical mask over the lower half of the face
    mcx = x + 0.33 * w
    d.rectangle([mcx - 0.05 * h, y + 0.70 * h, mcx + 0.05 * h,
                 y + 0.76 * h], fill="#FFFFFF", outline=INK, width=1)
    # 5,838 tag, bottom right (badge corner is top right)
    d.rectangle([x + 0.58 * w, y + 0.78 * h, x + 0.94 * w, y + 0.94 * h],
                fill="#FFFFFF", outline=INK, width=2)
    d.text((x + 0.62 * w, y + 0.81 * h), "5,838",
           font=F(SANS_B, max(8, int(w * 0.11))), fill=RED2)


# ---------------------------------------------------------------- map
# Bottom world map, v2: Natural Earth 110m land polygons (NE_LAND,
# embedded lon/lat, antimeridian-split, Douglas-Peucker 0.3 deg,
# clipped to lat [-50, 75] -- Antarctica dropped, Greenland cut at
# 75N), drawn with the Equal Earth projection (_equal_earth) fitted
# to the land box. Same frame, header strip, dashed graticule, land
# colour (#6ED598), dark-green 1px coastline, pink numbered dots
# (r=7) as before. Dots are projected from real lat/lon
# (MAP_DOTS_LATLON) through the same projection; MAP_DOT_NUDGE holds
# the minimal de-collision nudges (<= ~10px) where two projected
# centres would overlap or a dot would fall in the sea -- every dot
# was checked to sit on land except 18 (Banda Sea, sea by design)
# and 20 (Pago Pago, whose island is too small for 110m data and
# sits at the left edge, lon -170.7, by the dateline). No hand-drawn
# continents, no country borders any more: the old white internal
# borders were hand-drawn in the schematic frame and cannot be
# re-projected. Data source: ne_110m_land.geojson from the
# natural-earth-vector repo (CC0/public domain data), downloaded
# once and embedded -- no network at draw time.
MAP_W = 346
MAP_H = 252
MAP_SCALE = 0.6  # v3: the world is drawn at 60% of its v2 size
NE_LAND = [[(70.28, -49.71), (68.75, -49.77), (68.94, -48.62), (70.56, -49.26), (70.28, -49.71)], [(145.4, -40.79), (146.36, -41.14), (148.29, -40.88), (147.91, -43.21), (147.56, -42.94), (146.87, -43.63), (146.05, -43.55), (144.74, -40.7), (145.4, -40.79)], [(173.02, -40.92), (173.25, -41.33), (173.96, -40.93), (174.25, -41.35), (172.71, -43.37), (173.08, -43.85), (171.45, -44.24), (170.62, -45.91), (169.33, -46.64), (166.68, -46.22), (167.05, -45.11), (170.52, -43.03), (172.8, -40.49), (173.02, -40.92)], [(174.61, -36.16), (175.34, -37.21), (175.36, -36.53), (175.96, -37.56), (176.76, -37.88), (178.52, -37.7), (177.97, -39.17), (177.21, -39.15), (176.01, -41.29), (175.24, -41.69), (174.65, -41.28), (175.23, -40.46), (174.9, -39.91), (173.82, -39.51), (174.57, -38.8), (174.7, -37.38), (172.64, -34.53), (174.33, -35.27), (174.61, -36.16)], [(167.12, -22.16), (166.74, -22.4), (165.47, -21.68), (164.03, -20.11), (166.6, -21.7), (167.12, -22.16)], [(178.37, -17.34), (178.55, -18.15), (177.38, -18.16), (177.67, -17.38), (178.13, -17.5), (178.37, -17.34)], [(179.36, -16.8), (178.73, -17.01), (178.6, -16.64), (180.0, -16.07), (180.0, -16.56), (179.36, -16.8)], [(167.84, -16.47), (167.52, -16.6), (167.22, -15.89), (167.84, -16.47)], [(167.11, -14.93), (167.27, -15.74), (166.79, -15.67), (166.63, -14.63), (167.11, -14.93)], [(50.06, -13.56), (50.38, -15.71), (49.67, -15.71), (49.77, -16.88), (47.1, -24.94), (45.41, -25.6), (44.04, -24.99), (43.25, -22.06), (44.37, -20.07), (43.96, -17.41), (44.45, -16.22), (46.31, -15.78), (47.71, -14.59), (47.87, -13.66), (48.29, -13.78), (49.19, -12.04), (49.81, -12.9), (50.06, -13.56)], [(143.56, -13.76), (143.92, -14.55), (144.56, -14.17), (145.37, -14.98), (146.39, -18.96), (148.85, -20.39), (149.68, -22.34), (150.73, -22.4), (150.9, -23.46), (152.86, -25.27), (153.14, -26.07), (153.57, -28.11), (152.89, -31.64), (150.33, -35.67), (150.0, -37.43), (148.3, -37.81), (146.32, -39.04), (144.88, -38.42), (145.03, -37.9), (143.61, -38.81), (140.64, -38.02), (139.57, -36.14), (138.12, -35.61), (138.21, -34.38), (137.72, -35.08), (136.83, -35.26), (137.89, -33.64), (137.81, -32.9), (135.99, -34.89), (135.21, -34.48), (134.27, -32.62), (131.33, -31.5), (126.15, -32.22), (124.22, -32.96), (123.66, -33.89), (119.89, -33.98), (118.02, -35.06), (116.63, -35.03), (115.03, -34.2), (115.05, -33.62), (115.71, -33.26), (115.69, -31.61), (113.34, -26.12), (113.78, -26.55), (113.44, -25.62), (114.23, -26.3), (113.39, -24.38), (114.15, -21.76), (114.23, -22.52), (114.65, -21.83), (116.71, -20.7), (120.86, -19.68), (122.24, -18.2), (122.31, -17.25), (123.01, -16.41), (123.43, -17.27), (123.86, -17.07), (123.5, -16.6), (123.82, -16.11), (124.26, -16.33), (124.38, -15.57), (125.69, -14.23), (127.07, -13.82), (128.36, -14.87), (129.62, -14.97), (129.41, -14.42), (130.62, -12.54), (132.58, -12.11), (132.56, -11.6), (131.82, -11.27), (135.3, -12.25), (136.49, -11.86), (136.95, -12.35), (135.96, -13.32), (135.5, -15.0), (140.22, -17.71), (140.88, -17.37), (141.27, -16.39), (141.69, -12.41), (142.52, -10.67), (143.6, -13.4), (143.56, -13.76)], [(162.12, -10.48), (162.4, -10.83), (161.7, -10.82), (161.32, -10.2), (161.92, -10.45), (162.12, -10.48)], [(120.72, -10.24), (118.97, -9.56), (119.9, -9.36), (120.78, -9.97), (120.72, -10.24)], [(160.85, -9.87), (159.85, -9.79), (159.7, -9.24), (160.69, -9.61), (160.85, -9.87)], [(161.68, -9.6), (160.58, -8.32), (161.28, -9.12), (161.68, -9.6)], [(124.44, -10.14), (123.46, -10.24), (123.98, -9.29), (125.09, -8.66), (127.34, -8.4), (125.09, -9.39), (124.44, -10.14)], [(117.9, -8.1), (119.13, -8.71), (116.74, -9.03), (117.63, -8.45), (117.9, -8.1)], [(122.9, -8.09), (122.76, -8.65), (119.92, -8.81), (120.72, -8.24), (122.01, -8.46), (122.9, -8.09)], [(159.88, -8.34), (158.21, -7.42), (159.64, -8.02), (159.88, -8.34)], [(157.54, -7.35), (156.54, -6.6), (157.14, -7.02), (157.54, -7.35)], [(108.62, -6.78), (110.54, -6.88), (110.76, -6.47), (115.71, -8.37), (114.56, -8.75), (108.28, -7.77), (105.37, -6.85), (106.05, -5.9), (108.49, -6.42), (108.62, -6.78)], [(134.72, -6.21), (134.21, -6.9), (134.11, -6.14), (134.5, -5.45), (134.73, -5.74), (134.72, -6.21)], [(155.88, -6.82), (155.17, -6.54), (154.51, -5.14), (156.02, -6.54), (155.88, -6.82)], [(151.98, -5.48), (150.24, -6.32), (148.32, -5.75), (149.85, -5.51), (150.14, -5.0), (150.24, -5.53), (150.81, -5.46), (151.65, -4.76), (151.54, -4.17), (152.34, -4.31), (152.32, -4.87), (151.98, -5.48)], [(127.25, -3.46), (126.87, -3.79), (125.99, -3.18), (127.0, -3.13), (127.25, -3.46)], [(130.47, -3.09), (130.83, -3.86), (127.9, -3.39), (128.14, -2.84), (129.37, -2.8), (130.47, -3.09)], [(153.14, -4.5), (152.83, -4.77), (152.41, -3.79), (150.66, -2.74), (151.48, -2.78), (153.02, -3.98), (153.14, -4.5)], [(134.14, -1.15), (134.42, -2.77), (135.46, -3.37), (136.29, -2.31), (138.33, -1.7), (144.58, -3.86), (145.98, -5.47), (147.65, -6.08), (147.89, -6.61), (146.97, -6.72), (147.19, -7.39), (150.69, -10.58), (147.91, -10.13), (146.05, -8.07), (144.74, -7.63), (143.29, -8.25), (143.41, -8.98), (142.63, -9.33), (141.03, -9.12), (140.14, -8.3), (139.13, -8.1), (137.61, -8.41), (138.67, -7.32), (137.93, -5.39), (133.66, -3.54), (132.98, -4.11), (132.75, -3.31), (131.99, -2.82), (133.7, -2.21), (132.23, -2.21), (130.52, -0.94), (132.38, -0.37), (133.99, -0.78), (134.14, -1.15)], [(125.24, 1.42), (124.44, 0.43), (123.69, 0.24), (120.18, 0.24), (120.04, -0.52), (120.94, -1.41), (123.34, -0.62), (123.26, -1.08), (122.82, -0.93), (121.51, -1.9), (123.16, -5.34), (122.63, -5.63), (122.24, -5.28), (122.72, -4.46), (121.49, -4.57), (121.62, -4.19), (120.9, -3.6), (120.97, -2.63), (120.31, -2.93), (120.43, -5.53), (119.37, -5.38), (119.5, -3.49), (118.77, -2.8), (120.04, 0.57), (120.89, 1.31), (124.08, 0.92), (125.07, 1.64), (125.24, 1.42)], [(128.69, 1.13), (128.64, 0.26), (128.12, 0.36), (128.1, -0.9), (127.4, 1.01), (127.93, 2.17), (128.0, 1.63), (128.59, 1.54), (128.69, 1.13)], [(105.82, -5.85), (104.71, -5.87), (102.58, -4.22), (99.26, 0.18), (98.6, 1.82), (95.29, 5.48), (97.48, 5.25), (100.64, 2.1), (101.66, 2.08), (102.5, 1.4), (103.84, 0.1), (103.44, -0.71), (104.37, -1.08), (104.89, -2.34), (106.11, -3.06), (105.86, -4.31), (105.82, -5.85)], [(117.88, 1.83), (119.0, 0.9), (117.81, 0.78), (117.52, -0.8), (116.56, -1.49), (116.15, -4.01), (116.0, -3.66), (114.86, -4.11), (114.47, -3.5), (113.26, -3.12), (112.07, -3.48), (111.7, -2.99), (110.22, -2.93), (110.07, -1.59), (109.09, -0.46), (109.07, 1.34), (109.66, 2.01), (111.17, 1.85), (111.37, 2.7), (113.0, 3.1), (116.73, 6.92), (119.18, 5.41), (117.31, 3.23), (118.05, 2.29), (117.88, 1.83)], [(126.38, 8.41), (126.54, 7.19), (126.2, 6.27), (125.83, 7.29), (125.36, 6.79), (125.4, 5.58), (124.22, 6.16), (124.24, 7.36), (123.61, 7.83), (122.09, 6.9), (121.92, 7.19), (122.31, 8.03), (123.49, 8.69), (123.84, 8.24), (125.47, 8.99), (125.41, 9.76), (126.31, 8.78), (126.38, 8.41)], [(81.22, 6.2), (80.35, 5.97), (79.87, 6.76), (79.7, 8.2), (80.15, 9.82), (81.79, 7.52), (81.64, 6.48), (81.22, 6.2)], [(-60.94, 10.11), (-61.95, 10.09), (-61.68, 10.76), (-60.9, 10.86), (-60.94, 10.11)], [(123.98, 10.28), (123.0, 9.02), (122.38, 9.71), (122.95, 10.88), (123.5, 10.94), (123.34, 10.27), (124.08, 11.23), (123.98, 10.28)], [(118.5, 9.32), (117.17, 8.37), (119.51, 11.37), (119.69, 10.55), (119.03, 10.0), (118.5, 9.32)], [(121.88, 11.89), (123.12, 11.58), (122.0, 10.44), (122.04, 11.42), (121.88, 11.89)], [(125.5, 12.16), (125.78, 11.05), (125.01, 11.31), (125.28, 10.36), (124.8, 10.13), (124.3, 11.5), (124.89, 11.42), (124.88, 11.79), (124.27, 12.56), (125.23, 12.54), (125.5, 12.16)], [(121.53, 13.07), (121.26, 12.21), (120.32, 13.47), (121.18, 13.43), (121.53, 13.07)], [(121.32, 18.5), (122.25, 18.48), (122.52, 17.09), (121.66, 15.93), (121.73, 14.33), (123.95, 13.78), (124.08, 12.54), (122.93, 13.55), (122.67, 13.19), (122.03, 13.78), (120.63, 13.86), (120.99, 14.53), (120.69, 14.76), (120.56, 14.4), (120.07, 14.97), (119.88, 16.36), (120.29, 16.03), (120.72, 18.51), (121.32, 18.5)], [(-65.59, 18.23), (-67.18, 17.95), (-67.1, 18.52), (-65.77, 18.43), (-65.59, 18.23)], [(-76.9, 17.87), (-78.34, 18.23), (-76.9, 18.4), (-76.2, 17.89), (-76.9, 17.87)], [(-72.58, 19.87), (-69.95, 19.65), (-68.32, 18.61), (-68.69, 18.21), (-70.67, 18.43), (-71.4, 17.6), (-72.37, 18.21), (-73.92, 18.03), (-74.37, 18.66), (-72.33, 18.67), (-72.78, 19.48), (-73.42, 19.64), (-73.19, 19.92), (-72.58, 19.87)], [(110.34, 18.68), (109.48, 18.2), (108.66, 18.51), (108.63, 19.37), (110.79, 20.08), (111.01, 19.7), (110.57, 19.26), (110.34, 18.68)], [(-155.54, 19.08), (-155.94, 19.06), (-155.86, 20.27), (-154.81, 19.51), (-155.22, 19.24), (-155.54, 19.08)], [(-156.08, 20.64), (-156.71, 20.93), (-156.0, 20.76), (-156.08, 20.64)], [(-157.65, 21.32), (-158.13, 21.31), (-157.94, 21.65), (-157.65, 21.32)], [(-159.35, 21.98), (-159.8, 22.07), (-159.37, 22.21), (-159.35, 21.98)], [(-79.68, 22.77), (-78.35, 22.51), (-75.67, 20.74), (-74.18, 20.28), (-77.76, 19.86), (-77.09, 20.41), (-78.14, 20.74), (-78.72, 21.6), (-82.17, 22.39), (-81.8, 22.64), (-84.97, 21.9), (-83.27, 22.98), (-80.62, 23.11), (-79.68, 22.77)], [(-77.53, 23.76), (-78.41, 24.58), (-78.19, 25.21), (-77.54, 24.34), (-77.53, 23.76)], [(121.18, 22.79), (120.75, 21.97), (120.11, 23.56), (121.5, 25.3), (121.95, 25.0), (121.78, 24.39), (121.18, 22.79)], [(-77.82, 26.58), (-78.91, 26.42), (-78.98, 26.79), (-77.85, 26.84), (-77.82, 26.58)], [(-77.0, 26.59), (-77.17, 25.88), (-77.79, 27.04), (-77.0, 26.59)], [(134.64, 34.15), (134.2, 33.2), (133.79, 33.52), (133.01, 32.7), (132.36, 32.99), (132.92, 34.06), (133.9, 34.36), (134.64, 34.15)], [(34.58, 35.67), (32.98, 34.57), (32.26, 35.1), (33.67, 35.37), (34.58, 35.67)], [(23.7, 35.71), (26.29, 35.3), (24.72, 34.92), (23.51, 35.28), (23.7, 35.71)], [(15.52, 38.23), (15.1, 36.62), (12.43, 37.61), (12.57, 38.13), (14.76, 38.14), (15.52, 38.23)], [(9.21, 41.21), (9.81, 40.5), (9.67, 39.18), (8.81, 38.91), (8.16, 40.95), (8.71, 40.9), (9.21, 41.21)], [(140.98, 37.14), (140.25, 35.14), (137.22, 34.61), (135.79, 33.46), (135.12, 33.85), (135.08, 34.6), (130.99, 33.89), (132.0, 33.15), (131.33, 31.45), (130.69, 31.03), (130.2, 31.42), (130.45, 32.32), (129.41, 33.3), (132.62, 35.43), (135.68, 35.53), (136.72, 37.3), (137.39, 36.83), (139.43, 38.22), (140.05, 39.44), (139.88, 40.56), (140.31, 41.2), (141.37, 41.38), (141.88, 39.18), (140.96, 38.17), (140.98, 37.14)], [(9.56, 42.15), (9.23, 41.38), (8.54, 42.26), (9.39, 43.01), (9.56, 42.15)], [(143.91, 44.17), (144.61, 43.96), (145.32, 44.38), (145.54, 43.26), (144.06, 42.99), (143.18, 42.0), (141.61, 42.68), (141.07, 41.58), (139.96, 41.57), (139.82, 42.56), (140.31, 43.33), (141.38, 43.39), (141.97, 45.55), (143.14, 44.51), (143.91, 44.17)], [(-63.66, 46.55), (-62.01, 46.44), (-62.87, 45.97), (-64.14, 46.39), (-64.39, 46.73), (-64.01, 47.04), (-63.66, 46.55)], [(-61.81, 49.11), (-64.52, 49.87), (-61.84, 49.29), (-61.81, 49.11)], [(-123.51, 48.51), (-125.66, 48.83), (-128.44, 50.54), (-125.76, 50.3), (-123.92, 49.06), (-123.51, 48.51)], [(-56.13, 50.69), (-56.8, 49.81), (-56.14, 50.15), (-55.47, 49.94), (-55.82, 49.59), (-53.48, 49.25), (-53.79, 48.52), (-53.09, 48.69), (-52.65, 47.54), (-53.07, 46.66), (-54.18, 46.81), (-54.24, 47.75), (-55.4, 46.88), (-56.0, 46.92), (-55.29, 47.39), (-56.25, 47.63), (-59.27, 47.6), (-58.8, 48.25), (-59.23, 48.52), (-57.36, 50.72), (-55.87, 51.63), (-55.41, 51.59), (-55.6, 51.32), (-56.13, 50.69)], [(-132.71, 54.04), (-131.75, 54.12), (-132.05, 52.98), (-131.18, 52.18), (-133.05, 53.41), (-133.18, 54.17), (-132.71, 54.04)], [(143.65, 50.75), (144.65, 48.98), (143.17, 49.31), (142.56, 47.86), (143.53, 46.84), (143.51, 46.14), (142.75, 46.74), (142.09, 45.97), (142.18, 50.95), (141.59, 51.94), (141.68, 53.3), (142.61, 53.76), (142.21, 54.23), (142.65, 54.37), (143.24, 51.76), (143.65, 50.75)], [(-6.79, 52.26), (-8.56, 51.67), (-9.98, 51.82), (-9.17, 52.86), (-9.69, 53.88), (-6.73, 55.17), (-5.66, 54.55), (-6.2, 53.87), (-6.03, 53.15), (-6.79, 52.26)], [(12.69, 55.61), (12.09, 54.8), (11.04, 55.36), (10.9, 55.78), (12.37, 56.11), (12.69, 55.61)], [(-153.01, 57.12), (-154.01, 56.73), (-154.67, 57.46), (-153.23, 57.97), (-152.14, 57.59), (-153.01, 57.12)], [(-3.01, 58.63), (-4.07, 57.55), (-1.96, 57.68), (-3.12, 55.97), (-2.09, 55.91), (-1.11, 54.62), (-0.43, 54.46), (0.47, 52.93), (1.68, 52.74), (1.05, 51.81), (1.45, 51.29), (0.55, 50.77), (-2.96, 50.7), (-5.25, 49.96), (-5.78, 50.16), (-3.41, 51.43), (-5.27, 51.99), (-4.22, 52.3), (-4.77, 52.84), (-4.58, 53.5), (-3.09, 53.4), (-2.95, 53.98), (-3.63, 54.62), (-4.84, 54.79), (-5.05, 55.78), (-5.59, 55.31), (-6.15, 56.79), (-5.01, 58.63), (-4.21, 58.55), (-3.01, 58.63)], [(-165.58, 59.91), (-167.46, 60.21), (-165.67, 60.29), (-165.58, 59.91)], [(-79.27, 62.16), (-79.66, 61.63), (-80.36, 62.02), (-79.52, 62.36), (-79.27, 62.16)], [(-81.9, 62.71), (-83.07, 62.16), (-83.99, 62.45), (-81.88, 62.9), (-81.9, 62.71)], [(-171.73, 63.78), (-168.69, 63.3), (-169.53, 62.98), (-171.79, 63.41), (-171.73, 63.78)], [(-85.16, 65.66), (-84.98, 65.22), (-80.1, 63.73), (-80.99, 63.41), (-83.11, 64.1), (-85.52, 63.05), (-85.87, 63.64), (-87.22, 63.54), (-86.35, 64.04), (-85.88, 65.74), (-85.16, 65.66)], [(-14.51, 66.46), (-14.74, 65.81), (-13.61, 65.13), (-14.91, 64.36), (-18.66, 63.5), (-22.76, 63.96), (-21.78, 64.4), (-23.96, 64.89), (-22.23, 65.38), (-24.33, 65.61), (-23.65, 66.26), (-22.13, 66.41), (-20.58, 65.73), (-16.17, 66.53), (-14.51, 66.46)], [(-75.87, 67.15), (-76.99, 67.1), (-77.24, 67.59), (-76.81, 68.15), (-75.9, 68.29), (-75.11, 68.01), (-75.22, 67.44), (-75.87, 67.15)], [(-175.01, 66.58), (-174.34, 66.34), (-174.57, 67.06), (-171.86, 66.91), (-169.9, 65.98), (-172.53, 65.44), (-172.56, 64.46), (-172.96, 64.25), (-175.98, 64.92), (-176.21, 65.36), (-178.36, 65.39), (-178.9, 65.74), (-178.69, 66.11), (-179.88, 65.87), (-179.43, 65.4), (-180.0, 64.98), (-180.0, 68.96), (-174.93, 67.21), (-175.01, 66.58)], [(-95.65, 69.11), (-96.27, 68.76), (-99.8, 69.4), (-98.22, 70.14), (-96.26, 69.49), (-95.65, 69.11)], [(180.0, 70.83), (178.73, 71.1), (180.0, 71.52), (180.0, 70.83)], [(-178.69, 70.89), (-180.0, 70.83), (-180.0, 71.52), (-177.66, 71.13), (-178.69, 70.89)], [(-90.55, 69.5), (-90.55, 68.48), (-89.22, 69.26), (-88.02, 68.62), (-88.32, 67.87), (-87.35, 67.2), (-85.58, 68.78), (-85.52, 69.88), (-82.62, 69.66), (-81.28, 69.16), (-81.22, 68.67), (-81.96, 68.13), (-81.26, 67.6), (-81.39, 67.11), (-83.34, 66.41), (-85.77, 66.56), (-87.32, 64.78), (-88.48, 64.1), (-89.91, 64.03), (-90.7, 63.61), (-90.77, 62.96), (-91.93, 62.84), (-93.16, 62.02), (-94.24, 60.9), (-94.68, 58.95), (-93.22, 58.78), (-92.3, 57.09), (-90.9, 57.28), (-85.01, 55.3), (-82.27, 55.15), (-82.12, 53.28), (-81.4, 52.16), (-79.91, 51.21), (-79.14, 51.53), (-78.6, 52.56), (-79.12, 54.14), (-79.83, 54.67), (-78.23, 55.14), (-76.54, 56.53), (-77.3, 58.05), (-78.52, 58.8), (-77.34, 59.85), (-78.11, 62.32), (-73.84, 62.44), (-71.37, 61.14), (-69.59, 61.06), (-69.29, 58.96), (-67.65, 58.21), (-66.2, 58.77), (-64.58, 60.34), (-61.4, 56.97), (-61.8, 56.34), (-57.33, 54.63), (-56.94, 53.78), (-55.76, 53.27), (-55.68, 52.15), (-60.03, 50.24), (-66.4, 50.23), (-71.1, 46.82), (-68.65, 48.3), (-65.06, 49.23), (-64.17, 48.74), (-65.12, 48.07), (-64.47, 46.24), (-63.17, 45.74), (-61.52, 45.88), (-60.52, 47.01), (-60.45, 46.28), (-59.8, 45.92), (-65.36, 43.55), (-66.12, 43.62), (-66.16, 44.47), (-64.43, 45.29), (-67.14, 45.14), (-66.96, 44.81), (-70.12, 43.68), (-70.69, 43.03), (-70.83, 42.34), (-69.97, 41.64), (-73.71, 40.93), (-71.95, 40.93), (-73.95, 40.75), (-74.91, 38.94), (-75.53, 39.5), (-75.06, 38.4), (-75.94, 37.22), (-75.72, 37.94), (-76.35, 39.15), (-76.33, 38.08), (-76.96, 38.23), (-76.3, 37.92), (-75.73, 35.55), (-79.06, 33.49), (-81.34, 31.44), (-81.31, 30.04), (-80.06, 26.88), (-80.38, 25.21), (-81.17, 25.2), (-81.71, 25.87), (-82.86, 27.89), (-82.93, 29.1), (-84.1, 30.09), (-85.11, 29.64), (-86.4, 30.4), (-89.18, 30.32), (-89.6, 30.18), (-89.22, 29.29), (-90.15, 29.12), (-91.63, 29.68), (-93.85, 29.71), (-96.59, 28.31), (-97.37, 27.38), (-97.14, 25.87), (-97.87, 22.44), (-96.29, 19.32), (-94.43, 18.14), (-92.04, 18.7), (-90.77, 19.28), (-90.28, 21.0), (-87.05, 21.54), (-86.85, 20.85), (-87.84, 18.26), (-88.3, 18.5), (-88.36, 16.53), (-88.93, 15.89), (-84.98, 16.0), (-83.41, 15.27), (-83.18, 14.31), (-83.81, 11.1), (-82.21, 9.0), (-81.44, 8.79), (-79.57, 9.61), (-76.84, 8.64), (-75.67, 9.44), (-75.48, 10.62), (-74.91, 11.08), (-73.41, 11.23), (-71.75, 12.44), (-71.14, 12.11), (-71.95, 11.42), (-71.7, 9.07), (-71.04, 9.86), (-71.4, 10.97), (-70.16, 11.38), (-69.94, 12.16), (-68.19, 10.55), (-66.23, 10.65), (-64.89, 10.08), (-64.32, 10.64), (-61.88, 10.72), (-62.73, 10.42), (-62.39, 9.95), (-60.83, 9.38), (-60.67, 8.58), (-59.1, 8.0), (-58.45, 6.83), (-57.15, 5.97), (-53.96, 5.76), (-51.32, 4.2), (-50.51, 1.9), (-49.97, 1.74), (-49.95, 1.05), (-50.7, 0.22), (-50.39, -0.08), (-48.62, -0.24), (-48.58, -1.24), (-47.82, -0.58), (-44.91, -1.55), (-44.42, -2.14), (-44.58, -2.69), (-43.42, -2.38), (-39.98, -2.87), (-37.22, -4.82), (-35.6, -5.15), (-34.73, -7.34), (-35.13, -9.0), (-38.67, -13.06), (-39.27, -17.87), (-40.94, -21.94), (-41.99, -22.97), (-44.65, -23.35), (-47.65, -24.89), (-48.5, -25.88), (-48.89, -28.67), (-53.81, -34.4), (-54.94, -34.95), (-56.22, -34.86), (-58.43, -33.91), (-58.5, -34.43), (-57.23, -35.29), (-57.36, -35.98), (-56.74, -36.41), (-56.79, -36.9), (-57.75, -38.18), (-59.23, -38.72), (-62.34, -38.83), (-62.15, -40.68), (-62.75, -41.03), (-65.12, -41.06), (-64.98, -42.06), (-64.3, -42.36), (-63.76, -42.04), (-63.46, -42.56), (-65.18, -43.5), (-65.57, -45.04), (-67.29, -45.55), (-67.58, -46.3), (-65.64, -47.24), (-65.99, -48.13), (-67.17, -48.7), (-67.82, -49.87), (-68.02, -50.0), (-75.36, -50.0), (-75.61, -48.67), (-75.18, -47.71), (-74.13, -46.94), (-75.64, -46.65), (-74.69, -45.76), (-74.35, -44.1), (-73.24, -44.45), (-72.72, -42.38), (-73.39, -42.12), (-73.7, -43.37), (-74.33, -43.22), (-73.22, -39.26), (-73.59, -37.16), (-73.17, -37.12), (-71.44, -32.42), (-71.49, -28.86), (-70.91, -27.64), (-70.16, -19.76), (-70.37, -18.35), (-71.46, -17.36), (-76.01, -14.65), (-79.76, -7.19), (-81.25, -6.14), (-80.93, -5.69), (-81.41, -4.74), (-79.77, -2.66), (-79.99, -2.22), (-80.37, -2.69), (-80.97, -2.25), (-80.93, -1.06), (-80.09, 0.77), (-78.86, 1.38), (-78.43, 2.63), (-77.13, 3.85), (-77.5, 4.09), (-77.48, 6.69), (-78.21, 7.51), (-78.18, 8.32), (-79.56, 8.93), (-80.48, 8.09), (-80.0, 7.55), (-80.89, 7.22), (-81.06, 7.82), (-83.51, 8.45), (-83.63, 9.05), (-84.98, 10.09), (-85.11, 9.56), (-85.66, 9.93), (-85.71, 11.09), (-87.67, 12.91), (-87.49, 13.3), (-91.23, 13.93), (-94.69, 16.2), (-96.56, 15.65), (-103.5, 18.29), (-105.49, 19.95), (-105.73, 20.43), (-105.27, 21.42), (-106.03, 22.77), (-109.26, 25.58), (-109.29, 26.44), (-110.39, 27.16), (-110.64, 27.86), (-112.23, 28.95), (-113.15, 31.17), (-114.78, 31.8), (-114.67, 30.16), (-111.62, 26.66), (-110.66, 24.3), (-110.17, 24.27), (-109.43, 23.19), (-110.03, 22.82), (-112.18, 24.74), (-112.3, 26.01), (-115.06, 27.72), (-114.57, 27.74), (-114.16, 28.57), (-115.52, 29.56), (-117.3, 33.05), (-118.52, 34.03), (-120.62, 34.61), (-124.4, 40.31), (-124.53, 42.77), (-123.9, 45.52), (-124.69, 48.18), (-123.12, 48.04), (-122.59, 47.1), (-122.84, 49.0), (-127.44, 50.83), (-127.99, 51.72), (-127.85, 52.33), (-129.13, 52.76), (-129.31, 53.56), (-131.97, 55.5), (-132.25, 56.37), (-133.54, 57.18), (-134.08, 58.12), (-136.63, 58.21), (-139.87, 59.54), (-147.11, 60.88), (-148.22, 60.67), (-148.02, 59.98), (-151.72, 59.16), (-151.41, 60.73), (-150.35, 61.03), (-150.62, 61.28), (-154.02, 59.35), (-153.29, 58.86), (-154.23, 58.15), (-156.31, 57.42), (-158.43, 55.99), (-164.79, 54.4), (-157.72, 57.57), (-157.04, 58.92), (-159.06, 58.42), (-160.36, 59.07), (-161.97, 58.67), (-161.87, 59.63), (-162.52, 59.99), (-163.82, 59.8), (-165.35, 60.51), (-165.35, 61.07), (-166.12, 61.5), (-164.56, 63.15), (-163.07, 63.06), (-160.77, 63.77), (-161.52, 64.4), (-160.78, 64.79), (-164.96, 64.45), (-166.43, 64.69), (-168.11, 65.67), (-164.47, 66.58), (-163.65, 66.58), (-163.79, 66.08), (-161.68, 66.12), (-166.76, 68.36), (-166.2, 68.88), (-163.17, 69.37), (-161.91, 70.33), (-156.58, 71.36), (-154.34, 70.7), (-143.59, 70.15), (-136.5, 68.9), (-134.41, 69.63), (-132.93, 69.51), (-129.79, 70.19), (-129.11, 69.78), (-128.14, 70.48), (-125.76, 69.48), (-124.42, 70.16), (-124.29, 69.4), (-121.47, 69.8), (-113.9, 68.4), (-115.3, 67.9), (-109.95, 67.98), (-108.88, 67.38), (-107.79, 67.89), (-108.81, 68.31), (-108.17, 68.65), (-106.15, 68.8), (-104.34, 68.02), (-101.45, 67.65), (-98.44, 67.78), (-98.56, 68.4), (-97.67, 68.58), (-96.12, 68.24), (-96.13, 67.29), (-95.49, 68.09), (-94.68, 68.06), (-94.23, 69.07), (-96.47, 70.09), (-96.39, 71.19), (-95.21, 71.92), (-92.88, 71.32), (-91.52, 70.19), (-92.41, 69.7), (-90.55, 69.5)], [(-114.17, 73.12), (-114.67, 72.65), (-112.44, 72.96), (-111.05, 72.45), (-109.92, 72.96), (-108.19, 71.65), (-107.69, 72.07), (-108.4, 73.09), (-106.52, 73.08), (-105.4, 72.67), (-104.46, 70.99), (-100.98, 70.02), (-101.09, 69.58), (-102.73, 69.5), (-102.09, 69.12), (-102.43, 68.75), (-105.96, 69.18), (-113.31, 68.54), (-113.85, 69.01), (-116.11, 69.17), (-117.34, 69.96), (-112.42, 70.37), (-117.9, 70.54), (-118.43, 70.91), (-116.11, 71.31), (-119.4, 71.56), (-117.87, 72.71), (-115.19, 73.31), (-114.17, 73.12)], [(-104.5, 73.42), (-105.38, 72.76), (-106.94, 73.46), (-105.26, 73.64), (-104.5, 73.42)], [(-76.34, 73.1), (-79.49, 72.74), (-80.88, 73.33), (-80.35, 73.76), (-78.06, 73.65), (-76.34, 73.1)], [(-86.56, 73.16), (-85.77, 72.53), (-84.85, 73.34), (-82.32, 73.75), (-80.6, 72.72), (-80.75, 72.06), (-77.82, 72.75), (-74.23, 71.77), (-74.1, 71.33), (-72.24, 71.56), (-71.2, 70.92), (-68.79, 70.53), (-66.97, 69.19), (-68.81, 68.72), (-64.86, 67.85), (-63.42, 66.93), (-61.85, 66.86), (-62.16, 66.16), (-63.92, 65.0), (-66.72, 66.39), (-68.02, 66.26), (-68.14, 65.69), (-65.32, 64.38), (-64.67, 63.39), (-65.01, 62.67), (-68.78, 63.75), (-66.17, 61.93), (-71.02, 62.91), (-72.24, 63.4), (-71.89, 63.68), (-74.83, 64.68), (-77.71, 64.23), (-78.56, 64.57), (-77.9, 65.31), (-73.96, 65.45), (-74.29, 65.81), (-72.65, 67.28), (-72.93, 67.73), (-76.87, 68.89), (-76.23, 69.15), (-78.96, 70.17), (-81.31, 69.74), (-84.94, 69.97), (-88.68, 70.41), (-89.51, 70.76), (-88.47, 71.22), (-89.89, 71.22), (-90.21, 72.24), (-89.44, 73.13), (-85.83, 73.8), (-86.56, 73.16)], [(-100.36, 73.84), (-97.38, 73.76), (-97.12, 73.47), (-98.05, 72.99), (-96.54, 72.56), (-96.72, 71.66), (-99.32, 71.36), (-102.5, 72.51), (-102.48, 72.83), (-100.44, 72.71), (-101.54, 73.36), (-100.36, 73.84)], [(143.6, 73.21), (139.86, 73.37), (142.06, 73.86), (143.48, 73.48), (143.6, 73.21)], [(-93.2, 72.77), (-94.27, 72.02), (-95.41, 72.06), (-96.02, 73.44), (-94.5, 74.13), (-90.51, 73.86), (-92.0, 72.97), (-93.2, 72.77)], [(-120.46, 71.4), (-123.09, 70.9), (-125.93, 71.87), (-123.94, 73.68), (-124.92, 74.29), (-117.56, 74.19), (-115.51, 73.48), (-120.46, 71.82), (-120.46, 71.4)], [(-93.61, 74.98), (-94.16, 74.59), (-96.82, 74.93), (-96.62, 75.0), (-93.64, 75.0), (-93.61, 74.98)], [(144.49, 75.0), (144.3, 74.82), (138.96, 74.61), (137.77, 75.0), (144.49, 75.0)], [(-106.37, 75.0), (-112.22, 74.42), (-113.87, 74.72), (-112.56, 75.0), (-106.37, 75.0)], [(57.54, 70.72), (53.68, 70.76), (53.41, 71.21), (51.6, 71.47), (51.46, 72.01), (54.43, 73.63), (53.51, 73.75), (55.9, 74.63), (55.68, 75.0), (61.68, 75.0), (58.48, 74.31), (55.42, 72.37), (55.62, 71.54), (57.54, 70.72)], [(-79.96, 75.0), (-79.83, 74.92), (-81.95, 74.44), (-88.15, 74.39), (-92.42, 74.84), (-92.5, 75.0), (-79.96, 75.0)], [(112.6, 75.0), (109.4, 74.18), (113.02, 73.98), (113.53, 73.34), (115.57, 73.75), (123.2, 72.97), (123.26, 73.74), (126.98, 73.57), (128.59, 73.04), (129.05, 72.4), (128.46, 71.98), (131.29, 70.79), (132.25, 71.84), (133.86, 71.39), (139.87, 71.49), (139.15, 72.42), (140.47, 72.85), (149.5, 72.2), (152.97, 70.84), (159.0, 70.87), (159.83, 70.45), (159.71, 69.72), (160.94, 69.44), (167.84, 69.58), (169.58, 68.69), (170.82, 69.01), (170.01, 69.65), (170.45, 70.1), (175.72, 69.88), (180.0, 68.96), (180.0, 64.98), (177.41, 64.61), (179.37, 62.98), (179.23, 62.3), (177.36, 62.52), (173.68, 61.65), (170.33, 59.88), (168.9, 60.57), (166.3, 59.79), (165.84, 60.16), (164.88, 59.73), (163.54, 59.87), (162.02, 58.24), (162.05, 57.84), (163.19, 57.62), (163.06, 56.16), (162.13, 56.12), (161.7, 55.29), (162.12, 54.86), (160.37, 54.34), (160.02, 53.2), (158.53, 52.96), (158.23, 51.94), (156.79, 51.01), (155.43, 55.38), (155.91, 56.77), (156.81, 57.83), (158.36, 58.06), (163.67, 61.14), (164.47, 62.55), (163.26, 62.47), (162.66, 61.64), (160.12, 60.54), (159.3, 61.77), (156.72, 61.43), (154.22, 59.76), (155.04, 59.15), (151.27, 58.78), (151.34, 59.5), (149.78, 59.66), (148.54, 59.16), (142.2, 59.04), (135.13, 54.73), (136.7, 54.6), (138.16, 53.76), (138.8, 54.25), (139.9, 54.19), (141.35, 53.09), (141.38, 52.24), (140.6, 51.24), (140.06, 48.45), (138.22, 46.31), (134.87, 43.4), (133.54, 42.81), (132.28, 43.28), (129.97, 41.94), (129.71, 40.88), (127.53, 39.76), (127.39, 39.21), (128.35, 38.61), (129.46, 36.78), (129.09, 35.08), (126.49, 34.39), (126.12, 36.73), (126.86, 36.89), (126.17, 37.75), (124.71, 38.11), (125.32, 39.55), (124.27, 39.93), (121.05, 38.9), (122.17, 40.42), (121.64, 40.95), (119.02, 39.25), (118.04, 39.2), (117.53, 38.74), (118.88, 37.9), (118.91, 37.45), (119.7, 37.16), (120.82, 37.87), (122.36, 37.45), (122.52, 36.93), (121.1, 36.65), (119.15, 34.91), (120.23, 34.36), (121.91, 31.69), (121.89, 30.95), (121.26, 30.68), (122.09, 29.83), (121.68, 28.23), (121.13, 28.14), (118.66, 24.55), (115.89, 22.78), (114.15, 22.22), (113.81, 22.55), (110.79, 21.4), (110.44, 20.34), (109.89, 20.28), (109.86, 21.4), (108.52, 21.72), (105.88, 19.75), (105.66, 19.06), (108.88, 15.28), (109.34, 13.43), (109.2, 11.67), (105.16, 8.6), (104.8, 9.24), (105.08, 9.92), (103.5, 10.63), (102.59, 12.19), (100.83, 12.63), (100.98, 13.41), (100.1, 13.41), (99.22, 9.24), (99.87, 9.21), (100.46, 7.43), (102.96, 5.52), (104.23, 1.29), (103.52, 1.23), (101.39, 2.76), (100.09, 6.46), (98.5, 8.38), (98.34, 7.79), (98.76, 11.44), (97.16, 16.93), (95.37, 15.71), (94.19, 16.04), (94.32, 18.21), (93.66, 19.73), (92.37, 20.67), (91.42, 22.77), (90.5, 22.81), (90.27, 21.84), (89.03, 22.06), (88.89, 21.69), (86.98, 21.5), (87.03, 20.74), (86.5, 20.15), (85.06, 19.48), (82.19, 17.02), (82.19, 16.56), (80.32, 15.9), (79.86, 10.36), (79.34, 10.31), (78.89, 9.55), (79.19, 9.22), (78.28, 8.93), (77.54, 7.97), (76.59, 8.9), (73.53, 15.99), (72.63, 21.36), (70.47, 20.88), (69.16, 22.09), (69.64, 22.45), (69.35, 22.84), (67.44, 23.94), (66.37, 25.43), (61.5, 25.08), (57.4, 25.74), (56.97, 26.97), (56.49, 27.14), (54.72, 26.48), (51.52, 27.87), (50.12, 30.15), (47.97, 29.98), (48.81, 27.69), (50.15, 26.69), (50.81, 24.75), (51.01, 26.01), (51.59, 25.8), (51.39, 24.63), (51.79, 24.02), (54.01, 24.12), (56.36, 26.4), (56.85, 24.24), (58.73, 23.57), (59.81, 22.31), (58.49, 20.43), (57.83, 20.24), (57.69, 18.94), (55.27, 17.63), (55.27, 17.23), (52.39, 16.38), (52.17, 15.6), (48.68, 14.0), (45.63, 13.29), (44.99, 12.7), (43.48, 12.64), (42.6, 15.21), (42.65, 16.77), (40.94, 19.49), (39.14, 21.29), (38.49, 23.69), (37.48, 24.29), (35.13, 28.06), (34.63, 28.06), (34.92, 29.5), (33.92, 27.65), (32.42, 29.85), (34.1, 26.14), (35.69, 23.93), (35.53, 23.1), (36.87, 22.0), (37.48, 18.61), (38.41, 18.0), (39.27, 15.92), (43.32, 12.39), (42.72, 11.74), (44.61, 10.44), (51.11, 12.02), (51.05, 10.64), (49.45, 6.8), (47.74, 4.22), (40.26, -2.57), (39.2, -4.68), (38.8, -6.48), (39.44, -6.84), (39.19, -8.49), (40.48, -10.77), (40.78, -14.69), (39.45, -16.72), (37.41, -17.59), (34.79, -19.78), (35.61, -23.71), (35.04, -24.48), (32.57, -25.73), (32.92, -26.22), (32.2, -28.75), (28.22, -32.77), (25.78, -33.94), (22.57, -33.86), (19.62, -34.82), (18.38, -34.14), (17.93, -32.61), (18.22, -31.66), (15.21, -27.09), (14.26, -22.11), (11.79, -18.07), (11.78, -15.79), (12.5, -13.55), (13.63, -12.04), (13.69, -10.73), (12.88, -9.17), (13.24, -8.56), (11.92, -5.04), (8.8, -1.11), (9.8, 3.07), (9.4, 3.73), (8.5, 4.77), (5.9, 4.26), (4.33, 6.27), (1.87, 6.14), (-1.96, 4.71), (-4.65, 5.17), (-7.52, 4.34), (-9.0, 4.83), (-12.43, 7.26), (-14.84, 10.88), (-16.61, 12.17), (-16.71, 13.6), (-17.62, 14.73), (-16.46, 16.14), (-16.15, 18.11), (-16.97, 21.89), (-15.09, 24.52), (-14.44, 26.25), (-12.62, 28.04), (-11.69, 28.15), (-9.56, 29.93), (-9.81, 31.18), (-9.3, 32.56), (-6.91, 34.11), (-5.93, 35.76), (-2.17, 35.17), (1.47, 36.61), (8.42, 36.95), (9.51, 37.35), (10.21, 37.23), (10.18, 36.72), (11.1, 36.9), (10.6, 36.41), (10.94, 35.7), (10.81, 34.83), (10.15, 34.33), (10.34, 33.79), (15.25, 32.27), (15.71, 31.38), (19.09, 30.27), (20.05, 30.99), (20.13, 32.24), (21.54, 32.84), (28.91, 30.87), (30.98, 31.56), (31.96, 30.93), (32.19, 31.26), (33.77, 30.97), (34.56, 31.55), (36.0, 34.64), (36.15, 35.82), (35.78, 36.28), (36.16, 36.65), (34.71, 36.8), (34.03, 36.22), (32.51, 36.11), (31.7, 36.64), (29.7, 36.14), (27.64, 36.66), (26.32, 38.21), (26.8, 38.99), (26.17, 39.46), (27.28, 40.42), (28.82, 40.46), (29.24, 41.22), (31.15, 41.09), (33.51, 42.02), (35.17, 42.04), (38.35, 40.95), (40.37, 41.01), (41.7, 41.96), (41.45, 42.65), (36.68, 45.24), (38.23, 46.24), (37.67, 46.64), (39.12, 47.26), (34.96, 46.27), (35.02, 45.65), (36.53, 45.47), (36.33, 45.11), (33.88, 44.36), (33.33, 44.56), (33.55, 45.03), (32.45, 45.33), (33.59, 45.85), (33.3, 46.08), (30.75, 46.58), (29.63, 45.04), (28.84, 44.91), (27.67, 42.58), (28.81, 41.05), (27.62, 41.0), (26.36, 40.15), (26.06, 40.82), (24.93, 40.95), (23.71, 40.69), (24.41, 40.13), (23.9, 39.96), (22.63, 40.26), (23.35, 39.19), (22.97, 38.97), (24.03, 38.22), (24.04, 37.66), (23.12, 37.92), (23.41, 37.41), (22.78, 37.31), (23.15, 36.42), (22.49, 36.41), (21.67, 36.85), (21.12, 38.31), (19.41, 40.25), (19.54, 41.72), (16.02, 43.51), (14.9, 45.08), (14.26, 45.23), (13.95, 44.8), (13.94, 45.59), (13.14, 45.74), (12.33, 45.38), (12.59, 44.09), (15.14, 41.96), (15.93, 41.96), (15.89, 41.54), (18.48, 40.17), (18.29, 39.81), (16.87, 40.44), (16.45, 39.8), (17.17, 39.42), (17.05, 38.9), (16.1, 37.99), (15.68, 37.91), (16.11, 38.96), (15.41, 40.05), (12.11, 41.7), (10.51, 42.93), (10.2, 43.92), (8.89, 44.37), (6.53, 43.13), (4.56, 43.4), (3.1, 43.08), (3.04, 41.89), (0.81, 41.01), (-0.28, 39.31), (0.11, 38.74), (-2.15, 36.67), (-4.37, 36.68), (-5.38, 35.95), (-6.52, 36.94), (-8.9, 36.87), (-8.84, 38.27), (-9.53, 38.74), (-8.77, 40.76), (-9.39, 43.03), (-7.98, 43.75), (-1.9, 43.42), (-1.38, 44.02), (-1.19, 46.01), (-2.96, 47.57), (-4.49, 47.96), (-4.59, 48.68), (-1.62, 48.64), (-1.93, 49.78), (-0.99, 49.35), (1.34, 50.13), (1.64, 50.95), (3.83, 51.62), (4.71, 53.09), (8.12, 53.53), (8.8, 54.02), (8.12, 55.52), (8.54, 57.11), (10.58, 57.73), (10.25, 56.89), (10.91, 56.46), (9.65, 55.47), (9.94, 54.6), (10.95, 54.36), (10.94, 54.01), (12.52, 54.47), (14.12, 53.76), (17.62, 54.85), (19.66, 54.43), (21.27, 55.19), (21.09, 56.78), (21.58, 57.41), (22.52, 57.75), (23.32, 57.01), (24.12, 57.03), (24.43, 58.38), (23.43, 58.61), (23.34, 59.19), (27.98, 59.48), (29.12, 60.03), (28.07, 60.5), (22.87, 59.85), (21.32, 60.72), (21.54, 61.71), (21.06, 62.61), (21.54, 63.19), (25.4, 65.11), (25.29, 65.53), (23.9, 66.01), (22.18, 65.72), (21.21, 65.03), (21.37, 64.41), (17.85, 62.75), (17.12, 61.34), (18.79, 60.08), (17.87, 58.95), (16.83, 58.72), (15.88, 56.1), (14.67, 56.2), (14.1, 55.41), (12.94, 55.36), (10.36, 59.47), (8.38, 58.31), (7.05, 58.08), (5.67, 58.59), (4.99, 61.97), (10.53, 64.49), (14.76, 67.81), (19.18, 69.82), (23.02, 70.2), (24.55, 71.03), (28.17, 71.19), (31.29, 70.45), (30.01, 70.19), (31.1, 69.56), (32.13, 69.91), (36.51, 69.06), (41.06, 67.46), (41.13, 66.79), (38.38, 66.0), (33.18, 66.63), (34.81, 65.9), (34.94, 64.41), (37.01, 63.85), (37.14, 64.33), (36.52, 64.78), (37.18, 65.14), (39.59, 64.52), (40.44, 64.76), (39.76, 65.5), (42.09, 66.48), (43.95, 66.07), (44.53, 66.76), (43.7, 67.35), (44.19, 67.95), (43.45, 68.57), (46.25, 68.25), (46.82, 67.69), (45.56, 67.57), (45.56, 67.01), (46.35, 66.67), (47.89, 66.88), (48.14, 67.52), (53.72, 68.86), (54.47, 68.81), (53.49, 68.2), (58.8, 68.88), (59.94, 68.28), (61.08, 68.94), (60.03, 69.52), (60.55, 69.85), (63.5, 69.55), (68.51, 68.09), (69.18, 68.62), (68.14, 69.36), (66.93, 69.45), (67.26, 69.93), (66.69, 71.03), (68.54, 71.93), (69.2, 72.84), (72.59, 72.78), (72.8, 72.22), (71.85, 71.41), (72.79, 70.39), (72.56, 69.02), (73.67, 68.41), (71.28, 66.32), (72.42, 66.17), (75.05, 67.76), (74.47, 68.33), (74.94, 68.99), (73.84, 69.07), (73.6, 69.63), (74.4, 70.63), (73.1, 71.45), (74.89, 72.12), (74.66, 72.83), (75.68, 72.3), (75.29, 71.34), (76.36, 71.15), (75.9, 71.87), (77.58, 72.27), (79.65, 72.32), (81.5, 71.75), (80.61, 72.58), (80.51, 73.65), (86.82, 73.94), (86.01, 74.46), (86.96, 75.0), (112.6, 75.0)], [(-20.43, 75.0), (-19.37, 74.3), (-21.59, 74.22), (-20.43, 73.82), (-20.76, 73.46), (-23.57, 73.31), (-22.31, 72.63), (-22.3, 72.18), (-24.79, 72.33), (-22.13, 71.47), (-21.75, 70.66), (-23.54, 70.47), (-25.54, 71.43), (-25.2, 70.75), (-26.36, 70.23), (-22.35, 70.13), (-27.75, 68.47), (-31.78, 68.12), (-34.2, 66.68), (-39.81, 65.46), (-40.67, 64.84), (-41.19, 63.48), (-42.82, 62.68), (-42.42, 61.9), (-43.38, 60.1), (-44.79, 60.04), (-46.26, 60.85), (-48.26, 60.86), (-51.63, 63.63), (-52.28, 65.18), (-53.66, 66.1), (-53.3, 66.84), (-53.97, 67.19), (-52.98, 68.36), (-51.48, 68.73), (-50.87, 69.93), (-53.46, 69.28), (-54.68, 69.61), (-54.36, 70.82), (-51.39, 70.57), (-54.0, 71.55), (-55.83, 71.65), (-54.72, 72.59), (-57.32, 74.71), (-58.27, 75.0), (-20.43, 75.0)]]
MAP_DOTS_LATLON = {1: (40.71, -74.01), 2: (13.69, -89.22),
                   3: (47.91, 33.39), 4: (24.71, 46.68),
                   5: (26.50, 56.50), 6: (26.18, 56.25),
                   7: (48.28, 37.18), 8: (52.23, 21.01),
                   9: (55.68, 12.57), 10: (52.52, 13.40),
                   11: (38.91, -77.04), 12: (24.45, 54.38),
                   13: (36.17, -115.14), 14: (37.35, -121.95),
                   15: (1.35, 103.82), 16: (35.68, 139.69),
                   17: (50.11, 8.68), 18: (-6.00, 131.00),
                   19: (37.38, 97.37), 20: (-14.28, -170.70),
                   21: (33.75, -84.39)}
MAP_DOT_NUDGE = {1: (3.5, -21.0), 3: (10.4, 6.8), 4: (-20.1, -4.0),
                 5: (-2.3, -22.2), 6: (1.3, 8.9), 7: (27.3, -9.3),
                 8: (18.9, -13.0), 9: (3.2, -12.7), 10: (3.4, 19.2),
                 11: (0.0, -2.0), 12: (-18.2, 23.8), 13: (16.0, -3.8),
                 14: (8.5, 16.7), 17: (-19.3, 12.0), 21: (-6.0, 6.0)}
# v5: dot 21 Atlanta (CDC HQ, 33.75N -84.39W) joins a US cluster
# already crowded at 60% scale, so dots 1/11/13 got small new
# nudges (1 north a touch more, 11 east + north, 13 west a
# touch) and 21 itself sits 6 units SW of Atlanta (Alabama,
# still on land). A grid search over the cluster verified every
# dot still on land (point-in-polygon against NE_LAND) and the
# closest pair is now 14.3px -- discs are 14px, so no overlap,
# just 0.3px of clear space at the tightest pair (1/11). Dots
# 18 (Banda Sea, sea by design) and 20 (Pago Pago, island too
# small for 110m data) unchanged.


# Equal Earth projection (Snyder 1985): A1..A4 constants; lon/lat in
# degrees; returns x/y in units of the sphere radius.
_EE_A1, _EE_A2, _EE_A3, _EE_A4 = 1.340264, -0.081106, 0.000893, 0.003796


def _equal_earth(lon_deg, lat_deg):
    lam = math.radians(lon_deg)
    phi = math.radians(lat_deg)
    th = math.asin(math.sqrt(3) / 2 * math.sin(phi))
    x = (2 * math.sqrt(3) * lam
         / (3 * (9 * _EE_A4 * th ** 8 + 7 * _EE_A3 * th ** 6
                 + 3 * _EE_A2 * th ** 2 + _EE_A1)) * math.cos(th))
    y = (_EE_A4 * th ** 9 + _EE_A3 * th ** 7 + _EE_A2 * th ** 3
         + _EE_A1 * th)
    return x, y


def _map_fit(lw, lh):
    """Fit the Equal Earth world (lon +-180, lat -50..75) into a
    lw x lh box; returns (scale, x_half, y_top, x_off, y_off)."""
    xs = _equal_earth(180, 0)[0]
    y_top = _equal_earth(0, 75)[1]
    y_bot = _equal_earth(0, -50)[1]
    scale = min(lw / (2 * xs), lh / (y_top - y_bot))
    ox = (lw - 2 * xs * scale) / 2
    oy = (lh - (y_top - y_bot) * scale) / 2
    return scale, xs, y_top, ox, oy


def _dashed_hline(d, x0, x1, y, fill, dash=6, gap=4):
    """Thin dashed horizontal line (graticule)."""
    xx = x0
    while xx < x1:
        d.line([xx, y, min(xx + dash, x1), y], fill=fill, width=1)
        xx += dash + gap


def _dashed_vline(d, x, y0, y1, fill, dash=6, gap=4):
    """Thin dashed vertical line (graticule)."""
    yy = y0
    while yy < y1:
        d.line([x, yy, x, min(yy + dash, y1)], fill=fill, width=1)
        yy += dash + gap


def draw_map(d, x, y, w, h, header=None):
    """Bottom world map (346x252 frame, world drawn at 60%) with
    numbered dots 1-20.

    v2: land from Natural Earth 110m (NE_LAND, embedded), Equal
    Earth projection fitted to the land box, lat clipped to
    [-50, 75]. 1px dark-green coastlines, light dashed graticule
    in the sea. Dots are projected from real lat/lon through the
    same projection function (plus the small MAP_DOT_NUDGE
    de-collision offsets) and identified by the key to the map's
    right. No leader lines: panels are found by number + place
    tag. Optional header strip inside the frame top, so the map
    box and the info box share the same top/bottom edges (both
    y=702..954). With a header, the land area is inset below the
    strip (y+22..y+h); without one it fills the frame.
    v3: the frame is 346px wide (was 576) but stays 252px tall so
    it stays flush with the info box; the world itself is drawn
    at 60% of its v2 size (MAP_SCALE), centred in the land box,
    and the graticule, dots and header scale with it. The frame
    outline is redrawn last so land fill never eats it.
    """
    d.rectangle([x, y, x + w, y + h], fill="#BDEBFF", outline=INK, width=2)
    land = "#6ED598"
    edge = "#1F8A4C"
    grid = "#8FC8E8"
    # Land area: full frame, or inset below the header strip.
    lx, ly, lw, lh = x, y, w, h
    if header:
        f = F(SANS_B, 8)
        d.text((x + 6, y + 4), header, font=f, fill=RED)
        d.line([x + 6, y + 17, x + w - 6, y + 17], fill=INK, width=1)
        ly, lh = y + 22, h - 22

    # dashed graticule in the sea (drawn first; the land covers it).
    # v3: 64x56 cells scaled to 60% -> 38x34, same 8px page-grid
    # rhythm; spans the whole land box so the sea reads as a chart.
    for gx in range(38, lw, 38):
        _dashed_vline(d, lx + gx, ly + 1, ly + lh - 1, grid)
    for gy in range(34, lh, 34):
        _dashed_hline(d, lx + 1, lx + lw - 1, ly + gy, grid)

    # Equal Earth fit, then the Natural Earth land polygons
    # (lon/lat -> pixels through one projection). v3: the world is
    # drawn at MAP_SCALE of its v2 size -- the v2 fit scale for
    # the 576x224 land box, times 0.6 -- centred in this land box.
    ref_scale, xs, y_top, _, _ = _map_fit(576, 224)
    scale = ref_scale * MAP_SCALE
    y_bot = _equal_earth(0, -50)[1]
    ox = (lw - 2 * xs * scale) / 2
    oy = (lh - (y_top - y_bot) * scale) / 2

    def P(lon, lat):
        ex, ey = _equal_earth(lon, lat)
        return (lx + ox + (ex + xs) * scale,
                ly + oy + (y_top - ey) * scale)

    for poly in NE_LAND:
        d.polygon([P(lon, lat) for lon, lat in poly],
                  fill=land, outline=edge, width=1)

    # numbered dots, projected from real lat/lon plus the small
    # de-collision nudges (see MAP_DOT_NUDGE), both scaled to 60%.
    # v4: dot radius 7 and number font 9, so the numbers stay
    # legible at thumbnail size; white ring width 1 keeps a
    # sliver of background between neighbouring dots.
    f = F(SANS_B, 9)
    r = 7
    for n, (lat, lon) in MAP_DOTS_LATLON.items():
        cx, cy = P(lon, lat)
        dx, dy = MAP_DOT_NUDGE.get(n, (0, 0))
        cx, cy = cx + dx * MAP_SCALE, cy + dy * MAP_SCALE
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED2,
                  outline="#FFFFFF", width=1)
        t = str(n)
        d.text((cx - d.textlength(t, font=f) / 2, cy - 5), t, font=f,
               fill="#FFFFFF")
    # redraw the frame outline last: land fill must not eat it.
    d.rectangle([x, y, x + w, y + h], outline=INK, width=2)


# ---------------------------------------------------------------- page
def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "entry.png")
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # Region colours, shared by the region bar (below) and every
    # illustration background (panel bg): one colour per region.
    REGION_BG = {"ASIA": "#8CF5C8", "EUROPE": "#8ED8FF",
                 "MIDDLE EAST": "#FFE066", "AMERICAS": "#FFB3C8",
                 "AFRICA": "#FFC08A", "OCEANIA": "#D6C9FF",
                 "GLOBAL": "#8CE8E0"}

    # ---- masthead (same style as v20) ----
    f = F(SANS_B, 12)
    d.text((8, 8), "THE DAY IN WORLD NEWS", font=f, fill=RED)
    d.text((W - 8 - d.textlength("ALL STORIES FROM ONE DAY", font=f), 8),
           "ALL STORIES FROM ONE DAY", font=f, fill=INK2)
    f = F(SERIF_B, 44)
    d.text((8, 26), "Saturday 21 November 2026", font=f, fill=INK)
    d.rectangle([8, 74, 8 + d.textlength("Saturday 21 November 2026",
                                         font=f), 78], fill="#FF6FA5")
    f = F(SERIF, 15)
    d.text((8, 78), "US stocks plunge into correction  \u2022  Bitcoin "
           "crashes then rebounds  \u2022  Russian missile hits Kryvyi Rih",
           font=f, fill=RED)
    d.line([8, 102, 1016, 102], fill=INK, width=2)

    # ---- region bar: 6 regions shown (AFRICA 0 is not displayed) ----
    # ASIA 3 / EUROPE 6 / MIDDLE EAST 3 / AMERICAS 6 / OCEANIA 1 /
    # GLOBAL 2  (= 21 panels)
    regions = [("ASIA", "3", "#8CF5C8"), ("EUROPE", "6", "#8ED8FF"),
               ("MIDDLE EAST", "3", "#FFE066"), ("AMERICAS", "6", "#FFB3C8"),
               ("OCEANIA", "1", "#D6C9FF"), ("GLOBAL", "2", "#8CE8E0")]
    x = 8
    seg_w = (W - 16) // len(regions)
    f = F(SANS_B, 13)
    for name, n, col in regions:
        d.rectangle([x, 106, x + seg_w - 4, 128], fill=col, outline=INK,
                    width=1)
        t = f"{name} {n}"
        d.text((x + (seg_w - 4 - d.textlength(t, font=f)) / 2, 112), t,
               font=f, fill=INK)
        x += seg_w

    # ---- numbers strip: 6 cells, two lines each ----
    # Top line: big pink number (~18px bold), centred. Bottom line:
    # small uppercase label (~8px), centred. Cells are separated by
    # vertical divider lines; one outer frame holds the whole strip.
    nums = [("-3.7%", "S&P 500"), ("-5.3%", "NASDAQ"),
            ("$55K", "BTC LOW"), ("$2.53BN", "LIQUIDATED"),
            ("116", "CLASHES"), ("M6.8", "BANDA QUAKE")]
    f = F(SANS_B, 11)
    d.text((8, 134),
           "THE DAY IN NUMBERS  \u00b7  23 STORIES \u00b7 6 REGIONS "
           "\u00b7 21 DRAWN", font=f, fill=RED)
    d.rectangle([8, 148, 1016, 186], fill="#FFFFFF", outline=INK, width=2)
    for i in range(1, 6):
        d.line([8 + i * 168, 148, 8 + i * 168, 186], fill=INK, width=1)
    for i, (v, lbl) in enumerate(nums):
        cx = 8 + i * 168 + 84
        fv = F(SANS_B, 18)
        d.text((cx - d.textlength(v, font=fv) / 2, 153), v, font=fv,
               fill=RED2)
        fl = F(SANS_B, 8)
        d.text((cx - d.textlength(lbl, font=fl) / 2, 174), lbl, font=fl,
               fill=INK)
    d.line([8, 192, 1016, 192], fill=INK, width=1)

    # ---- grid: 8px gaps everywhere, outer margin 8px ----
    # Heroes: 3 columns (331/330/331 -- 1px rounding, the 1008px
    # content width minus 2x8px gaps is not divisible by 3), height
    # 128 = 1.5x the 85px secondary height. Secondary: 5 columns
    # (195/195/196/195/195 -- same 1px rounding), last row holds
    # the remaining 3 panels as 3 equal columns (331/330/331),
    # so no blank cell.
    # Rows: hero y=198, then y=334 / 427 / 520 / 613, all h=85.
    heroes = [
        (1, "AMERICAS", "AMERICAS \u00b7 MARKETS",
         "US STOCKS PLUNGE INTO CORRECTION",
         "S&P -3.7%, Nasdaq -5.3%, Dow -950; 7th fall, 10% off record.",
         art_stocks),
        (2, "GLOBAL", "GLOBAL \u00b7 MARKETS",
         "BITCOIN CRASHES, THEN REBOUNDS",
         "Fell to $55,130, a 2-year low, then +9% back above $60,000.",
         art_btc),
        (3, "EUROPE", "EUROPE \u00b7 WAR",
         "RUSSIAN MISSILE HITS KRYVYI RIH",
         "2 killed, 60+ wounded in Zelenskyy's hometown.", art_missile),
    ]
    hx = 8
    for n, region, tg, head, sub, fn in heroes:
        w = 331 if n != 2 else 330
        panel(d, hx, 198, w, 128, 116, n, tg, head, sub, fn,
              REGION_BG[region], head_size=15, sub_size=10, tag_size=9)
        hx += w + 8

    secondaries = [
        [(4, "MIDDLE EAST", "MIDDLE EAST \u00b7 DEFENCE",
          "SAUDI INTERCEPTS 3 HOUTHI MISSILES",
          "3 Riyadh missiles downed; no damage.", art_saudi),
         (5, "MIDDLE EAST", "MIDDLE EAST \u00b7 WAR",
          "IRAN DOWNS US MQ-9 DRONE",
          "MQ-9 downed over Hormuz; 58th lost.", art_drone),
         (6, "MIDDLE EAST", "MIDDLE EAST \u00b7 WAR",
          "TWO TANKERS STRUCK NEAR HORMUZ",
          "Two tankers hit off Oman; no injuries.", art_tanker),
         (7, "EUROPE", "EUROPE \u00b7 WAR",
          "UKRAINE FRONTLINE: 116 CLASHES",
          "116 clashes, 4,445 drones, 1,599 shells.", art_front),
         (8, "EUROPE", "EUROPE \u00b7 NATO",
          "POLAND FALLOUT: NATO CONDEMNS",
          "'Grave violation'; Trump: mistake.", art_nato)],
        [(9, "EUROPE", "EUROPE \u00b7 SECURITY",
          "DENMARK EXPELS RUSSIAN ATTACH\u00c9",
          "Attach\u00e9 out in 7 days; Russian visas halted.",
          art_denmark),
         (10, "EUROPE", "EUROPE \u00b7 BUSINESS",
          "GERMANY\u2013QATAR \u20ac15BN DEAL",
          "Qatar pledges \u20ac15bn more for Germany.", art_qatar),
         (11, "AMERICAS", "AMERICAS \u00b7 POLITICS",
          "TRUMP LIMITS CONTRACTOR INFO",
          "Contractors: ask White House first.", art_trump21),
         (12, "AMERICAS", "AMERICAS \u00b7 POLITICS",
          "TRUMP PUSHES UKRAINE DEAL BY JANUARY",
          "Ukraine deal push by January; talks resume.", art_deal),
         (13, "AMERICAS", "AMERICAS \u00b7 SPORTS",
          "F1: ANTONELLI FASTEST IN VEGAS",
          "Antonelli 1:33.893; P1 to Verstappen (-5).", art_f1)],
        [(14, "AMERICAS", "AMERICAS \u00b7 MARKETS",
          "NVIDIA -14% TO 52-WEEK LOW",
          "-14% to $125.53; 48% off record.", art_nvidia),
         (15, "GLOBAL", "GLOBAL \u00b7 MARKETS",
          "CRYPTO LIQUIDATIONS TOP $2.53BN",
          "359,742 traders wiped out; fear index at 5.", art_liq),
         (16, "ASIA", "ASIA \u00b7 MARKETS",
          "ASIAN MARKETS TUMBLE 5\u20136.2%",
          "Tokyo, Seoul, Taipei fall 5\u20136.2% on AI rout.", art_tokyo),
         (17, "EUROPE", "EUROPE \u00b7 MARKETS",
          "EUROPEAN STOCKS CLOSE LOWER",
          "DAX -2.6%, CAC -1.9%; worst since March.",
          art_frankfurt),
         (18, "ASIA", "ASIA \u00b7 DISASTER",
          "BANDA SEA M6.8 QUAKE",
          "M6.8, 132 km deep; no damage.",
          art_quake_banda)],
        [(19, "ASIA", "ASIA \u00b7 DISASTER",
          "QINGHAI QUAKE M5.6\u20135.9",
          "M5.6\u20135.9 in Delingha; 1,815 near epicentre.",
          art_quake_qinghai),
         (20, "OCEANIA", "OCEANIA \u00b7 WEATHER",
          "CYCLONE XAVIER WEAKENS TO CAT 1",
          "Cat 1, 75 km/h; was Cat 5 on 17 Nov.", art_xavier21),
         (21, "AMERICAS", "AMERICAS \u00b7 HEALTH",
          "US MEASLES HITS 5,838 CASES",
          "5,838 cases, most since 1991; 646 in hospital, 6 dead.",
          art_measles)],
    ]
    row_y = [334, 427, 520, 613]
    for ri, row in enumerate(secondaries):
        rx = 8
        for n, region, tg, head, sub, fn in row:
            if len(row) == 5:
                w = 196 if n in (6, 11, 16) else 195
            elif len(row) == 3:
                w = 331 if n != 20 else 330
            else:
                w = 500
            panel(d, rx, row_y[ri], w, 85, 62, n, tg, head, sub, fn,
                  REGION_BG[region], head_size=11, sub_size=10, tag_size=8)
            rx += w + 8

    # ---- bottom third (y=703..955): map + info column ----
    # v3: the map is drawn at 60% -- frame 346px wide (was 576),
    # land at 60% of its v2 size, centred in the frame; the frame
    # stays 252px tall so it stays flush with the info box, which
    # takes the freed width: map x=8..354, info x=362..1016.
    draw_map(d, 8, 703, 346, 252, header="WHERE IT HAPPENED")

    # ---- info column box: MAP KEY + ALSO in one framed grid ----
    # Frame drawn BEFORE any text; text starts 12px inside it.
    d.rectangle([362, 703, 1016, 955], fill=CARD, outline=INK, width=2)
    f = F(SANS_B, 11)
    d.text((374, 712), "MAP KEY", font=f, fill=RED)
    d.line([374, 730, 1004, 730], fill=INK, width=1)
    d.line([374, 846, 1004, 846], fill=INK, width=1)

    # ---- map key: three columns x 7 rows, 14px leading ----
    # Column-major order: 1-7 down col 1, 8-14 down col 2, 15-21
    # down col 3. Columns at x=374 / 592 / 810, each ~218px wide;
    # the longest entry ("5 HORMUZ STRAIT") clears its column.
    # 7 rows at 14px leading run 744..828, clearing the 846 divider.
    f = F(SANS, 10)
    key_cols = [["1 NEW YORK", "2 EL SALVADOR", "3 KRYVYI RIH",
                 "4 RIYADH", "5 HORMUZ STRAIT", "6 KHASAB",
                 "7 POKROVSK"],
                ["8 WARSAW", "9 COPENHAGEN", "10 BERLIN",
                 "11 WASHINGTON", "12 ABU DHABI", "13 LAS VEGAS",
                 "14 SANTA CLARA"],
                ["15 SINGAPORE", "16 TOKYO", "17 FRANKFURT",
                 "18 BANDA SEA", "19 DELINGHA", "20 PAGO PAGO",
                 "21 ATLANTA"]]
    for ci, col in enumerate(key_cols):
        for i, entry in enumerate(col):
            d.text((374 + ci * 218, 744 + i * 14), entry, font=f,
                   fill=INK2)

    # ---- ALSO briefs 21-22, same left edge x=374 as the key ----
    f = F(SANS, 10)
    f_b = F(SANS_B, 11)
    d.text((374, 856), "ALSO ON SATURDAY 21 NOVEMBER", font=f_b, fill=RED)
    lines = wrap(d, "22. SPACEX DRAGON splashes down off Southern "
                 "California after 34 days docked at the ISS; 6,300+ lbs "
                 "of cargo.", f, 630)[:3]
    justified_block(d, (374, 884), lines, f, INK2, max_w=630, leading=16)
    y2 = 884 + len(lines) * 16 + 10
    lines = wrap(d, "23. ATP FINALS: Alcaraz beats Shelton; Zverev beats "
                 "Medvedev to set up an Alcaraz\u2013Zverev final.", f,
                 630)[:3]
    justified_block(d, (374, y2), lines, f, INK2, max_w=630, leading=16)

    # ---- DATE CHECK (full width 8..1016) ----
    d.rectangle([8, 960, 1016, 1004], outline=RED2, width=3,
                fill="#FFE3EC")
    f = F(SANS_B, 12)
    d.text((20, 965), "DATE CHECK \u2014 NOT 21 NOV NEWS:", font=f,
           fill=RED2)
    f = F(SANS, 10)
    body = ("Poland missiles, F1 qualifying, US stock moves and the "
            "CDC measles update are all from Fri 20 Nov, first "
            "reported Sat 21 Nov \u2014 only the 21 Nov reactions "
            "are shown.")
    lines = wrap(d, body, f, 976)[:2]
    justified_block(d, (20, 978), lines, f, INK2, max_w=976, leading=11)

    # ---- footer (full width, same 8..1016 span) ----
    f = F(SANS, 10)
    d.text((8, 1008),
           "Sources: Reuters \u00b7 AP \u00b7 Al Jazeera \u00b7 Washington "
           "Post \u00b7 CoinDesk \u00b7 Le Monde \u00b7 Xinhua \u00b7 ATP "
           "Tour. All stories from Saturday 21 November 2026.",
           font=f, fill="#555555")
    d.text((W - 8 - d.textlength("make.fun / @inl-xin", font=f), 1008),
           "make.fun / @inl-xin", font=f, fill="#555555")

    img.save(out, "PNG", optimize=True)
    print("saved", out, img.size)

if __name__ == "__main__":
    main()
