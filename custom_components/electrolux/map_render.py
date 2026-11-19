"""Render PUREi9 interactive maps (zone polygons) as an SVG image.

The Electrolux API no longer returns the cleaned-area map (``mapData``) for the
PUREi9, but ``/interactiveMap`` still returns every map with its zones as
polygons in metres. This draws those zones: clean zones filled and labelled,
avoid zones hatched in red. One panel per map, titled with the map name.
"""

from __future__ import annotations

import math
from typing import Any
from xml.sax.saxutils import escape

PANEL_WIDTH = 800
MARGIN = 24
TITLE_HEIGHT = 36
MAX_PANEL_HEIGHT = 900

# Muted fills for clean zones, cycled per zone
_ZONE_FILLS = ("#8fb3a6", "#c9a66b", "#9aa8c7", "#c78f8f", "#a7c08a", "#b59ac7", "#c7b98a", "#8ab8c0")
_AVOID_STROKE = "#c0392b"


def _points(zone: dict[str, Any], rotation_rad: float) -> list[tuple[float, float]]:
    """Return the zone vertices rotated by the map rotation, with y pointing up."""
    pts: list[tuple[float, float]] = []
    for vertex in zone.get("vertices") or []:
        if not isinstance(vertex, dict):
            continue
        try:
            x, y = float(vertex["x"]), float(vertex["y"])
        except KeyError, TypeError, ValueError:
            continue
        if rotation_rad:
            c, s = math.cos(rotation_rad), math.sin(rotation_rad)
            x, y = x * c - y * s, x * s + y * c
        pts.append((x, y))
    return pts


def _centroid(pts: list[tuple[float, float]]) -> tuple[float, float]:
    """Area centroid of a polygon (vertex mean as a fallback for degenerate ones)."""
    area = cx = cy = 0.0
    for i, (x1, y1) in enumerate(pts):
        x2, y2 = pts[(i + 1) % len(pts)]
        cross = x1 * y2 - x2 * y1
        area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(area) < 1e-9:
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    return cx / (3 * area), cy / (3 * area)


def _map_zones(api_map: dict[str, Any]) -> list[tuple[dict[str, Any], list[tuple[float, float]]]]:
    rotation = api_map.get("rotation") or 0
    try:
        rotation_rad = math.radians(float(rotation))
    except TypeError, ValueError:
        rotation_rad = 0.0
    zones = []
    for zone in api_map.get("zones") or []:
        if isinstance(zone, dict) and len(pts := _points(zone, rotation_rad)) >= 3:
            zones.append((zone, pts))
    return zones


def render_maps_svg(maps: list[dict[str, Any]]) -> str | None:
    """Return an SVG with one panel per map that has zones, or None when none has."""
    panels: list[tuple[str, list[tuple[dict[str, Any], list[tuple[float, float]]]]]] = []
    for api_map in maps:
        if isinstance(api_map, dict) and (zones := _map_zones(api_map)):
            panels.append((str(api_map.get("name") or ""), zones))
    if not panels:
        return None

    body: list[str] = []
    offset_y = 0.0
    inner_width = PANEL_WIDTH - 2 * MARGIN
    fill_index = 0
    for title, zones in panels:
        xs = [x for _, pts in zones for x, _ in pts]
        ys = [y for _, pts in zones for _, y in pts]
        span_x = max(max(xs) - min(xs), 0.1)
        span_y = max(max(ys) - min(ys), 0.1)
        scale = min(inner_width / span_x, (MAX_PANEL_HEIGHT - 2 * MARGIN) / span_y)
        draw_height = span_y * scale
        top = offset_y + (TITLE_HEIGHT if title else 0) + MARGIN
        left = MARGIN + (inner_width - span_x * scale) / 2
        min_x, max_y = min(xs), max(ys)

        def to_svg(
            pt: tuple[float, float], left: float = left, top: float = top, scale: float = scale
        ) -> tuple[float, float]:
            return left + (pt[0] - min_x) * scale, top + (max_y - pt[1]) * scale

        if title:
            body.append(f'<text x="{MARGIN}" y="{offset_y + 26:.1f}" class="title">{escape(title)}</text>')
        labels: list[str] = []
        # Clean zones first, avoid zones on top so the restriction stays visible
        for zone, pts in sorted(zones, key=lambda item: item[0].get("zoneType") == "avoid"):
            path = " ".join(f"{x:.1f},{y:.1f}" for x, y in map(to_svg, pts))
            name = escape(str(zone.get("name") or ""))
            if zone.get("zoneType") == "avoid":
                body.append(f'<polygon points="{path}" class="avoid"><title>{name}</title></polygon>')
            else:
                fill = _ZONE_FILLS[fill_index % len(_ZONE_FILLS)]
                fill_index += 1
                body.append(
                    f'<polygon points="{path}" class="clean" fill="{fill}"><title>{name}</title></polygon>'
                )
                if name:
                    cx, cy = to_svg(_centroid(pts))
                    labels.append(f'<text x="{cx:.1f}" y="{cy:.1f}" class="label">{name}</text>')
        body.extend(labels)
        offset_y = top + draw_height + MARGIN

    height = math.ceil(offset_y)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL_WIDTH}" height="{height}" '
        f'viewBox="0 0 {PANEL_WIDTH} {height}">'
        "<defs>"
        '<pattern id="avoid-hatch" width="8" height="8" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)">'
        f'<line x1="0" y1="0" x2="0" y2="8" stroke="{_AVOID_STROKE}" stroke-width="3"/>'
        "</pattern>"
        "<style>"
        ".clean{stroke:#4a4a4a;stroke-width:2;fill-opacity:.75}"
        f".avoid{{fill:url(#avoid-hatch);fill-opacity:.6;stroke:{_AVOID_STROKE};stroke-width:2;"
        "stroke-dasharray:6 4}"
        ".label{font:600 15px sans-serif;fill:#1f1f1f;text-anchor:middle;dominant-baseline:middle;"
        "paint-order:stroke;stroke:#ffffff;stroke-width:3}"
        ".title{font:700 18px sans-serif;fill:#1f1f1f}"
        "</style>"
        "</defs>"
        f'<rect width="{PANEL_WIDTH}" height="{height}" fill="#f7f5f0"/>' + "".join(body) + "</svg>"
    )
