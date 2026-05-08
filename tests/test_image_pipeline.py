from __future__ import annotations

from PIL import Image

from printd.image_pipeline import prepare_for_print


def _solid(w: int, h: int, color: int) -> Image.Image:
    return Image.new("RGB", (w, h), (color, color, color))


def test_skip_resize_when_already_in_budget():
    src = _solid(570, 100, 255)
    out = prepare_for_print(src, print_width=576, pad_rows=24)
    assert out.resized is False
    assert out.width == 570
    assert out.height == 100 + 24
    assert out.image.mode == "1"


def test_skip_resize_at_exact_head_width():
    src = _solid(576, 80, 255)
    out = prepare_for_print(src, print_width=576, pad_rows=0)
    assert out.resized is False
    assert out.width == 576
    assert out.height == 80


def test_lanczos_resize_when_too_wide():
    src = _solid(1280, 200, 255)
    out = prepare_for_print(src, print_width=576, pad_rows=0)
    assert out.resized is True
    assert out.width == 576
    # 200 * (576/1280) = 90
    assert out.height == 90


def test_threshold_splits_at_128():
    src = Image.new("L", (10, 3), 0)
    src.putpixel((0, 0), 127)
    src.putpixel((1, 0), 128)
    src.putpixel((2, 0), 200)
    rgb = src.convert("RGB")
    out = prepare_for_print(rgb, print_width=576, pad_rows=0)
    px = out.image.load()
    # In mode "1", `.load()` returns 0 for black and a non-zero value for white
    # (0 vs 1 in older Pillow, 0 vs 255 in newer). Compare via truthiness.
    assert not px[0, 0]
    assert px[1, 0]
    assert px[2, 0]


def test_bottom_pad_is_white():
    src = _solid(100, 50, 0)  # entirely black source
    out = prepare_for_print(src, print_width=576, pad_rows=10)
    assert out.height == 60
    px = out.image.load()
    # Last 10 rows should all be white.
    for y in range(50, 60):
        for x in range(100):
            assert px[x, y]
    # Top rows should be black.
    assert not px[0, 0]
    assert not px[50, 25]


def test_pad_rows_zero_skips_padding():
    src = _solid(200, 50, 255)
    out = prepare_for_print(src, print_width=576, pad_rows=0)
    assert out.height == 50
