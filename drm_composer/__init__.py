"""drm_composer — stateless scene-to-screen-command compiler.

Parses a constrained screen-HTML subset, rasterizes elements to RGBA bitmaps,
and emits drm_screen command batches.  Holds no screen state, never blends the
final frame, never touches DRM/KMS.

A layer of `<path>` elements is the exception to "rasterizes": it compiles to a
scene document (`PlaceScene`) and stays primitives all the way to the panel, so
`<animate>` can put a stroke half way through being drawn.
"""

from .scene import (
    Scene, LayerNode, BoxNode, TextNode, ImageNode, ButtonNode, PathNode, AnimateNode,
)
from .parser import parse_scene
from .scene_ir import emit_scene_ir, emit_scene_json, layer_is_vector
from .painter import paint_scene
from .compositor import Compositor
from .actions import Action, parse_action, Dispatcher

from importlib.metadata import version, PackageNotFoundError
try:
    __version__ = version("drm-composer")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "Scene", "LayerNode", "BoxNode", "TextNode", "ImageNode", "ButtonNode",
    "PathNode", "AnimateNode",
    "parse_scene", "paint_scene", "Compositor",
    "emit_scene_ir", "emit_scene_json", "layer_is_vector",
    "Action", "parse_action", "Dispatcher", "__version__",
]
