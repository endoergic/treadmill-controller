# Recommended Tech Stack

The deciding constraint is the **Pi Zero W v1.1**: ARMv6, single core, 512 MB RAM.
The stack has to install from prebuilt packages (compiling on a Zero takes hours) and
idle at a few tens of MB.

## Summary

| Layer | Choice | Why |
|-------|--------|-----|
| OS | **Raspberry Pi OS Lite (32-bit)**, headless | Only 32-bit images run on ARMv6. Lite has no desktop, which saves about 200 MB RAM. |
| Language | **Python 3** (ships with the OS) | First-class on Pi. Best GPIO libraries. No toolchain to install. |
| GPIO | **gpiozero** on the **lgpio** backend | Current recommended Pi GPIO stack. Has a built-in *mock* pin factory, so the app runs and tests on a Mac. |
| Web framework | **Starlette** + **uvicorn** (plain, not `[standard]`) | Async, built-in WebSockets, static files. Pure Python, so no compiling. |
| Realtime | **WebSocket** (one connection per phone) | Instant button feedback. Server pushes state to all phones so they stay in sync. |
| Frontend | **Vanilla HTML/CSS/JS**, no build step | Nothing to compile, small payload, easy to edit on the Pi. Big touch targets. |
| Config | **TOML** (`tomllib`, in the stdlib) | Readable button → GPIO map with no extra dependency. |
| Process mgmt | **systemd** unit | Starts on boot, restarts on crash, journald logs. |
| Discovery | **Avahi / mDNS** (preinstalled) | Phones reach `http://treadmill.local` without knowing the IP. |
| Tests | **pytest** with `GPIOZERO_PIN_FACTORY=mock` | Test press timing and safety logic without hardware. |

## Install footprint (on the Pi)

Prefer Debian packages. They're prebuilt for armhf/ARMv6 and need no compiling. `deploy/install.sh` installs:

```bash
sudo apt install python3-gpiozero python3-lgpio python3-starlette \
                 python3-uvicorn python3-websockets
```

Tested versions are listed in [setup-pi.md](setup-pi.md#tested-versions). Tests run on a laptop, not on the Pi
(see `requirements-dev.txt`).

## Alternatives considered (and why not)

| Option | Problem on a Pi Zero W |
|--------|------------------------|
| **FastAPI** | Depends on pydantic v2, whose Rust core (`pydantic-core`) often has no ARMv6 wheel, so it compiles Rust on the Zero. Starlette is the same server underneath without that dependency. |
| **Node.js / Express** | Official Node builds dropped ARMv6 years ago. Only unofficial builds exist. |
| **React / Vue + bundler** | Needs a build step and node toolchain. Overkill for about 6 buttons and a number. |
| **Flask** | Works, but WebSockets need extra libraries and it's sync. Fine as a fallback. |
| **Home Assistant / Node-RED** | Too heavy for 512 MB, and adds a lot of moving parts for one device. |
| **RPi.GPIO** | Legacy. gpiozero/lgpio is the maintained path and has mocking. |

## App architecture

See [architecture.md](architecture.md): modules, WebSocket protocol, queue and safety rules, config keys.

## Dev workflow

1. Develop on a laptop with `GPIOZERO_PIN_FACTORY=mock`. The UI and logic are fully testable.
2. Deploy with `rsync` to the Pi (or `git pull` on the Pi), then `sudo systemctl restart treadmill`.
3. Logs: `journalctl -u treadmill -f`.
