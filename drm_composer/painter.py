"""Painter — Scene -> RGBA layer bitmaps -> drm_screen command batch.

Each layer becomes its own full-screen RGBA canvas; box/text/img nodes are drawn
into it at their coordinates.  The output is a list of drm_screen command records
(the stable contract) — this module never blends the final screen and never
touches DRM.

Channel order is RGBA throughout; the single RGBA->BGRA conversion happens far
downstream in drm_screen's backend.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from drm_screen.commands import CreateLayer, PlaceRawBuffer

from .scene import Scene, BoxNode, TextNode, ImageNode


def _rgba(color: str) -> tuple[int, int, int, int]:
    """Parse #rgb / #rrggbb / #rrggbbaa (and a few names) -> (r,g,b,a)."""
    named = {"white": "#ffffff", "black": "#000000", "red": "#ff0000",
             "green": "#00ff00", "blue": "#0000ff"}
    c = named.get(color.strip().lower(), color).lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) == 6:
        c += "ff"
    if len(c) != 8:
        raise ValueError(f"bad color {color!r}")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4, 6))


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def paint_scene(scene: Scene) -> list:
    """Compile a Scene into a drm_screen command batch."""
    W, H = scene.width, scene.height
    batch = []

    for layer in scene.layers:
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        for node in layer.children:
            if isinstance(node, BoxNode):
                draw.rectangle(
                    [node.x, node.y, node.x + node.w - 1, node.y + node.h - 1],
                    fill=_rgba(node.color),
                )
            elif isinstance(node, TextNode):
                draw.text((node.x, node.y), node.text,
                          fill=_rgba(node.color), font=_font(node.size))
            elif isinstance(node, ImageNode):
                _paste_image(canvas, node)

        rgba = np.asarray(canvas, dtype=np.uint8)
        batch.append(CreateLayer(layer.id, W, H, z=layer.z, visible=layer.visible))
        batch.append(PlaceRawBuffer(
            name=layer.id, width=W, height=H,
            data=np.ascontiguousarray(rgba).tobytes(),
        ))

    return batch


def _paste_image(canvas: Image.Image, node: ImageNode):
    img = Image.open(node.src).convert("RGBA")
    if node.w and node.h:
        img = img.resize((node.w, node.h))
    canvas.alpha_composite(img, (node.x, node.y))
