# Supported printers

`printd` speaks generic ESC/POS via [python-escpos](https://python-escpos.readthedocs.io). Anything python-escpos can drive should work; this page lists devices that have been verified end-to-end and any quirks worth knowing.

If you've successfully driven another model through `printd`, please open a PR adding a section here.

---

## Xprinter XP-80T (USB)

80 mm direct-thermal receipt printer, exposed as `/dev/usb/lp0` on Linux via the kernel `usblp` module — no CUPS or vendor driver needed. Print head: 576 dots, 72 mm printable width.

```env
PRINTD_PRINTER_KIND=usb
PRINTD_DEVICE=/dev/usb/lp0
PRINTD_PRINT_WIDTH=576
```

Make sure your user is in the `lp` group:
```bash
sudo usermod -aG lp $USER
# log out and back in
```

### Cutter alarm (3 beeps + red LED)

The XP-80T ships in **"Kitchen Mode"** by default — every auto-cut triggers 3 beeps and a red LED flash. This is intentional firmware behaviour, not an error. Disable it with:

```bash
printd-cli beep off
# power-cycle the printer to apply
```

Re-enable: `printd-cli beep on`.

The setting is written to NVRAM via a proprietary Xprinter command:
```
b'\x1f\x1b\x1f\xe0\x13\x14\x00\x04\x02\x03'  # beep off
b'\x1f\x1b\x1f\xe0\x13\x14\x01\x04\x02\x03'  # beep on
```

### Density

```bash
printd-cli density dark     # GS | 7
printd-cli density normal   # GS | 4 (factory default)
printd-cli density light    # GS | 1
```

### DIP switches

The XP-80T has physical DIP switches on the underside:

| Switch | ON | OFF |
|---|---|---|
| SW-1 | Cutter disabled | Cutter enabled |
| SW-2 | Beeper enabled | Beeper disabled |
| SW-3 | Dark / high density | Normal density |
| SW-6 | Kitchen alarm on cut | Alarm disabled |
| SW-8 | 115200 bps | 9600 bps |

### Cut alignment

The cutter blade sits ~18 mm above the print head. After printing, paper must be fed past the blade before cutting. `printd` sends `feed=4` newlines (≈20 mm) by default — adjust via `PRINTD_FEED_BEFORE_CUT` if your content needs a different gap.

### Dropped-row mitigation

On dense raster (thick borders, bold/black weights, solid black fills) the XP-80T can briefly enter a **stuck-busy** state where the print head is not actively printing but pending raster has not yet drained. If `cut` is sent during this state, the cut lands inside the image and the last few rows reappear at the top of the next ticket.

`printd` mitigates this two ways:
1. **Always single-shot the raster** via `bitImageRaster` (one `GS v 0` command per print).
2. **Bottom-pad** every image with 24 white rows (`PRINTD_BOTTOM_PAD_ROWS`) so any dropped rows are blank rather than content.

A `time.sleep(0.5)` between feed and cut also helps drain the buffer, but longer sleeps don't — the printer is genuinely not printing during the wait, so waiting longer is wasted.

**Best fix is at the source**: keep templates light. Avoid `border-[4px]+`, `font-black`, and large solid-black fills. A handful of text lines on an 80 mm × 80 mm receipt is fine; large black blocks are not.

---

## Network ESC/POS printers (e.g. Epson TM-T88)

```env
PRINTD_PRINTER_KIND=network
PRINTD_DEVICE=192.168.1.50:9100
```

`printd` opens a raw TCP connection (port 9100 by convention) and writes ESC/POS directly. No printer-specific driver needed.

---

## Serial printers

```env
PRINTD_PRINTER_KIND=serial
PRINTD_DEVICE=/dev/ttyUSB0
```

Baud rate defaults to whatever the printer is set to (DIP switches or a vendor utility usually); adjust at the python-escpos level if needed by extending `SerialConnector`.

---

## Dummy / dry-run

For testing on a machine with no printer attached:

```env
PRINTD_PRINTER_KIND=dummy
PRINTD_DEVICE=memory
```

The dummy connector accepts every ESC/POS byte and discards it. Useful for CI, frontend development, and integration tests in `pos-exchange-tickets`-style downstream apps.
