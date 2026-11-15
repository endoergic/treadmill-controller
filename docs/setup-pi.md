# Pi setup: from a blank SD card to the first press

This guide sets up a Raspberry Pi Zero W to run the treadmill web app. It assumes the relay board is already built
([breadboard build](hardware/breadboard-build.md)).

Throughout, `pi` is the example username. **Substitute the username you choose in step 1.**

> **Safety:** the treadmill's safety key is the real stop. The app's STOP button is a convenience. Keep the treadmill
> unplugged until step 8.

## Tested versions

| Item | Version |
|------|---------|
| Board | Raspberry Pi Zero W Rev 1.1 (armv6l) |
| OS | Raspberry Pi OS Lite (32-bit), Raspberry Pi OS 13 "trixie" |
| Python | 3.13.5 (ships with the OS) |
| python3-gpiozero | 2.0.1 |
| python3-lgpio | 0.2.2 |
| python3-starlette | 0.46.1 |
| python3-uvicorn | 0.32.0 |
| python3-websockets | 15.0.1 |

The Python packages come from apt and are installed by `deploy/install.sh`. Nothing is compiled on the Pi.

## 1. Flash the SD card

1. Install **Raspberry Pi Imager** on your laptop.
2. Device: **Raspberry Pi Zero**. OS: **Raspberry Pi OS (other) → Raspberry Pi OS Lite (32-bit)**.
   The Zero W is ARMv6, so it needs the 32-bit image. Lite has no desktop.
3. In the customisation settings:
   - Hostname: **`treadmill`** (phones will open `http://treadmill.local`).
   - Username and password: your choice (this guide uses `pi`).
   - Wi‑Fi: your home network name, password and country.
   - Services: **enable SSH** with **public-key authentication only**, and paste your laptop's public key
     (for example the contents of `~/.ssh/id_ed25519.pub`).
4. Write the card, put it in the Pi, and power the Pi from its own USB supply.

## 2. First boot and SSH

The first boot takes a few minutes on a Zero. Then, from your laptop:

```bash
ssh pi@treadmill.local
```

## 3. Copy the repository to the Pi

Either clone it on the Pi:

```bash
sudo apt install -y git
git clone https://github.com/endoergic/treadmill-controller ~/treadmill-controller
```

or copy it from your laptop (run in the repo folder on the laptop):

```bash
rsync -a --relative --exclude __pycache__ scripts config app deploy tests pi@treadmill.local:treadmill-controller/
```

## 4. Install the app and the service

On the Pi:

```bash
cd ~/treadmill-controller
sudo sh deploy/install.sh
```

The script:

- installs `python3-gpiozero python3-lgpio python3-starlette python3-uvicorn python3-websockets` with apt;
- fills your username and the repo folder into `deploy/treadmill.service` and installs it as
  `/etc/systemd/system/treadmill.service`;
- enables the service (starts on boot) and starts it.

The service runs `python3 -m treadmill.main` with `PYTHONPATH=app` as your user, listens on port 80 (allowed through
`CAP_NET_BIND_SERVICE`, no root), and restarts on failure.

## 5. Configure

The app reads `config/treadmill.toml` if it exists, otherwise `config/treadmill.example.toml`. Make your own copy:

```bash
cp config/treadmill.example.toml config/treadmill.toml
nano config/treadmill.toml
sudo systemctl restart treadmill
```

Settings you are most likely to change:

| Key | Default | What it does |
|-----|---------|--------------|
| `[server] pin` | `""` | Household PIN asked by the phone. Empty = no PIN. |
| `[safety] max_speed` | `6.0` | App speed limit. Taps and presets above it are refused. 6.0 is a placeholder, not measured. |
| `[hd6.gpio]` | see file | HD6 pin → BCM GPIO. Change only if you wired the board differently. |
| `[commands]` | see file | Button → keypad lines. Change if your console maps differently. |

All keys: [architecture.md → Config](architecture.md#config).

## 6. Optional: passwordless service control (sudoers rule)

`scripts/probe.py` stops and restarts the service on its own, using `sudo -n`. That needs this rule. It also lets you
restart the service without typing a password.

Create a file, for example `~/treadmill.sudoers`, with **one command per line** (replace `pi` with your username):

```
pi ALL=(root) NOPASSWD: /usr/bin/systemctl start treadmill
pi ALL=(root) NOPASSWD: /usr/bin/systemctl stop treadmill
pi ALL=(root) NOPASSWD: /usr/bin/systemctl restart treadmill
```

A line wrapped onto two lines is a syntax error. Validate, then install:

```bash
sudo visudo -c -f ~/treadmill.sudoers
sudo install -m 440 -o root -g root ~/treadmill.sudoers /etc/sudoers.d/treadmill
```

## 7. Verify the service

```bash
systemctl status treadmill        # should say "active (running)"
journalctl -u treadmill -f        # live log; "ready: commands ..." means it started
```

Open **http://treadmill.local** on a phone on the same Wi‑Fi. The page should show "connected".

## 8. Bench test (no treadmill)

Do this with the ribbon **not** plugged onto HD6 (or the treadmill unplugged from the wall).

The service holds the GPIOs, so stop it first:

```bash
sudo systemctl stop treadmill
python3 scripts/relay_test.py              # each relay on, one at a time
python3 scripts/relay_test.py --channel 2 --on 5   # hold one relay for the meter check
sudo systemctl start treadmill
```

Each indicator LED should light in turn. Only one relay is ever on at once, so the light show is safe even with the
treadmill connected.

**Meter check:** an indicator LED lighting does **not** prove the relay switches (the LED has its own path). With the
multimeter on beep, put the probes on the S rail and hole **j R** of the channel while that relay is held on: it must
beep, and go silent when the relay turns off. During the build, two touching resistor legs kept relay 2 on
permanently; this check finds that. More: [breadboard build → Troubleshooting](hardware/breadboard-build.md#troubleshooting).

## 9. First live press

1. Treadmill unplugged. Push the ribbon plug onto the HD6 header, dot to dot.
2. Plug the treadmill in, insert the safety key. **Nobody on the belt. Keep a hand on the safety key.**
3. On the phone, press **speed +**. The belt should start at 1.0 mph. Press **speed −** and **STOP**.

If nothing happens, see [breadboard build → Step 8](hardware/breadboard-build.md#step-8--first-real-test) and
[rewiring guide §7](hardware/rewiring-guide.md#7-test-sequence). If your console responds differently, map it with
`scripts/probe.py` ([rewiring guide §9](hardware/rewiring-guide.md#9-discovery-mode)).

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `relay_test.py` or `probe.py` fails because a GPIO is busy | The service is running and holds the GPIOs. `sudo systemctl stop treadmill` first (`probe.py` does this itself if the sudoers rule is installed). |
| `sudo: systemctl: command not found` | You ran the command on your laptop. Run it on the Pi (`ssh pi@treadmill.local`). |
| Phone shows the old UI after an update | Reload the page. Static files are served with `Cache-Control: no-cache`, so a normal reload is enough. |
| SSH key refused | Wrong username in `ssh user@treadmill.local`, or wrong permissions on the Pi: `~/.ssh` must be `700`, `~/.ssh/authorized_keys` `600`, both owned by your user (not root). |
| A background script started over SSH ignores Ctrl+C | Stop it with SIGTERM: `kill <pid>`. |
