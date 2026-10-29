#!/usr/bin/env python3
"""Generate the 1200x630 social preview card for Battery Alert Pro.

Usage (from anywhere; paths are resolved relative to the repository root):

    python3 tools/make_social_card.py

Requires Pillow and the Noto Sans fonts (Debian/Ubuntu: `fonts-noto-core`).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent

W, H = 1200, 630
ACCENT = (0, 149, 213)
TEXT = (26, 26, 26)
MUTED = (95, 95, 95)
CHIP_BG = (223, 242, 251)
RULE_BG = (226, 242, 251)

REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"

LEFT_X = 72
LEFT_W = 560  # left column width, before the screenshot starts at x=660


def fit_font(text, path, max_size, max_w, min_size=14):
    """Largest font size at which `text` fits within `max_w`."""
    size = max_size
    while size > min_size:
        f = ImageFont.truetype(path, size)
        if ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(text, font=f) <= max_w:
            return f
        size -= 1
    return ImageFont.truetype(path, min_size)


# --- background -------------------------------------------------------------
bg = Image.new("RGBA", (W, H), (255, 255, 255, 255))

# soft accent wash, built on its own layer then composited
wash = Image.new("RGBA", (W, H), (0, 0, 0, 0))
wd = ImageDraw.Draw(wash)
wd.ellipse([-260, -330, 620, 430], fill=ACCENT + (30,))
wd.ellipse([-160, -420, 760, 220], fill=ACCENT + (18,))
bg = Image.alpha_composite(bg, wash.filter(ImageFilter.GaussianBlur(90)))

draw = ImageDraw.Draw(bg)

# decorative diagonal hatch, bottom-right (opaque light tint)
for i in range(0, 30):
    draw.line([(860 + i * 15, H), (860 + i * 15 - 170, 400)], fill=RULE_BG, width=2)

# --- app icon ---------------------------------------------------------------
logo = Image.open(ROOT / "image.png").convert("RGBA").resize((92, 92), Image.LANCZOS)
bg.paste(logo, (LEFT_X, 66), logo)

# --- title ------------------------------------------------------------------
f_title = fit_font("Battery Alert Pro", BOLD, 58, LEFT_W)
draw.text((LEFT_X, 186), "Battery Alert Pro", font=f_title, fill=TEXT)
draw.rectangle([LEFT_X, 272, LEFT_X + 96, 276], fill=ACCENT)

# --- subtitle ---------------------------------------------------------------
f_sub = fit_font("Smart Battery Management for Windows", REG, 28, LEFT_W)
draw.text((LEFT_X, 298), "Smart Battery Management for Windows", font=f_sub, fill=MUTED)

# --- feature chips ----------------------------------------------------------
f_chip = ImageFont.truetype(BOLD, 20)
chips = ["Low & High Alerts", "Smart Hysteresis", "Autostart", "System Tray"]
x, y = LEFT_X, 386
for label in chips:
    tw = draw.textlength(label, font=f_chip)
    cw = int(tw) + 44
    if x + cw > LEFT_X + LEFT_W:
        x, y = LEFT_X, y + 56
    draw.rounded_rectangle([x, y, x + cw, y + 44], radius=22, fill=CHIP_BG)
    draw.text((x + 22, y + 11), label, font=f_chip, fill=ACCENT)
    x += cw + 16

# --- window mockup on the right ---------------------------------------------
sx, sy = 660, 100
shot = Image.open(ROOT / "main_screen.png").convert("RGBA")
frame_w = 492
frame_h = round(shot.height * frame_w / shot.width)
shot = shot.resize((frame_w, frame_h), Image.LANCZOS)

shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rounded_rectangle(
    [sx + 5, sy + 10, sx + frame_w + 5, sy + frame_h + 10], radius=14, fill=(0, 0, 0, 60)
)
bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(16)))

bg.paste(shot, (sx, sy), shot)
ImageDraw.Draw(bg).rounded_rectangle(
    [sx, sy, sx + frame_w, sy + frame_h], radius=6, outline=(214, 214, 214), width=2
)

# --- footer strip -----------------------------------------------------------
fd = ImageDraw.Draw(bg)
fd.rectangle([0, H - 50, W, H], fill=(250, 251, 252))
fd.line([(0, H - 50), (W, H - 50)], fill=(233, 233, 233), width=1)
fd.text(
    (LEFT_X, H - 36),
    "Woteq Software  ·  Free 7-day trial  ·  Windows 10 & 11",
    font=ImageFont.truetype(REG, 19),
    fill=MUTED,
)

out = ROOT / "social_card.png"
bg.convert("RGB").save(out, "PNG", optimize=True)
print("wrote", out, bg.size)
