"""Scene IR — a layer of primitives, as a document the panel can evaluate.

Everything else in this package ends in pixels: `painter.py` rasterises a layer
into an RGBA bitmap and sends it as `PlaceRawBuffer`. That is right for a box,
a label or a photograph, and it is wrong for a stroke that is supposed to draw
itself, because a bitmap has no way to be half a line.

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

The document is the contract between this compiler and whatever draws it, and
it is deliberately not this package's invention: it is `drm_scene_ir`, the same
format the ESP32 player loads. Version it there, not here.
"""

from __future__ import annotations

import json

from .scene import AnimateNode, PathNode

__all__ = ["SCENE_IR_VERSION", "emit_scene_ir", "layer_is_vector"]

SCENE_IR_VERSION = 1


def layer_is_vector(layer) -> bool:
    """True when this layer's content is primitives rather than pixels."""
    return any(isinstance(node, PathNode) for node in layer.children)


def emit_scene_ir(scene, layer, name: str | None = None) -> dict:
    """One layer of paths -> a scene document.

    The layer keeps the whole screen's coordinate system: a scene carries its
    own design size and the renderer fits it to the panel, so the same document
    is correct on a 450x250 panel and on a 1920x1080 one.
    """
    objects = []
    animations = []

    for node in layer.children:
        if not isinstance(node, PathNode):
            raise ValueError(
                f"layer {layer.id!r} mixes primitives with pixels: a layer holds "
                f"one or the other, because only one of them can be a scene"
            )
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
        objects.append(obj)

        for animation in node.animations:
            animations.append(_animation(animation))

    return {
        "version": SCENE_IR_VERSION,
        "name": name or layer.id,
        "width": scene.width,
        "height": scene.height,
        "fit": "contain",
        "duration": _duration(animations),
        "layers": [{"id": layer.id, "z": layer.z, "objects": objects}],
        "animations": animations,
    }


def emit_scene_json(scene, layer, name: str | None = None) -> bytes:
    """The document as bytes, ready for `PlaceScene`."""
    return json.dumps(emit_scene_ir(scene, layer, name), separators=(",", ":")).encode()


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


def _hex(color: str) -> str:
    """Colours reach the renderer as `#rrggbb`.

    Pillow does the parsing where it is installed, so the full CSS range works
    here exactly as it does for a box; a plain hex value needs nothing, which
    keeps this module importable on a machine with no Pillow.
    """
    value = (color or "").strip()
    if value.startswith("#") and len(value) in (7, 9):
        return value[:7]
    try:
        from PIL import ImageColor

        r, g, b = ImageColor.getrgb(value)[:3]
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return "#ffffff"
