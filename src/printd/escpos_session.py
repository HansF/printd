"""High-level operations on top of a Connector."""

from __future__ import annotations

import time

from PIL import Image

from .connectors import Connector
from .image_pipeline import prepare_for_print


def print_image(
    connector: Connector,
    src: Image.Image,
    *,
    print_width: int = 576,
    pad_rows: int = 24,
    cut: bool = True,
    feed_before_cut: int = 4,
    partial_cut: bool = False,
) -> tuple[int, int]:
    """Render and print an image. Returns (width, height) of the bitmap sent."""
    prepared = prepare_for_print(src, print_width=print_width, pad_rows=pad_rows)
    with connector.session() as p:
        # Single-shot GS v 0 raster — bitImageRaster issues one command for the
        # whole bitmap, which is what keeps the print head from desyncing.
        p.image(prepared.image, impl="bitImageRaster")
        if cut:
            if feed_before_cut > 0:
                p.text("\n" * feed_before_cut)
            time.sleep(0.5)  # let dense raster drain before we send the cut byte
            p.cut(mode="PART" if partial_cut else "FULL", feed=False)
        else:
            p.text("\n\n")
    return prepared.width, prepared.height


def cut(connector: Connector, *, partial: bool = False) -> None:
    with connector.session() as p:
        p.text("\n\n\n")
        time.sleep(0.3)
        p.cut(mode="PART" if partial else "FULL")


def feed(connector: Connector, lines: int) -> None:
    with connector.session() as p:
        p.text("\n" * max(0, int(lines)))


def write_raw(connector: Connector, data: bytes) -> int:
    with connector.session() as p:
        p._raw(data)  # noqa: SLF001 — escape hatch by design
    return len(data)
