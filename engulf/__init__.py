"""Engulf weather: climatology, forecasts and readings for one burn, built from the Hill Country toolkit."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def event() -> dict:
    return json.loads((ROOT / "config" / "event.json").read_text())
