"""Generate OrcFin logo and Windows .ico in assets/."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def _fallback_logo(path: Path) -> None:
    img = Image.new("RGBA", (512, 512), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((48, 48, 464, 464), radius=96, fill=(20, 184, 166, 255))
    draw.rounded_rectangle((120, 280, 180, 380), radius=12, fill=(255, 255, 255, 255))
    draw.rounded_rectangle((220, 220, 280, 380), radius=12, fill=(255, 255, 255, 230))
    draw.rounded_rectangle((320, 160, 380, 380), radius=12, fill=(255, 255, 255, 200))
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 72)
    except OSError:
        font = ImageFont.load_default()
    draw.text((256, 420), "OrcFin", fill=(255, 255, 255, 255), anchor="mm", font=font)
    img.save(path, format="PNG")


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    png_out = ASSETS / "orcfin_logo.png"
    ico_out = ASSETS / "orcfin.ico"

    if not png_out.exists():
        _fallback_logo(png_out)

    img = Image.open(png_out).convert("RGBA")
    img.save(ico_out, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Assets ready: {png_out.name}, {ico_out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())