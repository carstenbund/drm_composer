#!/usr/bin/env python3
"""End-to-end demo: screen-HTML -> drm_composer -> drm_screen -> frame.

Headless (forces the dummy backend), so it never touches a real display.
Run with the venv that has drm_display/drm_screen/drm_composer installed.
"""

import os
import time

from PIL import Image

from drm_screen import DrmDisplayBackend, ScreenService, InProcessTarget
from drm_composer import Compositor

W, H = 800, 480
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html_frame.png")

SCENE = """
<screen width="800" height="480">
  <layer id="background" z="0">
    <box x="0" y="0" w="800" h="480" color="#141e3c" />
  </layer>
  <layer id="status" z="10" visible="true">
    <box x="40" y="40" w="380" h="96" color="#000000aa" />
    <text x="60" y="74" size="24" color="#ffffff">System ready</text>
  </layer>
  <layer id="hint" z="20">
    <text x="60" y="430" size="18" color="#7fd0ff">drm_composer -&gt; drm_screen</text>
  </layer>
</screen>
"""


def main():
    # drm_screen service (headless, safe).
    backend = DrmDisplayBackend(device="dummy", width=W, height=H)
    service = ScreenService(backend, fps=30)
    service.start()

    # drm_composer compiles HTML and submits to the service via the target.
    compositor = Compositor(InProcessTarget(service))
    batch = compositor.render_html(SCENE)
    print(f"compiled {len(batch)} commands from screen-HTML")
    for cmd in batch:
        print("  ", type(cmd).__name__,
              getattr(cmd, "name", getattr(cmd, "id", "")))

    time.sleep(0.15)   # let the render thread composite

    frame = backend.snapshot_rgba()
    assert frame is not None and frame.shape == (H, W, 4)
    # background present, status box darkened the bg under it
    assert tuple(frame[300, 600][:3]) == (20, 30, 60), "background wrong"
    assert frame[100, 200][2] < 60, "status box did not blend over background"

    Image.fromarray(frame, "RGBA").save(OUT)
    print(f"saved -> {OUT}")
    service.stop()


if __name__ == "__main__":
    main()
