# Project Charter: Treadmill Controller

| | |
|---|---|
| **Owner** | endoergic |
| **Users** | Anyone in the household with a phone on the home Wi-Fi |
| **Hardware** | Raspberry Pi Zero W v1.1, existing treadmill console + motor controller |
| **Started** | 2026-10-04 |
| **Status** | Released v1.0.0 (2026-11-14) |

## 1. Background

The treadmill's button board (membrane keypad) has failed. The console electronics and
motor controller still work. At the start, household switches wired across the keypad connector
could reproduce **speed up** and **speed down**; the rest of the button combinations were unknown.
By v1.0.0 every keypad button except Heart Rate ▲▼ is mapped ([button-map.md](hardware/button-map.md)).

## 2. Purpose

Make the treadmill usable again without a replacement keypad. Each button gets an
electronic switch driven by a Raspberry Pi, and the Pi serves a phone-friendly web app.

## 3. Objectives & success criteria

| # | Objective | Success measure |
|---|-----------|-----------------|
| O1 | Pi can press every known button | Each mapped button responds 100% of the time across 50 test presses |
| O2 | Phone control | Any household phone opens `http://treadmill.local` and controls the treadmill, with no app install |
| O3 | Responsive | Under 300 ms from tap to button press on the home LAN |
| O4 | Fail-safe electronics | On power loss, crash, or reboot of the Pi, no buttons are pressed (all relays open) |
| O5 | Shared state | Two phones open at once both show the same estimated speed and status |
| O6 | Extensible | Adding a newly discovered button/combo is a config edit, with no code change |

## 4. Scope

**In scope**
- Interface board: 10 isolated PhotoMOS relays, one per HD6 keypad pin, each connecting its pin to a shared line (relay 1 = "Go")
- Web app on the Pi: start, stop, speed +/−, presets (e.g. "go to 3.0 mph"), plus any buttons discovered later
- Estimated speed/state tracking (open-loop: counted presses)
- Software limits: max speed, press-rate limiting, optional auto-stop when no phone is connected (auto-stop not implemented in v1.0.0)
- A discovery tool (CLI) for trying button combos to finish the button map
- Install/deploy as a systemd service that starts on boot

**Out of scope (for now)**
- Changes to the motor controller or anything on the mains side
- Replacing or bypassing the physical safety key
- Access from outside the home network (no port forwarding or cloud)
- Accounts and user profiles
- Native mobile apps

**Decision (2026-10-04):** keep emulating the console's keypad rather than driving the MC-2100
motor controller. Controlling the MC-2100 is well documented, but it disconnects the console
(display and safety key) and leaves stopping safely after a Pi crash up to us.

**Future candidates**
- **iFit audio chirps** via the console's "Interactive In" jack. Could give absolute speed and incline with no wiring. Try it first by playing a generated chirp file from a laptop.
- Closed-loop speed: read actual belt speed with a reed/hall sensor on the roller, or tap the console's speed signal
- Workout programs (intervals, ramps), session history
- Auto-stop when no phone is connected
- Soldered (Perma-Proto) version of the interface board

## 5. Constraints

- **Pi Zero W v1.1**: single-core ARMv6 at 1 GHz, 512 MB RAM, 2.4 GHz Wi-Fi only. Runs 32-bit Raspberry Pi OS only. Many modern toolchains (Node.js official builds, Rust-compiled Python wheels) don't support ARMv6 well. See [tech-stack.md](tech-stack.md).
- **GPIO**: 3.3 V logic, small current budget (about 16 mA per pin, about 50 mA total recommended).
- **No electrical connection** between Pi ground and treadmill electronics. Treadmill controllers sit next to mains/high-voltage DC.
- Button presses are momentary and the console gives no feedback, so speed shown in the app is **an estimate**.

## 6. Safety principles

1. The physical safety key is the primary stop. The app never replaces or overrides it.
2. **Fail open**: every failure mode (Pi off, app crash, GPIO uninitialized, Wi-Fi drop) leaves all buttons unpressed.
3. A button is never held longer than a configured maximum (watchdog).
4. STOP always jumps ahead of anything queued and is always visible in the UI.
5. Configurable max speed and press rate limits.
6. LAN-only. An optional household PIN guards against accidental taps from guests or kids.

## 7. Milestones

| # | Milestone | Deliverable | Status (v1.0.0) |
|---|-----------|-------------|-----------------|
| M0 | Document current state | Schematic in `hardware/schematics/`, button map started | Met |
| M1 | Interface board | 10-relay PhotoMOS board on HD6, bench-tested, speed ± verified | Met as a breadboard build ([breadboard-build.md](hardware/breadboard-build.md)); soldered version not built |
| M2 | Discovery tool | `scripts/probe.py` presses any button or combo from the terminal; button map completed | Met (Heart Rate ▲▼ not identified) |
| M3 | Web app MVP | Start / stop / speed ± from a phone, estimated speed, live sync between phones | Met (presets, incline, fan, programs, odometer included) |
| M4 | Hardening | systemd service, watchdog, limits, auto-stop option, `treadmill.local` hostname | Partly met: systemd service, `max_press_ms` limit, max speed, rate limit and hostname done; auto-stop not implemented |
| M5 | Nice-to-haves | Presets, PWA "add to home screen", workout programs | Not started (presets were delivered in M3) |

## 8. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Unknown console voltages or polarities | Interface doesn't trigger, or damages the console | Measure first ([rewiring guide §2](hardware/rewiring-guide.md#2-measure-first-10-minutes-multimeter)); done 2026-11-08. PhotoMOS works with either polarity. |
| Estimated speed drifts from actual speed | User confusion | Reset estimate on STOP, add a "sync" correction control, closed-loop sensor later |
| Pi boots with GPIO in an odd state | Accidental button press | Use GPIOs that default to pull-down at boot (done); relays start open. 10 kΩ pull-downs were not needed |
| ARMv6 package incompatibility | Install pain, long compiles | Pure-Python stack from apt (see tech-stack.md) |
| Wi-Fi drop mid-workout | Can't change speed from the phone | Safety key. Auto-stop on lost connection is not implemented in v1.0.0. |
| Ground loop / mains fault into the Pi | Pi or phone charger damage, shock risk | Full optical isolation, separate Pi power supply |

## 9. Open questions

Answered during the build:

- **Full button map?** Done by the probe scan on 2026-11-14: stop, start, incline ▲▼, the 1–10 mph presets, fan,
  programs and odometer are all mapped ([button-map.md](hardware/button-map.md#commands)).
- **Is Black (HD6 pin 1) GND?** Yes. Pins 1 and 10 are console ground (0 V to each other, 111 Ω to the plug's
  earth prong); pins 2–9 idle at +3.4 V DC. HD6 is 3.3 V logic and has no path to live or neutral (measured
  2026-11-08).

Still open:

- Heart Rate ▲▼: probably 4 + 9 and 5 + 9 (error beep in every state; likely needs a heart-rate sensor).
- Console minimum/maximum speed, the shortest Go press that registers, and what happens when the safety key is
  pulled and reinserted (not measured).
- Does the iFit Interactive In jack respond to chirps without a mode button press?
