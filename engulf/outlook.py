"""NOAA's longer-range outlooks at the site: the odds of a warmer or colder, wetter or drier stretch than normal.

The Climate Prediction Center publishes, every day, an outlook for 8 to 14 days ahead, and every
Friday one for weeks 3 and 4. They don't forecast a day; they give, for a whole period, the chance
that it averages above, near or below normal. Areas with no lean are "equal chances". The maps come
as KML polygons (ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/); this reads which polygon the site
falls in. Where polygons nest, the innermost (highest-chance) one that holds the site wins.
"""
from __future__ import annotations
import io, json, re, zipfile
from datetime import datetime
from xml.etree import ElementTree as ET
from . import ROOT, event
from .fetch import Refused, get

BASE = "https://ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/"
PRODUCTS = {"8-14 day": ("814temp_latest.kmz", "814prcp_latest.kmz")}
NS = {"k": "http://www.opengis.net/kml/2.2"}


def inside(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    """Ray casting: is the point inside the closed ring of (lon, lat)?"""
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def ring(text: str) -> list[tuple[float, float]]:
    return [(float(a), float(b)) for a, b, *_ in (c.split(",") for c in text.split())]


def read_kml(kml: bytes, lon: float, lat: float) -> dict:
    """The period the map covers, and the category and chance at the point ('equal chances' if no polygon holds it)."""
    root = ET.fromstring(kml)
    name = root.find(".//k:Document/k:name", NS).text
    valid = re.search(r"Valid:\s*([\d/]+)\s*-\s*([\d/]+)", name)
    best = None
    for pm in root.iter(f"{{{NS['k']}}}Placemark"):
        label = pm.find("k:name", NS).text or ""
        m = re.match(r"([\d.]+)% Chance of (Above|Below|Near) Normal (Temperature|Precipitation)", label.replace("&#37;", "%"))
        if not m:
            continue
        for poly in pm.iter(f"{{{NS['k']}}}Polygon"):
            outer = poly.find("k:outerBoundaryIs//k:coordinates", NS)
            holes = [ring(h.text) for h in poly.findall("k:innerBoundaryIs//k:coordinates", NS)]
            if outer is not None and inside(lon, lat, ring(outer.text)) and not any(inside(lon, lat, h) for h in holes):
                chance = float(m.group(1))
                if best is None or chance > best["chance"]:
                    best = {"lean": m.group(2).lower(), "chance": chance}
    period = [datetime.strptime(v, "%m/%d/%Y").date().isoformat() for v in valid.groups()] if valid else None
    return {"period": period, "issued": name, **(best or {"lean": "equal chances", "chance": None})}


def build() -> dict:
    ev = event()
    lon, lat = ev["site"]["lon"], ev["site"]["lat"]
    out = {"meaning": "NOAA Climate Prediction Center outlooks at the site: the lean for a whole period, not a day's forecast.",
           "source": "NOAA Climate Prediction Center", "outlooks": {}}
    for label, (temp, prcp) in PRODUCTS.items():
        row = {}
        for kind, f in (("temperature", temp), ("rain", prcp)):
            try:
                kmz = get(BASE + f, "cpc", f.replace(".kmz", ""), keep="new",   # ~290 KB a map, kept once per new issue
                          accept="application/vnd.google-earth.kmz")
                with zipfile.ZipFile(io.BytesIO(kmz)) as z:
                    row[kind] = read_kml(z.read(next(n for n in z.namelist() if n.endswith(".kml"))), lon, lat)
            except (Refused, KeyError, StopIteration, ET.ParseError, zipfile.BadZipFile) as e:
                row[kind] = {"error": str(e)[:200]}
        out["outlooks"][label] = row
    (ROOT / "data" / "outlook-latest.json").write_text(json.dumps(out, indent=1) + "\n")
    return out
