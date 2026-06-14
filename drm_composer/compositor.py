"""Compositor — the scene-to-screen-command compiler (orchestration).

Stateless: given the same HTML it emits the same command batch.  It compiles
(parse -> paint) and hands the batch to a target adapter that delivers it to the
drm_screen service.  It does NOT blend pixels (drm_screen's Composer does) and
does NOT know DRM (drm-display does).

The name 'Compositor' here means "compiles the scene", not "composites pixels".
"""

from .parser import parse_scene
from .painter import paint_scene


class Compositor:
    def __init__(self, target):
        self.target = target          # anything with .submit(commands), e.g.
                                      # drm_screen.InProcessTarget / SocketTarget

    def compile(self, html: str) -> list:
        """Parse + paint -> command batch (no side effects)."""
        return paint_scene(parse_scene(html))

    def render_html(self, html: str) -> list:
        """Compile and submit the batch to drm_screen. Non-blocking handoff."""
        batch = self.compile(html)
        self.target.submit(batch)
        return batch
