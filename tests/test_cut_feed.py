from __future__ import annotations


def test_cut_full(client, connector, auth_headers):
    res = client.post("/cut", json={"partial": False}, headers=auth_headers)
    assert res.status_code == 200
    out = bytes(connector.buffer)
    assert b"\x1d\x56" in out  # GS V


def test_cut_partial(client, connector, auth_headers):
    res = client.post("/cut", json={"partial": True}, headers=auth_headers)
    assert res.status_code == 200
    assert b"\x1d\x56" in bytes(connector.buffer)


def test_feed_writes_newlines(client, connector, auth_headers):
    res = client.post("/feed", json={"lines": 5}, headers=auth_headers)
    assert res.status_code == 200
    assert bytes(connector.buffer).count(b"\n") >= 5


def test_feed_rejects_negative(client, auth_headers):
    res = client.post("/feed", json={"lines": -1}, headers=auth_headers)
    assert res.status_code == 422
