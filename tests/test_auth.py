from __future__ import annotations

from fastapi.testclient import TestClient

from printd.app import create_app
from printd.connectors import DummyConnector


def test_status_requires_bearer(client):
    res = client.get("/status")
    assert res.status_code == 401


def test_status_rejects_wrong_scheme(client):
    res = client.get("/status", headers={"Authorization": "Basic abcdef"})
    assert res.status_code == 401


def test_status_rejects_wrong_key(client):
    res = client.get("/status", headers={"Authorization": "Bearer wrong"})
    assert res.status_code == 403


def test_status_accepts_correct_key(client, auth_headers):
    res = client.get("/status", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["kind"] == "dummy"


def test_dev_mode_no_auth(settings_no_auth):
    app = create_app(settings_no_auth, DummyConnector())
    res = TestClient(app).get("/status")
    assert res.status_code == 200


def test_healthz_is_unauthenticated(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["ok"] is True
