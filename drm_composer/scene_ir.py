"""Scene IR — a layer of primitives, as a document the panel can evaluate.

Everything else in this package ends in pixels: `painter.py` rasterises a layer
into an RGBA bitmap and sends it as `PlaceRawBuffer`. That is right for a
photograph, and it is wrong for a stroke that is supposed to draw itself,
because a bitmap has no way to be half a line.

So a layer holding `<path>` elements compiles to this instead: a small JSON
document that says what the shapes are and how their properties move over time.
It is sent once, as `PlaceScene`, and the renderer evaluates it against the
clock every frame. A 1.4 KB document fills 1920x1080 with no bitmap in it
anywhere.

    <path d="M 20 300 L 780 300" progress="0">
      <animate property="progress" from="0" to="1" duration="3000" />
    </path>

becomes

    {"version": 1, "width": 800, "height": 480, "duration": 3000,
     "layers": [{"id": "ink", "z": 20, "objects": [
        {"type": "path", "id": "line", "d": "M 20 300 L 780 300",
         "stroke": "#e8e8f0", "stroke_width": 3, "progress": 0}]}],
     "animations": [{"target": "line", "property": "progress",
                     "start": 0, "duration": 3000, "from": 0, "to": 1,
                     "easing": "linear"}]}

`<box>` and `<text>` have a scene form too (`rect`, `text`), so they may share a
layer with paths. `<img>` and `<button>` do not: a scene has no pixels to paste
and nothing to tap.

`emit_screen_ir` compiles the whole screen into one document. That is what a
panel without Python and without a layer compositor loads -- the ESP32 player
holds exactly one scene, drawn from its layers by z.

The document is the contract between this compiler and whatever draws it, and
it is deliberately not this package's invention: it is `drm_scene_ir`, the same
format the ESP32 player loads. Version it there, not here.
"""

from __future__ import annotations

import itertools
import json
import pathlib
import re
import zlib

from .scene import AnimateNode, BoxNode, ImageNode, PathNode, TextNode

__all__ = [
    "SCENE_IR_VERSION", "emit_scene_ir", "emit_scene_json",
    "emit_screen_ir", "emit_screen_json", "layer_is_vector",
]

SCENE_IR_VERSION = 1

_SCENE_FORM = (PathNode, BoxNode, TextNode)


def layer_is_vector(layer) -> bool:
    """True when this layer must be a scene: it holds a path.

    A layer of only boxes and text could be either, and stays pixels, so the
    RGBA compositor keeps drawing it without a scene renderer.
    """
    return any(isinstance(node, PathNode) for node in layer.children)


def emit_scene_ir(scene, layer, name: str | None = None) -> dict:
    """One layer -> a scene document.

    The layer keeps the whole screen's coordinate system: a scene carries its
    own design size and the renderer fits it to the panel, so the same document
    is correct on a 450x250 panel and on a 1920x1080 one.
    """
    return _document(scene, [layer], name or layer.id)


def emit_scene_json(scene, layer, name: str | None = None) -> bytes:
    """The document as bytes, ready for `PlaceScene`."""
    return _bytes(emit_scene_ir(scene, layer, name))


def emit_screen_ir(scene, name: str = "screen", assets: dict | None = None,
                   base_dir=".") -> dict:
    """Every layer of the screen -> one scene document, layers kept by z.

    For a player that loads a single scene and has no layer commands: the
    ESP32 panel. A hidden layer's objects are carried with `visible: false`.

    `<img>` needs `assets`: each picture is fitted to its box, converted to
    LVGL's binary image format and put in the dict as `{"<name>.bin": bytes}`,
    and the document refers to it by that readable name with its size and
    CRC32, so a player can tell a file that belongs to another build. Sources
    are read relative to `base_dir`. A dict shared across several screens
    stores an identical picture once.
    """
    images = None if assets is None else _ImageAssets(assets, base_dir)
    return _document(scene, scene.layers, name, images)


def emit_screen_json(scene, name: str = "screen", assets: dict | None = None,
                     base_dir=".") -> bytes:
    """The whole-screen document as bytes, ready to embed or send."""
    return _bytes(emit_screen_ir(scene, name, assets, base_dir))


class _ImageAssets:
    """Pictures for a scene: converted once, named for people, checked by CRC."""

    def __init__(self, store: dict, base_dir):
        self.store = store
        self.base_dir = pathlib.Path(base_dir)

    def add(self, node, serial, scene) -> dict:
        from PIL import Image

        from .lvgl_image import fit_image, to_lvgl_bin

        if node.fullscreen == "always":
            x, y, w, h = 0, 0, scene.width, scene.height
        else:
            x, y, w, h = node.x, node.y, node.w, node.h
        path = self.base_dir / node.src
        try:
            picture = Image.open(path).convert("RGBA")
        except OSError as exc:
            raise ValueError(f"<img src={node.src!r}>: cannot read {path}: {exc}") from exc
        if w and h:
            picture = fit_image(picture, w, h, node.fit)

        data = to_lvgl_bin(picture)
        name = self._name(node.src, picture.size, data)
        self.store[f"{name}.bin"] = data
        return {
            "type": "image",
            "id": f"img{next(serial)}",
            "x": x, "y": y, "w": picture.width, "h": picture.height,
            "src": name,
            "size": len(data),
            "crc32": zlib.crc32(data),
        }

    def _name(self, src: str, size, data: bytes) -> str:
        """The source's stem; its size appended only when that stem already
        names different bytes -- the same picture drawn at two sizes."""
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", pathlib.PurePath(src).stem)[:40] or "image"
        sized = f"{stem}-{size[0]}x{size[1]}"
        candidates = [stem, sized] + [f"{sized}-{n}" for n in range(2, 100)]
        for candidate in candidates:
            existing = self.store.get(f"{candidate}.bin")
            if existing is None or existing == data:
                return candidate
        raise ValueError(f"too many different pictures named {stem!r}")


def _document(scene, layers, name: str, images: "_ImageAssets | None" = None) -> dict:
    serial = itertools.count()
    seen: set[str] = set()
    out_layers = []
    animations = []

    for layer in layers:
        objects = []
        for node in layer.children:
            if isinstance(node, ImageNode) and images is not None:
                obj = images.add(node, serial, scene)
            elif isinstance(node, _SCENE_FORM):
                obj = _object(node, serial)
            elif isinstance(node, ImageNode):
                raise ValueError(
                    f"layer {layer.id!r}: <img> becomes a scene asset only in a "
                    f"whole-screen document -- emit_screen_ir(scene, assets={{}})"
                )
            else:
                raise ValueError(
                    f"layer {layer.id!r} mixes primitives with pixels: "
                    f"<{_tag(node)}> has no scene form (only <box>, <text>, "
                    f"<path>, and <img> with assets do) -- give it a layer of its own"
                )
            if obj["id"] in seen:
                raise ValueError(
                    f"object id {obj['id']!r} is used twice; animations find "
                    f"their target by id, so ids must be unique in a scene"
                )
            seen.add(obj["id"])
            if not layer.visible:
                obj["visible"] = False
            objects.append(obj)

            for animation in getattr(node, "animations", ()):
                animations.append(_animation(animation))

        out_layers.append({"id": layer.id, "z": layer.z, "objects": objects})

    return {
        "version": SCENE_IR_VERSION,
        "name": name,
        "width": scene.width,
        "height": scene.height,
        "fit": "contain",
        "duration": _duration(animations),
        "layers": out_layers,
        "animations": animations,
    }


def _object(node, serial) -> dict:
    if isinstance(node, PathNode):
        obj = {
            "type": "path",
            "id": node.id,
            "d": node.d,
            "stroke": _hex(node.stroke),
            "stroke_width": node.stroke_width,
            "progress": node.progress,
        }
        if node.fill:
            obj["fill"] = _hex(node.fill)
        if node.opacity != 1.0:
            obj["opacity"] = node.opacity
        return obj

    if isinstance(node, BoxNode):
        fill, alpha = _fill(node.color)
        obj = {
            "type": "rect",
            "id": f"box{next(serial)}",
            "x": node.x, "y": node.y, "w": node.w, "h": node.h,
            "fill": fill,
        }
    else:
        colour, alpha = _fill(node.color)
        obj = {
            "type": "text",
            "id": f"text{next(serial)}",
            "content": node.text,
            # The player picks the nearest size it was built with.
            "font_id": f"montserrat-{node.size}",
            "x": node.x, "y": node.y,
            "color": colour,
        }
    # An unreadable colour is transparent, as the painter treats it.
    if alpha < 1.0:
        obj["opacity"] = round(alpha, 4)
    return obj


def _tag(node) -> str:
    return {"ImageNode": "img", "ButtonNode": "button"}.get(
        type(node).__name__, type(node).__name__)


def _animation(node: AnimateNode) -> dict:
    return {
        "target": node.target,
        "property": node.property,
        "start": node.start,
        "duration": node.duration,
        "from": node.frm,
        "to": node.to,
        "easing": node.easing,
    }


def _duration(animations) -> int:
    """How long the scene lasts: until the last thing stops moving."""
    return max((a["start"] + a["duration"] for a in animations), default=0)


def _bytes(document: dict) -> bytes:
    return json.dumps(document, separators=(",", ":")).encode()


def _colour(color: str) -> tuple[str, float] | None:
    """A CSS colour -> (`#rrggbb`, alpha 0..1), or None when unreadable.

    Pillow does the parsing where it is installed, so the full CSS range works
    here exactly as it does for the painter; a plain hex value needs nothing,
    which keeps this module importable on a machine with no Pillow.
    """
    value = (color or "").strip()
    if value.startswith("#") and len(value) in (7, 9):
        try:
            int(value[1:], 16)
        except ValueError:
            pass
        else:
            alpha = int(value[7:9], 16) / 255 if len(value) == 9 else 1.0
            return value[:7].lower(), alpha
    try:
        from PIL import ImageColor

        rgba = ImageColor.getrgb(value)
    except Exception:
        return None
    alpha = rgba[3] / 255 if len(rgba) == 4 else 1.0
    return f"#{rgba[0]:02x}{rgba[1]:02x}{rgba[2]:02x}", alpha


def _fill(color: str) -> tuple[str, float]:
    """A box or text colour; unreadable is transparent, as the painter has it."""
    return _colour(color) or ("#000000", 0.0)


def _hex(color: str) -> str:
    """A stroke or path fill as `#rrggbb`; unreadable -> white, as before."""
    parsed = _colour(color)
    return parsed[0] if parsed else "#ffffff"
