"""Connectors that wrap python-escpos backends.

Each connector returns a context-managed `escpos.Escpos`-compatible object.
The `dummy` connector is used in tests and for local dev without hardware.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, suppress
from typing import Protocol

from escpos.escpos import Escpos
from escpos.printer import File, Network, Serial

from .config import PrinterKind, Settings


class Connector(Protocol):
    kind: PrinterKind
    target: str

    @contextmanager
    def session(self) -> Iterator[Escpos]: ...


class UsbConnector:
    """File-backed USB printer (e.g. /dev/usb/lp0 via the kernel `usblp` module)."""

    kind: PrinterKind = "usb"

    def __init__(self, device: str) -> None:
        self.target = device

    @contextmanager
    def session(self) -> Iterator[Escpos]:
        p = File(self.target)
        try:
            yield p
        finally:
            with suppress(Exception):
                p.close()


class NetworkConnector:
    """ESC/POS over raw TCP (port 9100 by convention)."""

    kind: PrinterKind = "network"

    def __init__(self, target: str) -> None:
        self.target = target

    def _parse(self) -> tuple[str, int]:
        host, _, port = self.target.partition(":")
        return host, int(port or "9100")

    @contextmanager
    def session(self) -> Iterator[Escpos]:
        host, port = self._parse()
        p = Network(host, port=port)
        try:
            yield p
        finally:
            with suppress(Exception):
                p.close()


class SerialConnector:
    kind: PrinterKind = "serial"

    def __init__(self, device: str) -> None:
        self.target = device

    @contextmanager
    def session(self) -> Iterator[Escpos]:
        p = Serial(devfile=self.target)
        try:
            yield p
        finally:
            with suppress(Exception):
                p.close()


class DummyConnector:
    """In-memory connector — captures every byte for tests and dry runs."""

    kind: PrinterKind = "dummy"

    def __init__(self) -> None:
        self.target = "memory"
        self.buffer = bytearray()

    @contextmanager
    def session(self) -> Iterator[Escpos]:
        from escpos.printer import Dummy

        p = Dummy()
        try:
            yield p
        finally:
            self.buffer.extend(p.output)


def make_connector(cfg: Settings) -> Connector:
    match cfg.printer_kind:
        case "usb":
            return UsbConnector(cfg.device)
        case "network":
            return NetworkConnector(cfg.device)
        case "serial":
            return SerialConnector(cfg.device)
        case "dummy":
            return DummyConnector()
