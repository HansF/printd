from __future__ import annotations

import base64


def test_print_json_writes_to_dummy(client, connector, png_data_url, auth_headers):
    res = client.post(
        "/print",
        json={"image": png_data_url(320, 100), "cut": True},
        headers=auth_headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["width"] == 320
    # 100 rows + 24 bottom pad.
    assert body["height"] == 124

    # Dummy buffer should now contain raster + cut bytes.
    out = bytes(connector.buffer)
    assert b"\x1d\x76\x30" in out  # GS v 0 raster command
    assert b"\x1d\x56" in out  # GS V cut


def test_print_no_cut_skips_cut_byte(client, connector, png_data_url, auth_headers):
    res = client.post(
        "/print",
        json={"image": png_data_url(200, 60), "cut": False},
        headers=auth_headers,
    )
    assert res.status_code == 200
    out = bytes(connector.buffer)
    assert b"\x1d\x76\x30" in out
    assert b"\x1d\x56" not in out  # no cut requested


def test_print_resizes_when_too_wide(client, png_data_url, auth_headers):
    res = client.post(
        "/print",
        json={"image": png_data_url(1280, 100), "cut": False},
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["width"] == 576
    # 100 * (576/1280) = 45, no padding because cut=False still pads, settings = 24
    assert body["height"] == 45 + 24


def test_print_rejects_invalid_image(client, auth_headers):
    res = client.post(
        "/print",
        json={"image": "data:image/png;base64,bm90LWFuLWltYWdl"},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_print_upload_multipart(client, connector, png_bytes, auth_headers):
    raw = png_bytes(300, 80)
    res = client.post(
        "/print/upload",
        files={"image": ("ticket.png", raw, "image/png")},
        data={"cut": "false"},
        headers=auth_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["width"] == 300


def test_print_raw_writes_bytes(client, connector, auth_headers):
    payload = base64.b64encode(b"\x1b\x40hello").decode()
    res = client.post(
        "/print/raw",
        json={"bytes_b64": payload},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["bytes_written"] == 7
    assert b"hello" in bytes(connector.buffer)


def test_print_too_large(client, auth_headers, settings):
    # Settings caps at 8 MB; build a >8 MB base64 blob.
    huge = base64.b64encode(b"\x00" * (settings.max_image_bytes + 1)).decode()
    res = client.post(
        "/print",
        json={"image": huge},
        headers=auth_headers,
    )
    assert res.status_code == 413
