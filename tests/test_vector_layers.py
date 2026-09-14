"""A layer of primitives: parsed, and compiled to a scene rather than a bitmap.

The distinction the tests are drawing: a `<box>` becomes pixels here, because a
box is finished the moment it is drawn. A `<path>` does not, because `progress`
means "how much of this stroke exists yet", and pixels cannot hold a question
like that -- only a description can, evaluated by the renderer against a clock.
"""

import json

import pytest

from drm_composer import parse_scene
from drm_composer.painter import paint_scene
from drm_composer.scene import AnimateNode, ButtonNode, ImageNode, PathNode
from drm_composer.scene_ir import emit_scene_ir, emit_screen_ir, layer_is_vector

HTML = """
<screen width="800" height="480">
  <layer id="bg" z="0">
    <box x="0" y="0" w="800" h="480" color="#101014" />
  </layer>
  <layer id="ink" z="20">
    <path id="line" d="M 20 300 L 780 300" stroke="#e8e8f0" stroke-width="3"
          progress="0">
      <animate property="progress" from="0" to="1" start="0" duration="3000" />
    </path>
    <path id="under" d="M 20 340 L 780 340" stroke="#8fe0c2" progress="0">
      <animate property="progress" from="0" to="1" start="1500" duration="2000"
               easing="ease-out" />
    </path>
  </layer>
</screen>
"""


def test_a_path_is_parsed_with_its_animation():
    scene = parse_scene(HTML)
    ink = scene.layers[1]
    line, under = ink.children

    assert isinstance(line, PathNode) and line.d == "M 20 300 L 780 300"
    assert line.stroke_width == 3.0 and line.progress == 0.0
    assert [a.property for a in line.animations] == ["progress"]
    assert under.animations[0].start == 1500
    assert under.animations[0].easing == "ease-out"


def test_an_animation_can_name_what_it_moves():
    scene = parse_scene("""
    <screen width="100" height="100">
      <layer id="ink">
        <path id="a" d="M 0 0 L 100 100" />
        <animate target="a" property="progress" from="0" to="1" duration="500" />
      </layer>
    </screen>
    """)
    path = scene.layers[0].children[0]

    assert isinstance(path.animations[0], AnimateNode)
    assert path.animations[0].target == "a"


def test_a_loose_animation_must_say_what_it_animates():
    with pytest.raises(ValueError, match="target"):
        parse_scene("""
        <screen width="100" height="100">
          <layer id="ink"><animate property="progress" to="1" /></layer>
        </screen>
        """)


def test_which_layers_are_primitives():
    scene = parse_scene(HTML)

    assert not layer_is_vector(scene.layers[0])
    assert layer_is_vector(scene.layers[1])


def test_the_scene_document_says_what_moves_and_for_how_long():
    scene = parse_scene(HTML)
    document = emit_scene_ir(scene, scene.layers[1])

    assert document["width"], document["height"] == (800, 480)
    assert [o["id"] for o in document["layers"][0]["objects"]] == ["line", "under"]
    assert document["layers"][0]["objects"][0]["stroke"] == "#e8e8f0"
    # the scene lasts until the last thing stops moving: 1500 + 2000
    assert document["duration"] == 3500
    assert {a["target"] for a in document["animations"]} == {"line", "under"}


def test_a_colour_by_name_still_reaches_the_renderer_as_hex():
    scene = parse_scene("""
    <screen width="10" height="10">
      <layer id="ink"><path id="p" d="M 0 0 L 10 10" stroke="rebeccapurple" /></layer>
    </screen>
    """)
    document = emit_scene_ir(scene, scene.layers[0])

    assert document["layers"][0]["objects"][0]["stroke"] == "#663399"


def test_a_vector_layer_is_placed_as_a_scene_and_a_box_as_pixels():
    batch = paint_scene(parse_scene(HTML))
    kinds = [type(c).__name__ for c in batch]

    assert kinds == ["CreateLayer", "PlaceRawBuffer", "CreateLayer", "PlaceScene"]

    placed = batch[3]
    document = json.loads(placed.scene)
    assert placed.name == "ink"
    assert document["layers"][0]["objects"][0]["d"] == "M 20 300 L 780 300"


def test_boxes_and_text_share_a_layer_with_paths_as_primitives():
    scene = parse_scene("""
    <screen width="320" height="480">
      <layer id="panel" z="5">
        <box x="10" y="20" w="300" h="60" color="#3060a080" />
        <text x="24" y="40" size="24" color="white">Nozzle 210</text>
        <path id="rule" d="M 10 100 L 310 100" />
      </layer>
    </screen>
    """)
    batch = paint_scene(scene)

    assert [type(c).__name__ for c in batch] == ["CreateLayer", "PlaceScene"]
    rect, text, path = json.loads(batch[1].scene)["layers"][0]["objects"]
    assert rect == {"type": "rect", "id": "box0", "x": 10, "y": 20, "w": 300,
                    "h": 60, "fill": "#3060a0", "opacity": pytest.approx(128 / 255, abs=1e-4)}
    assert text == {"type": "text", "id": "text1", "content": "Nozzle 210",
                    "font_id": "montserrat-24", "x": 24, "y": 40, "color": "#ffffff"}
    assert path["type"] == "path"


def test_a_button_has_no_scene_form():
    scene = parse_scene(HTML)
    scene.layers[1].children.append(ButtonNode(id="ok"))

    with pytest.raises(ValueError, match="mixes.*<button>"):
        paint_scene(scene)


def test_a_picture_in_a_layer_scene_needs_a_whole_screen_document():
    scene = parse_scene(HTML)
    scene.layers[1].children.append(ImageNode(src="logo.png"))

    with pytest.raises(ValueError, match="<img>.*whole-screen"):
        paint_scene(scene)


def test_the_whole_screen_compiles_to_one_document():
    """What the ESP32 loads: one scene, every layer in it, ordered by z there."""
    scene = parse_scene(HTML)
    scene.layers[0].visible = False
    document = emit_screen_ir(scene)

    assert [(layer["id"], layer["z"]) for layer in document["layers"]] == [("bg", 0), ("ink", 20)]
    background = document["layers"][0]["objects"][0]
    assert background["type"] == "rect" and background["fill"] == "#101014"
    assert background["visible"] is False
    assert document["duration"] == 3500


def test_an_unreadable_box_colour_is_transparent_as_in_the_painter():
    scene = parse_scene("""
    <screen width="10" height="10">
      <layer id="a"><box w="10" h="10" color="no-such-colour" /></layer>
    </screen>
    """)
    assert emit_screen_ir(scene)["layers"][0]["objects"][0]["opacity"] == 0.0


def test_object_ids_must_be_unique_across_the_screen():
    scene = parse_scene("""
    <screen width="10" height="10">
      <layer id="a"><path d="M 0 0 L 10 10" /></layer>
      <layer id="b"><path d="M 0 10 L 10 0" /></layer>
    </screen>
    """)
    with pytest.raises(ValueError, match="path0.*twice"):
        emit_screen_ir(scene)
