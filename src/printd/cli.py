"""`printd-cli` — direct ESC/POS utilities (no HTTP server).

Mirrors the operational tools that ship with most thermal printers:
beep, peel, density, buzz, cut, feed, test, image.
"""

from __future__ import annotations

import argparse
import sys
import time

from PIL import Image

from . import escpos_session
from .config import load_settings
from .connectors import make_connector

# Proprietary Xprinter NVRAM commands. Harmless on non-XP devices, ignored.
NVRAM = {
    "beep_off": b"\x1f\x1b\x1f\xe0\x13\x14\x00\x04\x02\x03",
    "beep_on": b"\x1f\x1b\x1f\xe0\x13\x14\x01\x04\x02\x03",
    "peel_off": b"\x1f\x1b\x1f\xbc\x13\x14\x00",
    "peel_on": b"\x1f\x1b\x1f\xbc\x13\x14\x01",
}

DENSITY = {
    "light": b"\x1d\x7c\x01",
    "normal": b"\x1d\x7c\x04",
    "dark": b"\x1d\x7c\x07",
}


def _conn():
    return make_connector(load_settings())


def cmd_beep(args):
    escpos_session.write_raw(_conn(), NVRAM["beep_off" if args.state == "off" else "beep_on"])
    print(f"Cutter alarm {args.state.upper()} — power-cycle the printer to apply.")


def cmd_peel(args):
    escpos_session.write_raw(_conn(), NVRAM["peel_off" if args.state == "off" else "peel_on"])
    print(f"Peel mode {args.state.upper()} — power-cycle the printer to apply.")


def cmd_density(args):
    escpos_session.write_raw(_conn(), DENSITY[args.level])
    print(f"Print density set to '{args.level}'.")


def cmd_buzz(args):
    n = max(1, min(args.times, 9))
    t = max(1, min(args.duration, 9))
    escpos_session.write_raw(_conn(), b"\x1b\x42" + bytes([n, t]))
    print(f"Buzzed {n}x for {t * 100}ms each.")


def cmd_cut(args):
    escpos_session.cut(_conn(), partial=args.partial)
    print(("PART" if args.partial else "FULL") + " cut done.")


def cmd_feed(args):
    escpos_session.feed(_conn(), args.lines)
    print(f"Fed {args.lines} lines.")


def cmd_test(_args):
    conn = _conn()
    with conn.session() as p:
        p.set(align="center", bold=True, height=2, width=2)
        p.text("printd\n")
        p.set(align="center", bold=False, height=1, width=1)
        p.text("python-escpos test\n")
        p.text("-" * 32 + "\n")
        p.set(align="left")
        p.text("Normal text\n")
        p.set(bold=True)
        p.text("Bold text\n")
        p.set(bold=False, underline=1)
        p.text("Underline text\n")
        p.set(underline=0, align="center")
        p.text("\nALIGN CENTER\n")
        p.set(align="right")
        p.text("ALIGN RIGHT\n")
        p.text("-" * 32 + "\n\n\n")
        time.sleep(0.3)
        p.cut()
    print("Test page printed.")


def cmd_image(args):
    cfg = load_settings()
    img = Image.open(args.file)
    w, h = escpos_session.print_image(
        _conn(),
        img,
        print_width=cfg.print_width,
        pad_rows=cfg.bottom_pad_rows,
        cut=not args.no_cut,
        feed_before_cut=cfg.feed_before_cut,
    )
    print(f"Printed {args.file} ({w}x{h}).")


def main() -> None:
    ap = argparse.ArgumentParser(prog="printd-cli", description="ESC/POS utility shell.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_beep = sub.add_parser("beep", help="Cutter alarm on/off (needs power cycle)")
    p_beep.add_argument("state", choices=["on", "off"])
    p_beep.set_defaults(func=cmd_beep)

    p_peel = sub.add_parser("peel", help="Peel mode on/off (needs power cycle)")
    p_peel.add_argument("state", choices=["on", "off"])
    p_peel.set_defaults(func=cmd_peel)

    p_den = sub.add_parser("density", help="Print density")
    p_den.add_argument("level", choices=["light", "normal", "dark"])
    p_den.set_defaults(func=cmd_density)

    p_buzz = sub.add_parser("buzz", help="Trigger buzzer manually")
    p_buzz.add_argument("--times", type=int, default=1)
    p_buzz.add_argument("--duration", type=int, default=3)
    p_buzz.set_defaults(func=cmd_buzz)

    p_cut = sub.add_parser("cut", help="Feed and cut paper")
    p_cut.add_argument("--partial", action="store_true")
    p_cut.set_defaults(func=cmd_cut)

    p_feed = sub.add_parser("feed", help="Feed paper N lines")
    p_feed.add_argument("lines", type=int, nargs="?", default=3)
    p_feed.set_defaults(func=cmd_feed)

    p_test = sub.add_parser("test", help="Print a test page")
    p_test.set_defaults(func=cmd_test)

    p_img = sub.add_parser("image", help="Print an image file")
    p_img.add_argument("file")
    p_img.add_argument("--no-cut", action="store_true", dest="no_cut")
    p_img.set_defaults(func=cmd_image)

    args = ap.parse_args()
    try:
        args.func(args)
    except FileNotFoundError as e:
        print(f"Device not found: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
