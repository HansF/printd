# API reference

The live, executable reference is at `/docs` (Swagger UI) and `/openapi.json` once the server is running. This page documents the routes for offline reading.

All authenticated endpoints require `Authorization: Bearer <PRINTD_API_KEY>`. If `PRINTD_API_KEY` is unset, the server runs in dev mode and accepts unauthenticated requests (with a warning at startup).

---

## `GET /healthz`

Liveness probe. Always returns 200 if the process is up.

```json
{
  "ok": true,
  "printer": "online",
  "kind": "usb",
  "target": "/dev/usb/lp0"
}
```

## `GET /status`

Returns the active connector, the last error (if any), and the image-pipeline configuration.

```json
{
  "ok": true,
  "kind": "usb",
  "target": "/dev/usb/lp0",
  "last_error": null,
  "print_width": 576,
  "bottom_pad_rows": 24,
  "feed_before_cut": 4
}
```

## `POST /print`

Print an image supplied as JSON. Image may be a `data:image/...;base64,…` URL or a bare base64 string. PNG and JPEG are both accepted.

Request:
```json
{
  "image": "data:image/png;base64,iVBORw0KGgo…",
  "cut": true,
  "feed": 4,
  "partial_cut": false
}
```

| Field | Default | Notes |
|---|---|---|
| `image` | required | Data URL or bare base64. |
| `cut` | `true` | Send a paper cut after the image. |
| `feed` | `null` → server default | Newlines fed before the cut. |
| `partial_cut` | `false` | `GS V 1` instead of `GS V 0`. |

Response:
```json
{ "ok": true, "width": 570, "height": 800 }
```

The returned `width`/`height` reflect the bitmap actually sent to the printer (after any resize and bottom-padding).

## `POST /print/upload`

Multipart equivalent of `/print` for binary efficiency.

```bash
curl -X POST http://localhost:8080/print/upload \
     -H "Authorization: Bearer $PRINTD_API_KEY" \
     -F image=@receipt.png \
     -F cut=true
```

Form fields: `image` (file, required), `cut` (bool), `feed` (int), `partial_cut` (bool).

## `POST /print/raw`

Escape hatch for callers that want to drive the printer with hand-crafted ESC/POS. Body:
```json
{ "bytes_b64": "<base64-encoded raw bytes>" }
```

Response:
```json
{ "ok": true, "bytes_written": 17 }
```

Useful for vendor-specific NVRAM commands or barcode/QR features not (yet) exposed by `printd`. **There is no payload validation** — you can put the printer in any state you can encode. Use with care.

## `POST /cut`

```json
{ "partial": false }
```

Feeds a few lines and cuts. Use `partial: true` for partial cut (`GS V 1`).

## `POST /feed`

```json
{ "lines": 3 }
```

Advances paper by N lines (each line is roughly 5 mm at default line height on most 80 mm printers).
