# drm-composer — outline

`drm_composer` is the **stateless high-level translator**. It compiles a
declarative scene (an HTML-like subset) into the command + bitmap calls that
`drm_screen` understands.

It is, in one line: a **scene-to-screen-command compiler**.

## What it does NOT do

These boundaries are the whole point of the split — keep them sharp:

- It does **not** own or persist layer buffers. → `drm_screen` does.
- It does **not** blend the final screen. → `drm_screen`'s `Composer` does.
- It does **not** know DRM/KMS. → `drm-display` does.

`drm_composer` holds no screen state between calls. Given the same scene it
emits the same commands.

## Place in the stack

```
Application
   ↓
drm_composer     scene markup → commands + RGBA bitmaps   (stateless, this repo)
   ↓
drm_screen       layers → composited frame                (stateful)
   ↓
drm-display      frame → DRM/KMS pixels                    (hardware)
```

## Responsibilities

1. **Parse** a constrained "screen HTML" subset.
2. **Resolve layout** — x, y, width, height, z, visibility.
3. **Rasterize** visual elements (box, text, img) into **RGBA** bitmaps.
4. **Translate** the resulting layers into `drm_screen` command calls.
5. **Send** those commands to `drm_screen` via a target adapter.

## Color convention

Everything `drm_composer` produces is **RGBA** `uint8`. It never converts to
BGRA — the single channel-order conversion happens far downstream, in
`drm_screen`'s backend adapter, right before `drm-display`. See drm-screen's
outline.

## Screen HTML — the input format

A constrained, declarative subset. **HTML describes state**, the compositor
renders state, drm-display outputs pixels.

MVP element set: `screen`, `layer`, `box`, `text`, `img`, `raw-buffer`.

```html
<screen width="800" height="480">
  <layer id="background" z="0">
    <img src="background.png" x="0" y="0" />
  </layer>
  <layer id="status" z="10" visible="true">
    <box x="20" y="20" w="300" h="80" color="#000000cc">
      <text x="16" y="24" size="22" color="#ffffff">System ready</text>
    </box>
  </layer>
</screen>
```

## What it compiles to

The same scene above produces `drm_screen` command calls (the stable contract
defined in drm-screen's outline):

```python
screen.create_layer("status", width=800, height=480, z=10)
screen.clear_layer("status")
screen.place_raw_buffer("status", w, h, status_bitmap_rgba)   # box+text rastered
screen.show_layer("status")
screen.render()
```

## Package layout

```
drm_composer/
  __init__.py
  scene.py          # Scene, LayerNode, BoxNode, TextNode, ImageNode
  parser.py         # screen-HTML subset → Scene tree
  layout.py         # resolve positions and sizes
  painter.py        # render boxes/text/images → RGBA bitmaps
  commands.py       # drm_screen command model (mirrors the contract)
  target.py         # client adapter that delivers commands to drm_screen
  compositor.py     # orchestration (compile only — NOT pixel blending)
```

Note: `compositor.py` here means "compiles the scene"; it does not composite
pixels. Pixel composition is `drm_screen`'s `Composer`. (Naming kept distinct
on purpose — this module never blends a frame.)

## Sync utility, not a service

`drm_composer` has no loop, no thread, and no state. It is a pure function
`html → (commands + RGBA bitmaps)`, invoked synchronously by whoever holds the
HTML. The only service in the stack is `drm_screen`; the single async boundary
is its `submit()` (a socket in production). The composer just produces a command
batch and hands it across that boundary — which returns immediately.

If rasterization is heavy enough to stall the caller (large image decode, slow
text layout), run the composer call in a worker thread *at the call site*. Don't
bake threading into the composer — keep it a plain, testable function.

## Main class

```python
class Compositor:
    def __init__(self, target):
        self.target = target            # adapter onto drm_screen's submit()

    def render_html(self, html: str):
        scene    = parse_scene(html)
        layout   = resolve_layout(scene)
        commands = paint_to_commands(layout)   # rasterize to RGBA, build batch
        self.target.submit(commands)           # non-blocking handoff to drm_screen
```

## Target adapter

`target` abstracts *how* the command batch reaches the `drm_screen` service. The
composer code is identical regardless of transport.

```python
class SocketTarget:        # production default — drm_screen is a separate daemon
    def submit(self, commands):
        self._send(serialize(commands))   # unix socket / HTTP POST; returns on ack

class InProcessTarget:     # debug only — service runs in the same process
    def __init__(self, service):
        self.service = service
    def submit(self, commands):
        self.service.submit(commands)     # direct enqueue, no socket
```

Commands must be **serializable** (records, with RGBA bitmaps as raw bytes) so
the same batch survives the socket hop. `InProcessTarget` is purely a
development convenience — same `submit()` contract, no transport.

## Pipeline

```
screen-HTML
   ↓  parser.py        → Scene tree (screen/layer/box/text/img)
   ↓  layout.py        → resolved geometry
   ↓  painter.py       → RGBA layer bitmaps + command list
   ↓  target.py        → drm_screen command API
drm_screen owns the buffers, composites, and pushes to drm-display.
```

Making screen-HTML the stable scene format from day one keeps the boundary
clean: the application speaks declarative HTML, and the lower layers never need
to change when the scene does.

## Service entry point (later)

`drm_screen`'s server can accept a scene directly and hand it to a
`drm_composer.Compositor` whose `target` is the local command API:

```
POST /scene
Content-Type: text/html

<screen>…</screen>
```

HTML rasterization (full CSS/browser engine) can come later. The contract above
does not change when it does: **HTML → RGBA bitmap → layer**, never "browser owns
the screen".
