"""A live tour of every printd endpoint.

What this prints, in order, on real paper:
  1. "Welcome to printd" header   → POST /print (JSON, base64)
  2. Endpoint cheat-sheet receipt → POST /print/upload (multipart)
  3. A QR code generated server-side via raw ESC/POS bytes
                                  → POST /print/raw
  4. A short paper feed           → POST /feed
  5. Final cut                    → POST /cut

Health and status are queried up front so a misconfigured printd surfaces
before any paper is wasted.

Usage:
    PRINTD_URL=http://localhost:8080 \\
    PRINTD_API_KEY=changeme \\
    python examples/demo.py
"""

from __future__ import annotations

import base64
import io
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Allow `python examples/demo.py` from a fresh checkout without an install step.
sys.path.insert(0, str(Path(__file__).parent))

from client import Printd  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

WIDTH = 570  # client-side render target — printd passes images <=576 px straight through


# ── pretty CLI logging ────────────────────────────────────────────────────────


def step(n: int, label: str) -> None:
    print(f"\n\033[1;36m[{n}]\033[0m {label}")


def ok(msg: str) -> None:
    print(f"   \033[32m✓\033[0m {msg}")


# ── image generators ──────────────────────────────────────────────────────────


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Best-effort font load. Falls back to PIL's bitmap default."""
    candidates = [
        "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Menlo.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_header() -> bytes:
    img = Image.new("RGB", (WIDTH, 360), "white")
    d = ImageDraw.Draw(img)
    title = _font(56)
    body = _font(22)
    small = _font(18)

    d.text((WIDTH // 2, 50), "printd", anchor="ma", font=title, fill="black")
    d.text(
        (WIDTH // 2, 130),
        "An HTTP API for ESC/POS",
        anchor="ma",
        font=body,
        fill="black",
    )
    d.text((WIDTH // 2, 165), "thermal receipt printers", anchor="ma", font=body, fill="black")
    d.line([(40, 220), (WIDTH - 40, 220)], fill="black", width=1)
    d.text(
        (WIDTH // 2, 250),
        f"DEMO · {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        anchor="ma",
        font=small,
        fill="black",
    )
    d.text(
        (WIDTH // 2, 290),
        "github.com/HansF/printd",
        anchor="ma",
        font=small,
        fill="black",
    )
    return _to_png(img)


def render_cheatsheet() -> bytes:
    rows = [
        ("GET", "/healthz", "liveness"),
        ("GET", "/status", "config + last error"),
        ("POST", "/print", "JSON image"),
        ("POST", "/print/upload", "multipart image"),
        ("POST", "/print/raw", "raw ESC/POS"),
        ("POST", "/cut", "feed and cut"),
        ("POST", "/feed", "advance N lines"),
    ]
    img = Image.new("RGB", (WIDTH, 60 + len(rows) * 38 + 60), "white")
    d = ImageDraw.Draw(img)
    title = _font(28)
    mono = _font(20)

    d.text((WIDTH // 2, 18), "ENDPOINTS", anchor="ma", font=title, fill="black")
    d.line([(40, 60), (WIDTH - 40, 60)], fill="black", width=1)

    y = 78
    for verb, path, note in rows:
        d.text((40, y), verb, font=mono, fill="black")
        d.text((110, y), path, font=mono, fill="black")
        d.text((WIDTH - 40, y), note, anchor="ra", font=mono, fill="black")
        y += 38

    d.line([(40, y + 6), (WIDTH - 40, y + 6)], fill="black", width=1)
    d.text(
        (WIDTH // 2, y + 16), "Bearer auth · OpenAPI · CORS", anchor="ma", font=mono, fill="black"
    )
    return _to_png(img)


def _to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── ESC/POS for /print/raw ────────────────────────────────────────────────────


def qr_bytes(payload: str) -> bytes:
    """Hand-rolled ESC/POS that prints a QR code, then feeds + cuts.

    Uses the GS ( k command set (the standard ESC/POS QR family). Module
    size 8 dots, error correction L. Most modern thermal printers (XP-80T,
    Epson TM, Star) implement this.
    """
    data = payload.encode("utf-8")
    cmds = bytearray()

    # Center align
    cmds += b"\x1b\x61\x01"

    # Model 2
    cmds += b"\x1d\x28\x6b\x04\x00\x31\x41\x32\x00"
    # Module size (1..16) — 8 is a comfortable scan target on 80 mm paper.
    cmds += b"\x1d\x28\x6b\x03\x00\x31\x43\x08"
    # Error correction L (48), M (49), Q (50), H (51).
    cmds += b"\x1d\x28\x6b\x03\x00\x31\x45\x48"
    # Store data
    n = len(data) + 3
    cmds += b"\x1d\x28\x6b" + bytes([n & 0xFF, (n >> 8) & 0xFF]) + b"\x31\x50\x30" + data
    # Print
    cmds += b"\x1d\x28\x6b\x03\x00\x31\x51\x30"

    # A label under the QR
    cmds += b"\n"
    cmds += b"github.com/HansF/printd\n"
    cmds += b"\x1b\x61\x00"  # left-align reset
    return bytes(cmds)


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    base = os.environ.get("PRINTD_URL", "http://localhost:8080")
    key = os.environ.get("PRINTD_API_KEY", "")
    c = Printd(base, api_key=key or None)

    step(0, f"Connecting to printd at {base}")
    h = c.health()
    ok(f"healthy: kind={h['kind']} target={h['target']}")
    s = c.status()
    ok(f"status: width={s['print_width']} pad={s['bottom_pad_rows']} feed={s['feed_before_cut']}")

    step(1, "POST /print — JSON header image")
    r = c.print_bytes(render_header(), cut=False)
    ok(f"sent {r['width']}x{r['height']} bitmap (no cut yet, more coming)")
    time.sleep(0.5)

    step(2, "POST /print/upload — multipart cheatsheet")
    # client.py doesn't bind /print/upload yet — call it via the underlying http client.
    files = {"image": ("cheatsheet.png", render_cheatsheet(), "image/png")}
    r2 = c._client.post(
        f"{base.rstrip('/')}/print/upload",
        headers={"Authorization": f"Bearer {key}"} if key else {},
        files=files,
        data={"cut": "false"},
    )
    r2.raise_for_status()
    body = r2.json()
    ok(f"sent {body['width']}x{body['height']} bitmap via multipart")
    time.sleep(0.5)

    step(3, "POST /print/raw — server-printed QR via ESC/POS")
    payload = qr_bytes("https://github.com/HansF/printd")
    raw = c._post("print/raw", json={"bytes_b64": base64.b64encode(payload).decode()})
    ok(f"wrote {raw['bytes_written']} raw bytes — printer rasterised the QR")
    time.sleep(0.5)

    step(4, "POST /feed — clear the cutter blade")
    c.feed(4)
    ok("fed 4 lines (~20 mm)")

    step(5, "POST /cut — finish the receipt")
    c.cut()
    ok("cut")

    print("\n\033[1;32mDone.\033[0m Tear off the receipt — that was every endpoint.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
