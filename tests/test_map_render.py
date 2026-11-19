"""Tests for the PUREi9 interactive map SVG renderer."""

from __future__ import annotations

import xml.dom.minidom
from typing import Any

from custom_components.electrolux.map_render import render_maps_svg


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[dict[str, float]]:
    return [{"x": x0, "y": y0}, {"x": x1, "y": y0}, {"x": x1, "y": y1}, {"x": x0, "y": y1}]


GROUND: dict[str, Any] = {
    "id": "map-ground",
    "name": "Ground & floor",
    "rotation": 0.0,
    "zones": [
        {"id": "kitchen", "name": "Kitchen", "zoneType": "clean", "vertices": _rect(0, 0, 4, 3)},
        {"id": "hall", "name": "Hall <1>", "zoneType": "clean", "vertices": _rect(4, 0, 6, 3)},
        {"id": "rug", "name": "Rug", "zoneType": "avoid", "vertices": _rect(1, 1, 2, 2)},
    ],
}


def _parse(svg: str | None) -> xml.dom.minidom.Document:
    assert svg is not None
    return xml.dom.minidom.parseString(svg)


def test_renders_valid_svg_with_zones_labels_and_title():
    doc = _parse(render_maps_svg([GROUND]))
    polygons = doc.getElementsByTagName("polygon")
    assert [p.getAttribute("class") for p in polygons] == ["clean", "clean", "avoid"]  # avoid drawn last
    texts = [t.firstChild.data for t in doc.getElementsByTagName("text")]
    # names are escaped and still readable after parsing
    assert texts == ["Ground & floor", "Kitchen", "Hall <1>"]


def test_y_axis_points_up():
    doc = _parse(render_maps_svg([GROUND]))
    kitchen = doc.getElementsByTagName("polygon")[0].getAttribute("points").split()
    ys = {round(float(p.split(",")[1])) for p in kitchen}
    # y=0 (bottom of the map) must be drawn below y=3
    first = kitchen[0].split(",")  # vertex (0, 0)
    fourth = kitchen[3].split(",")  # vertex (0, 3)
    assert float(first[1]) > float(fourth[1])
    assert len(ys) == 2


def test_one_panel_per_map_and_empty_maps_skipped():
    second = {
        "id": "map-basement",
        "name": "Basement",
        "zones": [{"id": "laundry", "name": "Laundry", "zoneType": "clean", "vertices": _rect(0, 0, 2, 2)}],
    }
    empty = {"id": "map-empty", "name": None, "zones": None}
    doc = _parse(render_maps_svg([empty, GROUND, second]))
    texts = doc.getElementsByTagName("text")
    titles = [t.firstChild.data for t in texts if t.getAttribute("class") == "title"]
    assert titles == ["Ground & floor", "Basement"]


def test_rotation_is_applied():
    rotated = dict(GROUND, rotation=90.0)
    assert render_maps_svg([rotated]) != render_maps_svg([GROUND])


def test_returns_none_without_drawable_zones():
    assert render_maps_svg([]) is None
    assert render_maps_svg([{"id": "m", "zones": None}]) is None
    bad = {
        "id": "m",
        "rotation": "x",
        "zones": [
            {"id": "z", "zoneType": "clean", "vertices": [{"x": 0, "y": 0}, {"x": "a", "y": 1}, "junk"]},
            "junk",
        ],
    }
    assert render_maps_svg([bad, "junk"]) is None  # type: ignore[list-item]


def test_unnamed_map_has_no_title_and_unnamed_zone_no_label():
    unnamed = {"id": "m", "zones": [{"id": "z", "zoneType": "clean", "vertices": _rect(0, 0, 1, 1)}]}
    doc = _parse(render_maps_svg([unnamed]))
    assert doc.getElementsByTagName("text") == []
    assert len(doc.getElementsByTagName("polygon")) == 1


def test_degenerate_polygon_uses_vertex_mean_for_label():
    line = {
        "id": "m",
        "zones": [
            {
                "id": "z",
                "name": "Line",
                "zoneType": "clean",
                "vertices": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0}],
            }
        ],
    }
    doc = _parse(render_maps_svg([line]))
    assert doc.getElementsByTagName("text")[0].firstChild.data == "Line"
