# printd

> **An HTTP API for ESC/POS thermal receipt printers.** Send a PNG, get a receipt.

[![CI](https://github.com/HansF/printd/actions/workflows/ci.yml/badge.svg)](https://github.com/HansF/printd/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)

`printd` turns any ESC/POS thermal printer (USB, network, or serial) into a clean REST endpoint that any frontend, app, or device on your network can hit. It's a single-process FastAPI service with OpenAPI docs, bearer-token auth, Docker support, and an image pipeline tuned for the quirks of cheap thermal heads.

```bash
curl -X POST http://printd.local:8080/print \
     -H "Authorization: Bearer $PRINTD_API_KEY" \
     -F image=@receipt.png
```

Paper comes out. That's the entire mental model.

---

## Why

Driving a thermal printer from app code is annoying:
- USB device permissions, CUPS, vendor drivers, kernel modules.
- Print-head density quirks that drop raster rows on dense images.
- Dance of feed-then-cut to land cuts at sane positions.
- Different transports for the same protocol (USB / TCP:9100 / serial).

`printd` does this once, properly, behind a stable HTTP API:
- **One process, one Docker container, one config file.**
- **Generic ESC/POS** via [python-escpos](https://python-escpos.readthedocs.io) — any USB / network / serial printer it speaks to, `printd` speaks to.
- **Image pipeline** that handles fast-path pass-through ≤576 px wide, LANCZOS downscale otherwise, 1-bit threshold, and bottom-pad against dropped rows.
- **Single-shot `GS v 0` raster** — full bitmap in one ESC/POS command, no chunking, no slipped cuts.
- **Bearer-token auth**, CORS for browser frontends, `/healthz`, `/status`.
- **OpenAPI 3** at `/docs` (Swagger UI) and `/openapi.json` — generate clients in any language for free.
- **Tested** with a `DummyConnector` so CI never needs hardware.

---

## Quickstart

### Docker

```bash
git clone https://github.com/HansF/printd
cd printd
cp .env.example .env
# edit .env — set PRINTD_API_KEY and PRINTD_DEVICE
docker compose up -d
```

### Local Python

```bash
pip install printd          # or: pip install -e ".[dev]" from a clone
cp .env.example .env
python -m printd            # serves on :8080
```

Test:

```bash
curl http://localhost:8080/healthz
# {"ok":true,"printer":"online","kind":"usb","target":"/dev/usb/lp0"}

curl -X POST http://localhost:8080/print \
     -H "Authorization: Bearer $PRINTD_API_KEY" \
     -F image=@examples/tickets/sample.png
```

Open http://localhost:8080/docs for the interactive Swagger UI.

---

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET`  | `/healthz`        | no  | Liveness probe — fine for k8s / cron / monitoring. |
| `GET`  | `/status`         | yes | Connector kind, target, last error, image-pipeline settings. |
| `POST` | `/print`          | yes | JSON body `{ "image": "<data:url or base64>", "cut": true }` |
| `POST` | `/print/upload`   | yes | Multipart `image` upload (form fields: `cut`, `feed`, `partial_cut`). |
| `POST` | `/print/raw`      | yes | Escape hatch — write base64-encoded raw ESC/POS bytes. |
| `POST` | `/cut`            | yes | `{ "partial": false }` |
| `POST` | `/feed`           | yes | `{ "lines": 3 }` |
| `GET`  | `/docs`           | no  | Swagger UI. |
| `GET`  | `/openapi.json`   | no  | OpenAPI 3 schema. |

Auth is a static bearer token: `Authorization: Bearer <PRINTD_API_KEY>`. If `PRINTD_API_KEY` is unset, `printd` runs in dev mode (no auth, prints a loud warning at startup).

Full reference: [`docs/api.md`](docs/api.md).

---

## Configuration

All configuration is via env vars (or a `.env` file in the working directory). See [`.env.example`](.env.example).

| Var | Default | What it does |
|---|---|---|
| `PRINTD_API_KEY` | _empty_ | Bearer token. Empty = dev mode, no auth. |
| `PRINTD_HOST` | `0.0.0.0` | Bind host. |
| `PRINTD_PORT` | `8080` | Bind port. |
| `PRINTD_PRINTER_KIND` | `usb` | `usb` / `network` / `serial` / `dummy`. |
| `PRINTD_DEVICE` | `/dev/usb/lp0` | Device node, `host:port`, or serial port. |
| `PRINTD_PRINT_WIDTH` | `576` | Print-head dot count. Most 80 mm printers are 576. |
| `PRINTD_BOTTOM_PAD_ROWS` | `24` | White rows appended to every image (drop-row mitigation). |
| `PRINTD_FEED_BEFORE_CUT` | `4` | Newlines printed before cut so the blade clears the content. |
| `PRINTD_CORS_ORIGINS` | `*` | Comma-separated origins. |
| `PRINTD_MAX_IMAGE_BYTES` | `8388608` | Reject larger payloads with HTTP 413. |

---

## Client examples

### TypeScript

```ts
export async function printImage(pngDataUrl: string, opts: { cut?: boolean } = {}) {
  const res = await fetch(`${PRINTD_URL}/print`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${PRINTD_API_KEY}`,
    },
    body: JSON.stringify({ image: pngDataUrl, cut: opts.cut ?? true }),
  });
  if (!res.ok) throw new Error(`printd ${res.status}: ${await res.text()}`);
  return res.json();
}
```

Drop-in helper: [`examples/client.ts`](examples/client.ts).

### Python

```python
import base64, requests

with open("ticket.png", "rb") as f:
    img = "data:image/png;base64," + base64.b64encode(f.read()).decode()

requests.post(
    f"{PRINTD_URL}/print",
    json={"image": img, "cut": True},
    headers={"Authorization": f"Bearer {PRINTD_API_KEY}"},
).raise_for_status()
```

Drop-in helper: [`examples/client.py`](examples/client.py).

### curl

See [`examples/curl.sh`](examples/curl.sh).

### Live demo

[`examples/demo.py`](examples/demo.py) is a 5-step scripted tour that hits every endpoint and prints a real receipt — header → endpoint cheatsheet → server-rendered QR (via raw ESC/POS) → feed → cut.

```bash
PRINTD_URL=http://localhost:8080 \
PRINTD_API_KEY=changeme \
python examples/demo.py
```

Receipts are generated on the fly with Pillow, so a fresh checkout is enough — no bundled assets, no cropping if your paper width differs.

---

## Supported printers

`printd` speaks generic ESC/POS, which means anything python-escpos talks to. Verified in the field: **Xprinter XP-80T** (USB). See [`docs/printers.md`](docs/printers.md) for known device-specific quirks (cutter alarms, DIP switches, density commands, dropped-row mitigation).

If you've successfully driven another model through `printd`, please open a PR adding it to that file.

---

## Deployment

- **systemd unit** for bare-metal Linux.
- **Docker / Compose** with USB device passthrough.
- **Raspberry Pi** notes (udev rules so the `lp` group owns `/dev/usb/lp0`).
- **Reverse proxy** (Caddy / nginx) for TLS + bearer auth at the edge.

All in [`docs/deployment.md`](docs/deployment.md).

---

## CLI

`printd-cli` ships alongside the server for direct hardware operations (no HTTP). It uses the same env-driven `Settings`, so the same `.env` works for both:

```bash
printd-cli test                 # print a formatting test page
printd-cli image receipt.png    # print an image file
printd-cli density dark         # set print density
printd-cli beep off             # disable Xprinter cutter-alarm (see docs/printers.md)
printd-cli cut --partial
```

---

## Development

```bash
git clone https://github.com/HansF/printd
cd printd
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check .
```

The test suite uses a `DummyConnector` that captures every ESC/POS byte in memory — no hardware required to run `pytest`. CI runs lint + tests on Python 3.11 and 3.12.

---

## Used by

- [exchange-terminal](https://github.com/HansF/exchange-terminal) — a small suite of paper-receipt apps (offerings/demands tickets, oracle fortunes, focus-session timers, AI caricatures, image stencils) that drive printd over its HTTP API.

If you're building on top of printd, open a PR adding your project here.

---

## Contributing

Bug reports, printer compatibility notes, and PRs welcome. Please:
- Add tests for new behaviour (the dummy connector makes this trivial).
- Run `ruff format` and `ruff check` before opening a PR.
- For new printer support, include a one-paragraph entry in `docs/printers.md`.

---

## License

[MIT](LICENSE).
