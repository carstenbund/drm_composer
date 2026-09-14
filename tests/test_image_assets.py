"""<img> as a scene asset: converted to LVGL's binary image format, referred to
by a readable name, and carried with the size and CRC a player checks."""

import struct
import zlib

import pytest
from PIL import Image

from drm_composer import parse_scene
from drm_composer.lvgl_image import CF_RGB565, CF_RGB565A8, MAGIC, to_lvgl_bin
from drm_composer.scene_ir import emit_screen_ir


def _screen(body: str) -> str:
    return f'<screen width="320" height="480"><layer id="a">{body}</layer></screen>'


@pytest.fixture
def pictures(tmp_path):
    Image.new("RGBA", (40, 20), (255, 0, 0, 255)).save(tmp_path / "logo.png")
    half = Image.new("RGBA", (10, 10), (0, 0, 255, 255))
    half.putpixel((0, 0), (0, 0, 255, 0))
    half.save(tmp_path / "badge.png")
    return tmp_path


def test_an_opaque_picture_becomes_rgb565_named_after_its_file(pictures):
    assets = {}
    doc = emit_screen_ir(parse_scene(_screen('<img src="logo.png" x="5" y="6" />')),
                         assets=assets, base_dir=pictures)
    image = doc["layers"][0]["objects"][0]
    data = assets["logo.bin"]

    assert image == {"type": "image", "id": "img0", "x": 5, "y": 6, "w": 40, "h": 20,
                     "src": "logo", "size": len(data), "crc32": zlib.crc32(data)}
    assert struct.unpack_from("<BBHHHHH", data) == (MAGIC, CF_RGB565, 0, 40, 20, 80, 0)
    assert len(data) == 12 + 40 * 20 * 2
    assert struct.unpack_from("<H", data, 12)[0] == 0xF800   # pure red in RGB565


def test_transparency_adds_an_alpha_plane():
    picture = Image.new("RGBA", (3, 2), (0, 255, 0, 128))
    data = to_lvgl_bin(picture)

    assert data[1] == CF_RGB565A8
    assert len(data) == 12 + 3 * 2 * 2 + 3 * 2
    assert data[-1] == 128


def test_a_picture_is_fitted_to_its_box_on_the_host(pictures):
    assets = {}
    doc = emit_screen_ir(
        parse_scene(_screen('<img src="logo.png" w="80" h="80" fit="contain" />')),
        assets=assets, base_dir=pictures)

    image = doc["layers"][0]["objects"][0]
    assert (image["w"], image["h"]) == (80, 80)
    assert assets["logo.bin"][1] == CF_RGB565A8, "a letterbox is transparent"


def test_one_picture_at_two_sizes_gets_two_names(pictures):
    assets = {}
    doc = emit_screen_ir(parse_scene(_screen(
        '<img src="logo.png" /><img src="logo.png" />'
        '<img src="logo.png" w="20" h="10" />')), assets=assets, base_dir=pictures)

    names = [o["src"] for o in doc["layers"][0]["objects"]]
    assert names == ["logo", "logo", "logo-20x10"]
    assert sorted(assets) == ["logo-20x10.bin", "logo.bin"]


def test_a_picture_needs_somewhere_to_go():
    with pytest.raises(ValueError, match="assets"):
        emit_screen_ir(parse_scene(_screen('<img src="logo.png" />')))


def test_a_missing_picture_fails_the_build_not_the_panel(tmp_path):
    with pytest.raises(ValueError, match="cannot read"):
        emit_screen_ir(parse_scene(_screen('<img src="nope.png" />')),
                       assets={}, base_dir=tmp_path)
