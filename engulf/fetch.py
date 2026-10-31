"""Fetch with the raw bytes kept: every response is written, gzipped, before anything parses it.

The rule comes from hill-country-hydro ("raw before interpretation"): a capture under
data/captures/<source>/ and one row in data/manifest.jsonl with the URL, the time, the HTTP status,
the byte count and a sha256 of the bytes as received. A provider refusal is recorded too, then raised.
"""
from __future__ import annotations
import gzip, hashlib, json, time, urllib.error, urllib.request
from datetime import datetime, timezone
from . import ROOT

UA = "engulf-weather/0.1 (github.com/saulbanov/engulf-weather)"
CAPTURES = ROOT / "data" / "captures"
MANIFEST = ROOT / "data" / "manifest.jsonl"


class Refused(Exception):
    """The provider answered with an error; the body is in the message and the manifest."""


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def seen(sha: str) -> bool:
    """Whether bytes with this hash are already kept as a capture."""
    if not MANIFEST.exists():
        return False
    for line in MANIFEST.read_text().splitlines():
        r = json.loads(line)
        if r.get("sha256") == sha and r.get("capture") and (ROOT / r["capture"]).exists():
            return True
    return False


def get(url: str, source: str, name: str, keep: bool | str = True, tries: int = 3, accept: str = "application/json") -> bytes:
    """GET `url`; keep the bytes as data/captures/<source>/<stamp>-<name>.gz. keep=False records only the hash;
    keep="new" keeps the bytes unless an identical capture is already kept (for large files that change daily)."""
    status, body, err = None, b"", ""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=120) as r:
                status, body = r.status, r.read()
            break
        except urllib.error.HTTPError as e:
            status, body, err = e.code, e.read() or b"", str(e)
            if e.code in (400, 404, 429):
                break
        except (urllib.error.URLError, TimeoutError) as e:
            err = str(e)
        if i < tries - 1:
            time.sleep(2 ** (i + 1))
    row = {"retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source": source,
           "url": url, "status": status, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    if keep == "new" and body and seen(row["sha256"]):
        row["capture_of_same_bytes"] = True
    elif keep and body:
        path = CAPTURES / source / f"{stamp()}-{name}.gz"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(body, mtime=0))
        row["capture"] = str(path.relative_to(ROOT))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a") as f:
        f.write(json.dumps(row) + "\n")
    if status != 200:
        raise Refused(f"{source}: HTTP {status} {err} {body[:300].decode('utf-8', 'replace')}")
    return body


def get_json(url: str, source: str, name: str, **kw) -> dict:
    return json.loads(get(url, source, name, **kw))
