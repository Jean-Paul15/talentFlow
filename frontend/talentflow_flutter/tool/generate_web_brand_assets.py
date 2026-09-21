from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "images" / "logo.png"
WEB = ROOT / "web"
ICONS = WEB / "icons"

BACKGROUND = "#FFF8F2"
HIGHLIGHT = "#F9E4D9"
SHADOW = (22, 30, 40, 28)


def _load_logo() -> Image.Image:
    image = Image.open(SOURCE).convert("RGBA")
    return image.crop(image.getbbox())


def _rounded_background(size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), BACKGROUND)

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        (
            int(size * 0.18),
            int(size * 0.12),
            int(size * 0.82),
            int(size * 0.76),
        ),
        fill=HIGHLIGHT,
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(4, size // 14)))
    canvas.alpha_composite(glow)

    return canvas


def _compose_icon(size: int, scale: float) -> Image.Image:
    base = _rounded_background(size)
    logo = _load_logo()

    logo.thumbnail((int(size * scale), int(size * scale)), Image.LANCZOS)

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sx = (size - logo.width) // 2
    sy = (size - logo.height) // 2 + max(2, size // 48)
    shadow.alpha_composite(
        Image.new("RGBA", logo.size, SHADOW),
        (sx, sy),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(2, size // 64)))
    base.alpha_composite(shadow)

    x = (size - logo.width) // 2
    y = (size - logo.height) // 2
    base.alpha_composite(logo, (x, y))
    return base


def main() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)

    outputs = {
        WEB / "favicon.png": _compose_icon(64, 0.78),
        ICONS / "apple-touch-icon.png": _compose_icon(180, 0.76),
        ICONS / "Icon-192.png": _compose_icon(192, 0.74),
        ICONS / "Icon-512.png": _compose_icon(512, 0.74),
        ICONS / "Icon-maskable-192.png": _compose_icon(192, 0.62),
        ICONS / "Icon-maskable-512.png": _compose_icon(512, 0.62),
    }

    for path, image in outputs.items():
        image.save(path, format="PNG")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
