"""drm_composer — stateless scene-to-screen-command compiler.

Parses a constrained screen-HTML subset, rasterizes elements to RGBA bitmaps,
and emits drm_screen command batches.  Holds no screen state, never blends the
final frame, never touches DRM/KMS.
"""

from .scene import Scene, LayerNode, BoxNode, TextNode, ImageNode
from .parser import parse_scene
from .painter import paint_scene
from .compositor import Compositor

__all__ = [
    "Scene", "LayerNode", "BoxNode", "TextNode", "ImageNode",
    "parse_scene", "paint_scene", "Compositor",
]
