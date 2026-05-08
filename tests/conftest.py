from __future__ import annotations

import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from printd.app import create_app
from printd.config import Settings
from printd.connectors import DummyConnector


@pytest.fixture
def settings() -> Settings:
    return Settings(
        api_key="test-key",
        printer_kind="dummy",
        device="dummy",
        print_width=576,
        bottom_pad_rows=24,
        feed_before_cut=4,
        cors_origins="*",
    )


@pytest.fixture
def settings_no_auth() -> Settings:
    return Settings(api_key="", printer_kind="dummy", device="dummy")


@pytest.fixture
def connector() -> DummyConnector:
    return DummyConnector()


@pytest.fixture
def app(settings: Settings, connector: DummyConnector):
    return create_app(settings, connector)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-key"}


def _png_bytes(w: int, h: int, color: tuple[int, int, int] = (0, 0, 0)) -> bytes:
    img = Image.new("RGB", (w, h), (255, 255, 255))
    # Draw a single black pixel so the image isn't entirely white.
    img.putpixel((w // 2, h // 2), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def png_bytes():
    return _png_bytes


@pytest.fixture
def png_data_url(png_bytes):
    def _make(w: int = 320, h: int = 240) -> str:
        b64 = base64.b64encode(png_bytes(w, h)).decode("ascii")
        return f"data:image/png;base64,{b64}"

    return _make
