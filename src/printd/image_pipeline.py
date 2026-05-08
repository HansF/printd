"""Image preparation for ESC/POS thermal heads.

The pipeline mirrors the proven path from XP-80T field testing:

1. Decode the input as RGB.
2. If the source is already <= the head dot count, skip resampling — the
   client has done the work and resampling would only soften strokes.
3. Otherwise downscale (LANCZOS) to the head width.
4. Threshold to 1-bit black/white at luminance 128.
5. Bottom-pad with `pad_rows` white rows. Some thermal printers drop the
   last few raster rows on dense images while the head is in a stuck-busy
   state; padding ensures any dropped rows are blank, not content.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class PreparedImage:
    image: Image.Image  # mode "1"
    width: int
    height: int
    resized: bool


def prepare_for_print(
    src: Image.Image,
    *,
    print_width: int = 576,
    pad_rows: int = 24,
) -> PreparedImage:
    rgb = src.convert("RGB")
    if rgb.width <= print_width:
        bw = rgb.convert("L").point(lambda x: 0 if x < 128 else 255, "1")
        resized = False
    else:
        ratio = print_width / rgb.width
        scaled = rgb.resize((print_width, int(rgb.height * ratio)), Image.LANCZOS)
        bw = scaled.convert("L").point(lambda x: 0 if x < 128 else 255, "1")
        resized = True

    if pad_rows > 0:
        padded = Image.new("1", (bw.width, bw.height + pad_rows), 1)
        padded.paste(bw, (0, 0))
    else:
        padded = bw

    return PreparedImage(image=padded, width=padded.width, height=padded.height, resized=resized)
