#!/usr/bin/env python3
"""Engulf weather, end to end.

    python3 run.py climatology   # once: 30 years of the festival week (about 2 minutes, 31 requests)
    python3 run.py today         # forecasts + NOAA outlook + drought + river + last 30 days, then the reading in readings/ and the page in site/
    python3 run.py reading       # rewrite the reading and the page from the data already saved
"""
import sys
from engulf import climatology, forecast, ground, outlook, reading, site


def main(cmd: str) -> None:
    if cmd == "climatology":
        climatology.build()
    elif cmd == "today":
        forecast.build(); ground.build(); outlook.build(); reading.build(); site.build()
    elif cmd == "reading":
        reading.build(); site.build()
    else:
        raise SystemExit(__doc__)
    if cmd != "climatology":
        print((reading.ROOT / "readings" / "latest.md").read_text())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
