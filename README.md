# drm_composer

Stateless scene-to-screen-command compiler. Parses a declarative HTML-like
scene and emits commands for [`drm_screen`](https://github.com/carstenbund/drm_screen) — most elements as
**RGBA** bitmaps, a layer of `<path>` elements as a scene document that stays
primitives all the way to the panel.

Python package: `drm_composer`.

```
drm_composer  →  drm_screen  →  drm-display
 scene → cmds     layers →         frame →
 bitmaps          composited       DRM/KMS
 or scenes        frame            pixels
```

- Parses `screen` / `layer` / `box` / `text` / `img` / `raw-buffer`
- Resolves layout (x, y, w, h, z, visibility)
- Rasterizes to RGBA bitmaps
- Compiles `<path>` / `<animate>` layers to a scene document instead
- Translates layers into `drm_screen` commands

It holds **no** screen state, does **not** blend the final frame (that's
`drm_screen`'s compositor), and does **not** know DRM/KMS (that's `drm_display`).

## Documentation

- **[SYNTAX.md](https://github.com/carstenbund/drm_composer/blob/main/SYNTAX.md)** — complete screen-HTML reference: every element,
  every attribute, accepted value formats, and behaviour. **Start here to write
  scenes.**
- [outline.md](https://github.com/carstenbund/drm_composer/blob/main/outline.md) — the design and where this package sits in the stack.

## Install

```bash
pip install drm-composer    # also pulls in drm-screen and drm-display
```

Installing `drm-composer` brings the whole rendering chain with it — one install
gets you HTML → screen.

### `<path>` layers need a scene renderer

Bitmap layers work with what the line above installs.  A layer of `<path>`
elements does not: it travels as a `PlaceScene` command, and `drm_screen`'s
default numpy compositor carries pixels only — it raises `UnsupportedCommand`
rather than guessing.  Drawing those layers needs a renderer that declares the
`scene` capability:

```bash
pip install drm-screen-lvgl
```

The gain is why it is worth the extra install: the paths are drawn at the
panel's own resolution and animated against a clock, so nothing is rasterised
and a moving scene costs a document once rather than pixels every frame.

## Part of the drm_stack

Each package installs and runs on its own:

| Package | Role |
|---|---|
| **`drm-composer`** | screen-HTML → layer commands · *this package* |
| [`drm-screen`](https://github.com/carstenbund/drm_screen) | layers → composited frame |
| [`drm-display`](https://github.com/carstenbund/drm_display) | frame → DRM/KMS pixels |
| [`drm-screen-lvgl`](https://github.com/carstenbund/drm_screen_lvgl) | optional renderer — draws `<path>` layers as primitives |

Full stack, bootstrap, and integration demo:
[`drm_stack`](https://github.com/carstenbund/drm_stack).

## Changes

```
0.2.2   Documentation and packaging.  Relative links 404 on PyPI, where this
        README is the project description -- including the one pointing at
        SYNTAX.md, which the text calls the place to start.  The Author header
        was empty, a {name, email} author mapping to Author-email alone.  The
        summary said RGBA bitmaps only, predating vector scene layers.
0.2.1   Documentation.  The README described this package as a rasteriser and
        never named the renderer <path> layers need, so the documented syntax
        failed with UnsupportedCommand against a default install.  Record
        release history.
0.2.0   <path> and <animate>.  A layer of paths compiles to a scene document
        and travels as one PlaceScene command, staying primitives all the way
        to the panel instead of being rasterised.  Needs drm-screen >= 0.2 for
        the command, and a renderer with the `scene` capability to draw it --
        the numpy compositor raises UnsupportedCommand rather than guess.
        Also the first release to carry the interactive <button> element,
        written well before this but never uploaded.
0.1.4   never released
0.1.3   never released
0.1.1   same source as 0.1.0; the version string is the only difference
0.1.0   initial -- screen-HTML to drm_screen command batches
```

## License

**GPL-3.0-or-later** (see [LICENSE](https://github.com/carstenbund/drm_composer/blob/main/LICENSE)). Use it freely under the GPL. For
proprietary/closed use that cannot comply with the GPL, a separate commercial
license is available — contact Carsten Bund <carstenbund@gmail.com>.

Dependencies are permissive (BSD/MIT) and installed separately; their notices
are in [THIRD_PARTY_LICENSES.md](https://github.com/carstenbund/drm_composer/blob/main/THIRD_PARTY_LICENSES.md).
