"""Images for LVGL — Pillow in, LVGL 9's binary image format out.

A panel without a decoder or the RAM for one can still draw a picture if the
picture arrives in the form LVGL draws from: a 12-byte header, RGB565 rows, and
an A8 alpha plane when anything is not opaque. Resizing happens here too, once,
on the host, so the device never scales at runtime unless its panel differs
from the design size.
"""

from __future__ import annotations

import struct

from PIL import Image

MAGIC = 0x19            # LV_IMAGE_HEADER_MAGIC: LVGL 9 images
CF_RGB565 = 0x12        # LV_COLOR_FORMAT_RGB565
CF_RGB565A8 = 0x14      # LV_COLOR_FORMAT_RGB565A8: colour rows, then alpha rows

__all__ = ["fit_image", "to_lvgl_bin"]


def fit_image(img: Image.Image, w: int, h: int, fit: str) -> Image.Image:
    """Resize `img` into a w x h box per CSS object-fit. Returns a w x h image.

    - fill    : stretch to w x h (aspect ignored) — the default
    - contain : whole image fits inside, aspect kept, transparent letterbox
    - cover   : image covers the box, aspect kept, overflow centre-cropped
    """
    iw, ih = img.size
    if fit == "contain":
        scale = min(w / iw, h / ih)
        nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        out.alpha_composite(img.resize((nw, nh)), ((w - nw) // 2, (h - nh) // 2))
        return out
    if fit == "cover":
        scale = max(w / iw, h / ih)
        nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
        scaled = img.resize((nw, nh))
        left, top = (nw - w) // 2, (nh - h) // 2
        return scaled.crop((left, top, left + w, top + h))
    return img.resize((w, h))   # fill


def to_lvgl_bin(img: Image.Image) -> bytes:
    """An RGBA image -> LVGL 9 `.bin` bytes: RGB565, or RGB565A8 if any pixel
    is not fully opaque. Little-endian, as on every ESP32 and ARM/x86 host."""
    img = img.convert("RGBA")
    w, h = img.size
    if w > 0xFFFF or h > 0xFFFF:
        raise ValueError(f"image {w}x{h} is larger than LVGL's 16-bit size fields")

    pixels = img.tobytes()
    alpha = pixels[3::4]
    opaque = alpha.count(255) == w * h
    cf = CF_RGB565 if opaque else CF_RGB565A8
    stride = w * 2

    colour = bytearray(w * h * 2)
    for i in range(w * h):
        r, g, b = pixels[i * 4], pixels[i * 4 + 1], pixels[i * 4 + 2]
        struct.pack_into("<H", colour, i * 2, ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3))

    header = struct.pack("<BBHHHHH", MAGIC, cf, 0, w, h, stride, 0)
    return header + bytes(colour) + (b"" if opaque else alpha)
