"""screen-HTML with a stroke that draws itself, all the way to the panel.

    drm_composer  →  drm_screen  →  drm_screen_lvgl  →  DRM/KMS
     HTML → batch     layers        primitives          pixels

The `<box>` in this document is compiled to a bitmap, as it always was. The
`<path>` is not: it stays a description, and `progress` is evaluated against the
clock every frame, so the line is drawn rather than appearing.

    python example/vector_screen.py            # on the panel
    python example/vector_screen.py memory     # headless, prints ink per second
"""

import sys
import time

from drm_composer import Compositor
from drm_screen import InProcessTarget, ScreenService

HTML = """
<screen width="800" height="480">
  <layer id="bg" z="0">
    <box x="0" y="0" w="800" h="480" color="#101014" />
  </layer>
  <layer id="ink" z="20">
    <path id="rule" d="M 60 240 L 740 240" stroke="#e8e8f0" stroke-width="4" progress="0">
      <animate property="progress" from="0" to="1" start="0" duration="3000" />
    </path>
  </layer>
</screen>
"""


def main() -> int:
    headless = len(sys.argv) > 1 and sys.argv[1] == "memory"
    options = dict(width=800, height=480, display="memory") if headless else {}

    service = ScreenService(renderer="lvgl", renderer_options=options, fps=60)
    Compositor(InProcessTarget(service)).render_html(HTML)

    started = time.monotonic()
    while True:
        elapsed = (time.monotonic() - started) * 1000.0
        if elapsed > 3500:
            break
        service.render_once(elapsed)

    if headless:
        frame = service.renderer.snapshot_rgba()
        lit = int((frame[..., :3].max(axis=2) > 80).sum())
        print(f"ink after the stroke finished: {lit} px")
    service.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
