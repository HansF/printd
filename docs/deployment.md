# Deployment

`printd` is a single-process FastAPI app. Three common deployment shapes:

---

## Docker / Compose (recommended)

The repo ships a working `docker-compose.yml`:

```bash
cp .env.example .env
# edit PRINTD_API_KEY and PRINTD_DEVICE
docker compose up -d
```

USB device passthrough is the only host-specific bit. The compose file mounts `/dev/usb/lp0` into the container; if your printer lives at a different node, edit the `devices:` line. For network printers, drop `devices:` entirely and set `PRINTD_PRINTER_KIND=network`.

If your distribution uses `udev` rules that put the printer in the `lp` group rather than world-writable, uncomment the `group_add: ["7"]` block in `docker-compose.yml` (group ID 7 = `lp` on Debian/Ubuntu).

---

## Bare metal — systemd

```bash
pip install printd
cp .env.example /etc/printd.env
# edit /etc/printd.env
```

`/etc/systemd/system/printd.service`:

```ini
[Unit]
Description=printd — ESC/POS print server
After=network.target

[Service]
Type=simple
User=printd
Group=lp
EnvironmentFile=/etc/printd.env
ExecStart=/usr/local/bin/python -m printd
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
```

```bash
sudo useradd -r -G lp printd
sudo systemctl daemon-reload
sudo systemctl enable --now printd
journalctl -u printd -f
```

---

## Raspberry Pi

A Pi 3 or later with the printer plugged into USB is the canonical home setup.

```bash
sudo apt install python3-pip python3-venv
sudo usermod -aG lp pi   # so the service user can write /dev/usb/lp0
python3 -m venv ~/printd-venv
~/printd-venv/bin/pip install printd
```

If `/dev/usb/lp0` ends up root-owned, drop a udev rule at `/etc/udev/rules.d/99-printd.rules`:

```
SUBSYSTEM=="usbmisc", KERNEL=="lp[0-9]*", GROUP="lp", MODE="0660"
```

Then `sudo udevadm control --reload && sudo udevadm trigger`.

---

## TLS / public exposure

Don't expose `printd` directly to the internet. The bearer-token auth is good for LAN, not for hostile networks.

If you need to reach `printd` from outside your network, put it behind a reverse proxy you trust:

### Caddy

```
print.example.com {
  reverse_proxy localhost:8080
  basicauth { admin <hashed-password> }   # optional second factor
}
```

### nginx

```
server {
  listen 443 ssl http2;
  server_name print.example.com;
  ssl_certificate     /etc/letsencrypt/live/print.example.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/print.example.com/privkey.pem;

  location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
  }
}
```

---

## Health checks

`GET /healthz` returns `200 {"ok": true, …}` whenever the process is up. It does **not** verify the printer is reachable — that's intentional, so a dead printer doesn't take the API down. Use `/status` for an authenticated probe that returns the last error encountered.
