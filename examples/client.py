"""Minimal Python client for printd.

Usage:
    from client import Printd
    c = Printd("http://printd.local:8080", api_key="secret")
    c.print_file("ticket.png")
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx


class Printd:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key
        self._client = httpx.Client(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def _post(self, path: str, **kw: Any) -> dict[str, Any]:
        r = self._client.post(urljoin(self.base_url, path), headers=self._headers(), **kw)
        r.raise_for_status()
        return r.json()

    def health(self) -> dict[str, Any]:
        return self._client.get(urljoin(self.base_url, "healthz")).json()

    def status(self) -> dict[str, Any]:
        r = self._client.get(urljoin(self.base_url, "status"), headers=self._headers())
        r.raise_for_status()
        return r.json()

    def print_file(
        self, path: str | Path, *, cut: bool = True, feed: int | None = None
    ) -> dict[str, Any]:
        data = Path(path).read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return self._post(
            "print",
            json={"image": f"data:image/png;base64,{b64}", "cut": cut, "feed": feed},
        )

    def print_bytes(self, png: bytes, *, cut: bool = True) -> dict[str, Any]:
        b64 = base64.b64encode(png).decode("ascii")
        return self._post("print", json={"image": b64, "cut": cut})

    def cut(self, partial: bool = False) -> None:
        self._post("cut", json={"partial": partial})

    def feed(self, lines: int) -> None:
        self._post("feed", json={"lines": lines})


if __name__ == "__main__":
    import os
    import sys

    c = Printd(os.environ["PRINTD_URL"], api_key=os.environ.get("PRINTD_API_KEY"))
    print(c.health())
    if len(sys.argv) > 1:
        print(c.print_file(sys.argv[1]))
