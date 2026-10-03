#!/usr/bin/env python3
"""Redraw the client cover images for the portfolio carousel and work page.

    python3 tools/make-portfolio-covers.py

Writes images/marketready-cover.png, images/floralsromero-cover.png and
images/golden-ridge-cover.png: 1200x630, each project's mark in its own original ink on a *transparent*
background.

The background isn't baked in on purpose. Each client's ground colour is
painted behind the image by CSS (the .brand-cover-* rules in styles.css), so it fills whatever shape the card's
image area takes at any screen width, right into the card's rounded corners,
without cropping the mark the way object-fit: cover would.

  * FloralsRomero: her signature is redrawn from the traced path in her site's
    index.html (no cut-out, so no fringe), in the same deep-rose ramp her own
    social card uses.
  * Golden Ridge: the transparent logo their site already ships, set at the
    width their social card uses.
  * MarketReady: lifted off its own social banner, which draws the logo on a
    flat #080809 panel with baked-in rounded corners and a border. The logo
    comes off by colour-to-alpha; the panel's border and corners are dropped.

Both client repos are read in place; nothing here is copied by hand.
"""

import pathlib

import numpy as np
from PIL import Image, ImageChops, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
DESKTOP = pathlib.Path.home() / "Desktop"
FLORALS_INDEX = DESKTOP / "Customer Websites " / "FloralsRomero" / "public" / "index.html"
GOLDEN_LOGO = DESKTOP / "Golden Ridge" / "images" / "golden-ridge-landscaping-logo.webp"
MARKET_BANNER = DESKTOP / "MarketReady.Trade" / "public" / "media" / "marketready_banner_1200x630.png"

W, H = 1200, 630
SS = 4  # supersample factor for the signature

# FloralsRomero site.css: the deepest three of Zaira's five paint codes, the
# same ramp her make-og-card.py inks the social card with.
ROSE_1 = (138, 90, 88)
ROSE_2 = (170, 122, 119)
ROSE_3 = (196, 140, 139)


def florals_cover():
    import re

    m = re.search(r'<path class="mk"[^>]*\sd="([^"]+)"', FLORALS_INDEX.read_text())
    subpaths, current = [], []
    for cmd, nums in re.findall(r"([MLZ])([^MLZ]*)", m.group(1)):
        if cmd == "Z":
            if len(current) >= 3:
                subpaths.append(current)
            current = []
            continue
        vals = [float(v) for v in nums.replace(",", " ").split()]
        current.extend(zip(vals[0::2], vals[1::2]))
    if len(current) >= 3:
        subpaths.append(current)

    # Same size and evenodd XOR as her make-og-card.py, so the mark is framed
    # exactly as it was on the cream card.
    sig_w = 700
    s = sig_w * SS / 1000.0
    acc = Image.new("1", (sig_w * SS, round(372 * s)), 0)
    for pts in subpaths:
        layer = Image.new("1", acc.size, 0)
        ImageDraw.Draw(layer).polygon([(x * s, y * s) for x, y in pts], fill=1)
        acc = ImageChops.logical_xor(acc, layer)
    mask = acc.convert("L").resize((sig_w, round(372 * sig_w / 1000)), Image.LANCZOS)

    # Deep-to-lighter across the stroke, as on her own social card.
    t = np.linspace(0, 1, mask.width)[:, None]
    stops = [(0.0, ROSE_1), (0.55, ROSE_2), (1.0, ROSE_3)]
    row = np.zeros((mask.width, 3))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        k = np.clip((t - t0) / (t1 - t0), 0, 1)
        seg = (t[:, 0] >= t0) & (t[:, 0] <= t1)
        row[seg] = (np.array(c0) + (np.array(c1) - np.array(c0)) * k)[seg]
    ink = np.repeat(row[None, :, :], mask.height, axis=0).astype(np.uint8)
    sig = Image.fromarray(ink).convert("RGBA")
    sig.putalpha(mask)

    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    box = mask.getbbox()
    x = (W - (box[2] - box[0])) // 2 - box[0]
    y = (H - (box[3] - box[1])) // 2 - box[1]
    card.alpha_composite(sig, (x, y))
    return card


def golden_cover():
    logo = Image.open(GOLDEN_LOGO).convert("RGBA")

    # Their og card sets the logo ~980px wide on 1200; match it.
    target_w = 980
    logo = logo.resize((target_w, round(logo.height * target_w / logo.width)), Image.LANCZOS)
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card.alpha_composite(logo, ((W - logo.width) // 2, (H - logo.height) // 2))
    return card


def marketready_cover():
    """Colour-to-alpha against the banner's flat panel.

    Every pixel of the logo's anti-aliased edge is a blend of a logo colour and
    the panel: p = a*fg + (1-a)*bg. Knowing bg, the smallest a that keeps fg a
    valid colour is how far p has moved from bg, as a fraction of how far it
    *could* move in that direction. That recovers soft edges exactly, where a
    plain "is it background? then clear it" test would leave a dark fringe."""
    px = np.asarray(Image.open(MARKET_BANNER).convert("RGB"), dtype=np.float32)
    bg = np.array([8, 8, 9], dtype=np.float32)

    diff = px - bg
    room = np.where(diff >= 0, 255 - bg, bg)
    alpha = (np.abs(diff) / room).max(axis=2, keepdims=True)
    fg = bg + diff / np.maximum(alpha, 1e-6)

    # The banner's own rounded corners and 1px border sit in the outer ~20px;
    # the logo is nowhere near them (its ink spans rows ~275-354). Drop that
    # frame so the card's corners are the only ones.
    alpha[:40, :] = 0
    alpha[-40:, :] = 0
    alpha[:, :40] = 0
    alpha[:, -40:] = 0

    out = np.concatenate([np.clip(fg, 0, 255), alpha * 255], axis=2)
    return Image.fromarray(out.round().astype(np.uint8))


def main():
    for name, make in (
        ("marketready-cover.png", marketready_cover),
        ("floralsromero-cover.png", florals_cover),
        ("golden-ridge-cover.png", golden_cover),
    ):
        out = ROOT / "images" / name
        make().save(out, optimize=True)
        print(f"wrote {out.relative_to(ROOT)}  {W}x{H}  {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
