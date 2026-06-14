# drm_composer

Stateless scene-to-screen-command compiler. Parses a declarative HTML-like
scene, rasterizes elements to **RGBA** bitmaps, and emits commands for
[`drm_screen`](../drm_screen).

Python package: `drm_composer`.

```
drm_composer  →  drm_screen  →  drm-display
 scene → cmds     layers →         frame →
 + RGBA bitmaps   composited       DRM/KMS
                  frame            pixels
```

- Parses `screen` / `layer` / `box` / `text` / `img` / `raw-buffer`
- Resolves layout (x, y, w, h, z, visibility)
- Rasterizes to RGBA bitmaps
- Translates layers into `drm_screen` commands

It holds **no** screen state, does **not** blend the final frame (that's
`drm_screen`'s compositor), and does **not** know DRM/KMS (that's `drm_display`).

## Documentation

- **[SYNTAX.md](SYNTAX.md)** — complete screen-HTML reference: every element,
  every attribute, accepted value formats, and behaviour. **Start here to write
  scenes.**
- [outline.md](outline.md) — the design and where this package sits in the stack.

## Install

```bash
pip install drm-composer    # also pulls in drm-screen and drm-display
```

Installing `drm-composer` brings the whole rendering chain with it — one install
gets you HTML → screen.

## Part of the drm_stack

Each package installs and runs on its own:

| Package | Role |
|---|---|
| **`drm-composer`** | screen-HTML → layer commands · *this package* |
| [`drm-screen`](https://github.com/carstenbund/drm_screen) | layers → composited frame |
| [`drm-display`](https://github.com/carstenbund/drm_display) | frame → DRM/KMS pixels |

Full stack, bootstrap, and integration demo:
[`drm_stack`](https://github.com/carstenbund/drm_stack).

## License

**GPL-3.0-or-later** (see [LICENSE](LICENSE)). Use it freely under the GPL. For
proprietary/closed use that cannot comply with the GPL, a separate commercial
license is available — contact Carsten Bund <carstenbund@gmail.com>.

Dependencies are permissive (BSD/MIT) and installed separately; their notices
are in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
