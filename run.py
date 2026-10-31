#!/usr/bin/env python3
"""Engulf weather, end to end.

    python3 run.py climatology   # once: 30 years of the festival week (about 2 minutes, 31 requests)
    python3 run.py today         # forecasts + drought + river, then the reading in readings/
    python3 run.py reading       # rewrite the reading from the data already saved
"""
import sys
from engulf import climatology, forecast, ground, reading


def main(cmd: str) -> None:
    if cmd == "climatology":
        climatology.build()
    elif cmd == "today":
        forecast.build(); ground.build(); reading.build()
    elif cmd == "reading":
        reading.build()
    else:
        raise SystemExit(__doc__)
    if cmd != "climatology":
        print((reading.ROOT / "readings" / "latest.md").read_text())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
