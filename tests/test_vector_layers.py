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
from drm_composer.scene import AnimateNode, BoxNode, PathNode
from drm_composer.scene_ir import emit_scene_ir, layer_is_vector

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


def test_a_layer_holds_pixels_or_primitives_but_not_both():
    scene = parse_scene(HTML)
    scene.layers[1].children.append(BoxNode(x=0, y=0, w=10, h=10))

    with pytest.raises(ValueError, match="mixes"):
        paint_scene(scene)
