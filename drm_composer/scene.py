"""Scene model — the parsed, in-memory form of a screen-HTML document.

A Scene is a screen with ordered layers; each layer holds visual nodes
(box / text / img).  This is pure data: the parser builds it, the painter
consumes it.  Nothing here rasterizes or talks to drm_screen.
"""

from dataclasses import dataclass, field


@dataclass
class BoxNode:
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    color: str = "#000000ff"   # #rrggbb or #rrggbbaa


@dataclass
class TextNode:
    text: str
    x: int = 0
    y: int = 0
    size: int = 16
    color: str = "#ffffffff"


@dataclass
class ImageNode:
    src: str
    x: int = 0
    y: int = 0
    w: int | None = None       # None -> native size
    h: int | None = None
    fit: str = "fill"          # fill (stretch) | contain (letterbox) | cover (crop)
    fullscreen: str = ""       # "" (off) | "toggle" (tap -> full:<src>) | "always"


@dataclass
class ButtonNode:
    """An interactive region: compiled to its own interactive layer (hit_id=id)."""
    id: str
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    color: str = "#3060a0ff"        # button fill
    text_color: str = "#ffffffff"
    size: int = 28
    label: str = ""                  # character data inside <button>...</button>


@dataclass
class AnimateNode:
    """One phase of one property, over time.

    The same element SVG/SMIL uses, and the same meaning: the property moves
    from `frm` to `to` between `start` and `start + duration`, along `easing`.
    Held by the node it animates, or given an explicit `target`.
    """
    target: str = ""
    property: str = "progress"
    frm: float = 0.0
    to: float = 1.0
    start: int = 0
    duration: int = 1000
    easing: str = "linear"


@dataclass
class PathNode:
    """A stroked path — content that is still a description when it reaches the
    panel, so it can be drawn *part* way.

    `progress` is the fraction of the path's ordered length that has been drawn:
    animate it and the line draws itself. A layer holding paths compiles to a
    scene rather than to a bitmap; see `scene_ir.py`.
    """
    id: str
    d: str
    stroke: str = "#ffffffff"
    stroke_width: float = 2.0
    fill: str = ""
    progress: float = 1.0
    opacity: float = 1.0
    animations: list = field(default_factory=list)   # AnimateNode


@dataclass
class LayerNode:
    id: str
    z: int = 0
    visible: bool = True
    children: list = field(default_factory=list)   # Box/Text/Img/Button/Path nodes


@dataclass
class Scene:
    width: int
    height: int
    layers: list = field(default_factory=list)      # LayerNode in document order
