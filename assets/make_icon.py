# kasa/assets/make_icon.py
# KASA uygulama ikonu uretir (cok-cozunurluklu .ico). Marka: koyu zemin (#0D1017) +
# kirmizi kasa kadrani (#E02244), tray ikonuyla uyumlu. Build-asseti; IP degil.
# Kullanim: py -3.12 assets/make_icon.py

import pathlib

from PIL import Image, ImageDraw

BG = (13, 16, 23, 255)      # #0D1017 koyu zemin
PANEL = (22, 27, 38, 255)   # hafif acik panel
RED = (224, 34, 68, 255)    # #E02244 marka kirmizisi
LIGHT = (240, 243, 248, 255)


def render(size: int) -> Image.Image:
    # Buyuk ciz, sonra kucult (kenar yumusatma).
    S = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Yuvarlatilmis koseli zemin.
    r = int(S * 0.22)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=BG)
    m = int(S * 0.14)
    d.rounded_rectangle([m, m, S - 1 - m, S - 1 - m], radius=int(r * 0.7), outline=PANEL, width=max(2, S // 64))

    # Kasa kadrani (dial): dis halka + ic disk.
    cx = cy = S / 2
    R = S * 0.26
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=RED, width=max(3, S // 24))
    r2 = R * 0.52
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=RED)
    r3 = r2 * 0.45
    d.ellipse([cx - r3, cy - r3, cx + r3, cy + r3], fill=BG)

    # Kadran cizgileri (4 yon).
    tick = S * 0.045
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        x0 = cx + dx * (R + tick * 0.4)
        y0 = cy + dy * (R + tick * 0.4)
        x1 = cx + dx * (R + tick * 1.6)
        y1 = cy + dy * (R + tick * 1.6)
        d.line([x0, y0, x1, y1], fill=LIGHT, width=max(2, S // 48))

    # Kol (handle) — sag alt capraz.
    hx, hy = cx + R * 0.72, cy + R * 0.72
    d.line([cx, cy, hx, hy], fill=LIGHT, width=max(3, S // 30))
    d.ellipse([hx - tick * 0.6, hy - tick * 0.6, hx + tick * 0.6, hy + tick * 0.6], fill=LIGHT)

    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base = render(256)
    out = pathlib.Path(__file__).parent / "icon.ico"
    base.save(out, format="ICO", sizes=[(s, s) for s in sizes])
    print("wrote", out, "sizes", sizes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
