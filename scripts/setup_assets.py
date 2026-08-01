"""Generate OrcFin logo and Windows .ico in assets/ with transparent corners.

The source mark is a rounded-square on a solid white canvas (often saved as
JPEG-in-disguise). Desktop icons must not show that white square — only the
squircle itself. White text *inside* the mark is preserved via edge flood-fill.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICO_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]


def _fallback_logo(path: Path) -> None:
    """Vector-ish mark with real alpha (no white canvas)."""
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((24, 24, 488, 488), radius=112, fill=(15, 23, 42, 255))
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


def _is_near_white(rgb: np.ndarray, tol: int) -> np.ndarray:
    """rgb: HxWx3 uint8 -> bool mask of near-white pixels."""
    return (
        (rgb[:, :, 0] >= 255 - tol)
        & (rgb[:, :, 1] >= 255 - tol)
        & (rgb[:, :, 2] >= 255 - tol)
    )


def remove_edge_white_background(
    img: Image.Image,
    hard_tol: int = 28,
    soft_tol: int = 55,
) -> Image.Image:
    """Make the outer white canvas transparent; keep white glyphs inside the mark.

    1. Flood-fill near-white pixels connected to the image border (hard cut).
    2. Soften the anti-aliased fringe (JPEG bleed of white into the squircle edge).
    """
    rgba = np.array(img.convert("RGBA"))
    h, w = rgba.shape[:2]
    rgb = rgba[:, :, :3]
    hard = _is_near_white(rgb, hard_tol)

    bg = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        if hard[0, x]:
            bg[0, x] = True
            q.append((0, x))
        if hard[h - 1, x]:
            bg[h - 1, x] = True
            q.append((h - 1, x))
    for y in range(h):
        if hard[y, 0] and not bg[y, 0]:
            bg[y, 0] = True
            q.append((y, 0))
        if hard[y, w - 1] and not bg[y, w - 1]:
            bg[y, w - 1] = True
            q.append((y, w - 1))

    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and not bg[ny, nx] and hard[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))

    out = rgba.copy()
    out[bg, 3] = 0

    # Soft fringe: near-white pixels adjacent to removed bg get partial alpha
    # (and despill toward the body color). Does not touch interior white text —
    # those pixels are not edge-adjacent to the outer canvas.
    soft = _is_near_white(rgb, soft_tol) & ~bg
    if soft.any():
        # 4-neighborhood of hard background
        dilated = bg.copy()
        dilated[1:, :] |= bg[:-1, :]
        dilated[:-1, :] |= bg[1:, :]
        dilated[:, 1:] |= bg[:, :-1]
        dilated[:, :-1] |= bg[:, 1:]
        fringe = soft & dilated
        if fringe.any():
            # Alpha from how far from pure white (higher channel min => more transparent)
            channel_min = rgb.min(axis=2).astype(np.float32)
            # Map [255-soft_tol, 255] -> [255, 0]
            t = np.clip((channel_min - (255 - soft_tol)) / max(soft_tol, 1), 0.0, 1.0)
            soft_alpha = (255.0 * (1.0 - t)).astype(np.uint8)
            ys, xs = np.where(fringe)
            out[ys, xs, 3] = np.minimum(out[ys, xs, 3], soft_alpha[ys, xs])
            # Despill: pull RGB away from white on fringe so no halo remains
            for c in range(3):
                out[ys, xs, c] = np.minimum(out[ys, xs, c], rgb[ys, xs, c])

    # Slight blur on alpha only at very small sizes is handled per ICO size later;
    # keep master sharp.
    return Image.fromarray(out, "RGBA")


def _has_outer_white(img: Image.Image, tol: int = 20) -> bool:
    arr = np.array(img.convert("RGBA"))
    h, w = arr.shape[:2]
    corners = [arr[0, 0], arr[0, w - 1], arr[h - 1, 0], arr[h - 1, w - 1]]
    for r, g, b, a in corners:
        if a > 200 and r >= 255 - tol and g >= 255 - tol and b >= 255 - tol:
            return True
    return False


def write_ico(img: Image.Image, path: Path) -> None:
    """Write multi-resolution ICO with alpha (Windows desktop)."""
    frames: list[Image.Image] = []
    for size in ICO_SIZES:
        frame = img.resize(size, Image.Resampling.LANCZOS)
        # Tiny sizes: slight alpha expand so soft edges don't vanish
        if size[0] <= 32:
            alpha = frame.split()[3]
            alpha = alpha.filter(ImageFilter.MaxFilter(3))
            r, g, b, _ = frame.split()
            frame = Image.merge("RGBA", (r, g, b, alpha))
        frames.append(frame)
    # Pillow: first image + append_images for extra sizes
    frames[0].save(
        path,
        format="ICO",
        sizes=ICO_SIZES,
        append_images=frames[1:],
    )


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    png_out = ASSETS / "orcfin_logo.png"
    ico_out = ASSETS / "orcfin.ico"

    if not png_out.exists():
        _fallback_logo(png_out)

    img = Image.open(png_out).convert("RGBA")
    if _has_outer_white(img):
        img = remove_edge_white_background(img)
        # Always rewrite as real PNG with alpha (source may have been JPEG data).
        img.save(png_out, format="PNG", optimize=True)
        print(f"Updated transparent PNG: {png_out}")
    else:
        print(f"PNG already has transparent outer canvas: {png_out.name}")

    write_ico(img, ico_out)
    print(f"Wrote ICO: {ico_out} sizes={','.join(str(s[0]) for s in ICO_SIZES)}")

    # Sanity: corners must be transparent
    check = Image.open(ico_out).convert("RGBA")
    w, h = check.size
    for label, xy in (
        ("TL", (0, 0)),
        ("TR", (w - 1, 0)),
        ("BL", (0, h - 1)),
        ("BR", (w - 1, h - 1)),
    ):
        a = check.getpixel(xy)[3]
        if a > 10:
            print(f"WARNING: ICO corner {label} alpha={a} (expected ~0)")
        else:
            print(f"OK corner {label} alpha={a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
