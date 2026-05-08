from __future__ import annotations


def test_status_reports_settings(client, auth_headers):
    res = client.get("/status", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["kind"] == "dummy"
    assert body["print_width"] == 576
    assert body["bottom_pad_rows"] == 24
    assert body["last_error"] is None


def test_status_surfaces_print_errors(client, app, auth_headers, monkeypatch):
    from printd import escpos_session

    def boom(*_a, **_kw):
        raise RuntimeError("printer offline")

    monkeypatch.setattr(escpos_session, "print_image", boom)
    res = client.post(
        "/print",
        json={
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQMAAAAl21bKAAAAA1BMVEX///+nxBvIAAAACklEQVQI12NgAAAAAgAB4iG8MwAAAABJRU5ErkJggg=="
        },
        headers=auth_headers,
    )
    assert res.status_code == 500
    s = client.get("/status", headers=auth_headers).json()
    assert s["last_error"] is not None
    assert "RuntimeError" in s["last_error"]
