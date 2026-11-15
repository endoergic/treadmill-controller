# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Build photos (metadata stripped): console, finished relay board, HD6 before/after, ribbon plug; shown in the
  README and the breadboard build guide.

### Changed

- Docs and parts list accept any 40-pin T-type GPIO breakout (Adafruit T-Cobbler Plus or a generic "GPIO Extension
  Board", which the tested build used); wire by the board's printed labels.
- Photos renamed descriptively (`IMG_2173/2174/2390.jpeg` → `console.jpeg`, `console-keypad.jpeg`, `hd6-header.jpeg`).

## [1.0.0] - 2026-11-14

First public release.

### Added

- Web app (Starlette + uvicorn) on a Raspberry Pi Zero W at `http://treadmill.local`: LAN only, optional household PIN.
- Phone UI (plain HTML/CSS/JS): speed ±, START / STOP, 1–10 mph presets, incline ▲▼, fan, programs, odometer.
  Buttons come from `[commands]` in the config; unknown names become extra buttons.
- Live sync: one WebSocket per phone; the server broadcasts state to every phone.
- Controller: single worker queue, open-loop speed estimate, presets via `sets_speed`, `start` that only moves the
  estimate from stopped, `max_speed` limit that counts queued taps, rate limit, STOP that jumps the queue and bypasses
  the rate limit, reset of the estimate.
- Hidden "Manual signals" troubleshooting panel (tap "connected" 5× within 3 s, or `/#manual`) with the same queue
  and checks, logged to journald, last 8 presses kept on the phone.
- PhotoMOS relay driver (gpiozero, lgpio backend) with fail-open behaviour: relays start open, Go is released first,
  everything is released in `finally` and on shutdown.
- Config validation (`config/treadmill.example.toml`): ground pins, GPIO map, timings, `max_relays_on`.
- Static files served with `Cache-Control: no-cache`.
- `deploy/install.sh` and a systemd unit (port 80 via `CAP_NET_BIND_SERVICE`, restart on failure).
- `scripts/relay_test.py` (bench light show) and `scripts/probe.py` (keypad discovery, logs to
  `docs/hardware/discovery-log.csv`).
- 13 pytest tests against gpiozero's mock pins; `requirements-dev.txt`.
- Docs: README, Pi setup guide, architecture, kid-friendly breadboard build, shopping list, rewiring guide,
  button map, relay board schematic, breadboard layout picture, photos.

### Hardware verified

- NordicTrack C2100, model NTL1085, Solaris console, MC-2100WA motor controller (Icon drawing #214876, 8/2004).
- Raspberry Pi Zero W Rev 1.1, Raspberry Pi OS 13 "trixie", Python 3.13.5.
- Panasonic AQY212EH PhotoMOS relays, 10 channels on a full-size breadboard with a generic 40-pin T-type GPIO
  extension board (the docs also list the Adafruit T-Cobbler Plus #2028; wire by the printed labels).
- HD6 measured (2026-11-08): 3.3 V logic, ground on pins 1 and 10, no path to live or neutral.
- All commands confirmed on the belt (2026-11-14), Go = pin 1: speed_up 2+7 (starts at 1.0 mph), speed_down 3+6,
  start 3+7, stop 4+6, incline_up 4+7, incline_down 5+6, presets 1–10 mph, fan 8+9, programs 6+9, odometer 7+9.

### Known limitations

- Speed is open-loop: no feedback from the console; the estimate can drift.
- Heart Rate ▲▼ not mapped (4+9 and 5+9 beep in every state; probably needs a heart-rate sensor).
- `max_speed = 6.0` is a placeholder, not measured.
- Not measured: console minimum and maximum speed, shortest Go press that registers, safety-key pull/reinsert
  behaviour.
- Breadboard build only; a soldered Perma-Proto version is suggested but not built.
- No auto-stop when phones disconnect.
- Tested on one treadmill only.

### Removed before release

- Direct drive mode (Pi GPIOs wired straight to HD6, no relays).
- LED playground.
- Printable measure sheet.
- LED light-show layout picture.

[1.0.0]: https://github.com/endoergic/treadmill-controller/releases/tag/v1.0.0
