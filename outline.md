The compositor module is the high-level translator.

It should not own the screen and should not write to DRM/KMS.

drm-compositor
  input:  HTML subset / scene description / templates
  output: commands + bitmaps for drm-screen-service

Correct stack:

Application
  ↓
drm-compositor
  ↓
drm-screen-service
  ↓
drm-display

Responsibilities of drm-compositor:

1. Parse simple HTML-like scene markup
2. Resolve layout: x, y, width, height, z, visibility
3. Render visual elements into RGBA bitmaps
4. Translate layers into screen-service commands
5. Send those commands to drm-screen-service

It may understand:

<screen width="800" height="480">
  <layer id="status" z="10" visible="true">
    <box x="20" y="20" w="300" h="80" color="#000000cc" />
    <text x="40" y="65" size="24" color="#ffffff">Ready</text>
    <img src="logo.png" x="240" y="20" w="64" h="64" />
  </layer>
</screen>

It produces lower-level operations:

screen.create_layer("status", width=800, height=480, z=10)
screen.clear_layer("status")
screen.put_bitmap("status", bitmap, x=20, y=20)
screen.show_layer("status")
screen.render()

Suggested module outline:

drm_compositor/
  __init__.py
  scene.py          # Scene, LayerNode, BoxNode, TextNode, ImageNode
  parser.py         # HTML subset parser
  layout.py         # resolves positions and sizes
  painter.py        # renders boxes/text/images to RGBA bitmaps
  commands.py       # screen-service command model
  target.py         # client adapter for drm-screen-service
  compositor.py     # orchestration

Main class:

class Compositor:
    def __init__(self, target):
        self.target = target
    def render_html(self, html: str):
        scene = parse_scene(html)
        layout = resolve_layout(scene)
        commands = paint_to_commands(layout)
        self.target.apply(commands)

Important boundary:

drm-compositor does not manage persistent layer buffers.
drm-screen-service does.
drm-compositor does not blend the final screen.
drm-screen-service does.
drm-compositor does not know DRM/KMS.
drm-display does.

So the compositor is really a scene-to-screen-command compiler.


make HTML the declarative scene format, but keep rendering as bitmap composition.

Think:

simple HTML/CSS -> rasterized layer buffer -> compositor -> drm-display

Not:

browser owns the screen

Recommended MVP subset:

<screen width="800" height="480">
  <layer id="background" z="0">
    <img src="background.png" x="0" y="0" />
  </layer>
  <layer id="status" z="10" visible="true">
    <box x="20" y="20" w="300" h="80" color="#000000cc">
      <text x="16" y="24" size="22" color="#ffffff">
        System ready
      </text>
    </box>
  </layer>
</screen>

Start with a constrained “screen HTML”:

screen
layer
img
text
box
raw-buffer

Possible first renderer interface:

class HtmlSceneRenderer:
    def render_scene(self, html: str) -> list[Layer]:
        ...

Then the service can accept:

POST /scene
Content-Type: text/html

Example:

<screen>
  <layer id="main" z="0">
    <img src="/assets/logo.png" x="200" y="50" />
  </layer>
  <layer id="overlay" z="20" visible="false">
    <box x="0" y="400" w="800" h="80" color="#000000aa" />
    <text x="24" y="430" size="28" color="white">
      Loading...
    </text>
  </layer>
</screen>

The compositor still only sees:

Layer(
    id="overlay",
    z=20,
    visible=False,
    buffer=np.ndarray(...)
)

So the architecture becomes:

HTML parser
  parses screen/layer/img/text/box
Layer renderer
  draws each layer into RGBA NumPy buffers
Compositor
  combines visible layers
drm-display
  writes final frame

This avoids deviation because the screen description becomes the stable contract from day one.

Good first package layout:

drm_screen_service/
  compositor.py
  layer.py
  html_scene.py
  drawing.py
  server.py
  backend_drm.py

The key rule:

HTML describes state.
Compositor renders state.
drm-display outputs pixels.
