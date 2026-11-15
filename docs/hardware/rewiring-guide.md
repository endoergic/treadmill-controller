# Rewiring Guide: HD6 Keypad Connector → Raspberry Pi Relay Board

This is the engineering reference for the interface between the Pi and the treadmill console. It describes the
finished v1.0 design: a Raspberry Pi Zero W drives 10 Panasonic **AQY212EH** PhotoMOS relays, one per pin of the
console's 10-pin keypad connector **HD6**. The relays "press" keypad buttons the same way the failed membrane keypad
did, and the Pi has **no electrical connection to the treadmill**.

- Step-by-step breadboard build (kid-friendly): [breadboard-build.md](breadboard-build.md)
- Schematic: [`hardware/schematic.svg`](../../hardware/schematic.svg)
- Breadboard picture: [`hardware/breadboard-layout.svg`](../../hardware/breadboard-layout.svg)
- Pinout, command map, measurements: [button-map.md](button-map.md)
- Parts: [shopping-list.md](shopping-list.md)
- Pi software: [setup-pi.md](../setup-pi.md)

Tested on one treadmill only: NordicTrack C2100 (model NTL1085), Solaris console, MC-2100WA motor controller.
Other consoles will differ. Measure yours first ([§2](#2-measure-first-10-minutes-multimeter)).

> ⚠️ **Before opening anything:** unplug the treadmill from the wall and wait a few minutes.
> The MC-2100 motor controller holds charged capacitors at mains-level DC voltage. Only work on
> the console/keypad side (HD6). Never touch the motor controller.

---

## 1. The idea

The keypad is a set of lines. HD6 pins 2–9 are eight signal lines that the console holds at 3.4 V. Pins 1 and 10
are console ground. A button grounds a **combination** of lines 2–9. Before the Pi, this was done by hand with a
household switch box (history: [button-map.md](button-map.md#old-manual-circuit-removed-with-the-socket)).

The relay board does the same thing with one relay per HD6 pin:

```
Old switch box (removed)                     Relay board (v1.0)

Black ──[SW0 Go]──┬──[SW1]── Red 1           HD6 pin 1  ──[relay 1]──┐   ← relay 1 = "Go" (pin 1 = ground)
                  ├──[SW2]── Blue 2          HD6 pin 2  ──[relay 2]──┤
                  └──[SW3]── Red 2 + Blue 1  HD6 pin 3  ──[relay 3]──┤
                                                  ⋮            ⋮      ├── shared line ("S rail")
                                             HD6 pin 10 ──[relay 10]─┘   (on the board only)
```

Each relay is a **PhotoMOS** chip. On the Pi side it's an LED; on the treadmill side it's a MOSFET switch. There is
no electrical connection between the two sides. When the Pi lights the LED, that HD6 pin joins the shared line.

A command is a sequence:

1. Close the **select** relays (e.g. pins 2 + 7 for speed up). The selected lines are now joined to the shared line.
2. Wait `settle_ms` (50 ms).
3. Close relay 1 (**Go**) for `press_ms` (300 ms). Go joins the shared line to pin 1 (ground), so the selected lines
   are grounded: that is the button press.
4. Release Go first, then all select relays.

The full command map is in [button-map.md](button-map.md#commands).

---

## 2. Measure first (10 minutes, multimeter)

Do this before building anything, on your own console. It confirms the lines are low-voltage logic and that the
console has no path to the mains wiring.

| # | Condition | Measurement | Result on the tested treadmill (2026-11-08) |
|---|-----------|-------------|---------------------------------------------|
| 1 | Unplugged | Ohms, every HD6 pin → plug ground prong | Pins 1 and 10: **111 Ω**. Pins 2–9: OL |
| 2 | Unplugged | Ohms, every HD6 pin → both flat prongs (live, neutral) | All **OL**: no path to mains |
| 3 | Powered, safety key in, nobody on the belt | DC volts, pins 2–9 vs pin 1 (black probe on pin 1) | All **+3.4 V DC**, steady, no AC |
| 4 | Powered, safety key in | DC volts, pin 1 ↔ pin 10 | **0 V**: both are ground |

Conclusion: HD6 is 3.3 V logic; a button grounds a combination of lines 2–9; Go = pin 1 (ground). That is far below
the AQY212EH's 60 V rating.

**Stop and rethink if:**
- any pin shows a beep or low resistance to **live or neutral**, or
- you see more than about 24 V, any AC, or anything else unexpected.

That means it isn't the keypad lines, or the console is tied to the wall wiring. Either way, the Pi must stay fully
isolated: keep the relays and don't connect anything until you understand it. Ground (pins 1 and 10) reading about
111 Ω to the earth prong is expected on the tested treadmill.

**Mark pin 1** on the console board before you change anything on HD6 (paint-marker dot). Once a socket is removed,
all 10 holes look the same ([§6](#6-connect-to-hd6)).

Record your results in [button-map.md](button-map.md#measurements).

---

## 3. Parts

The complete v1.0 bill of materials, with part numbers and prices, is [shopping-list.md](shopping-list.md). The
circuit itself needs:

| Qty | Part | Notes |
|-----|------|-------|
| 10 | **PhotoMOS relay, DIP-4**: Panasonic **AQY212EH** | 60 V / ~500 mA, LED trigger ≤ 3 mA. Toshiba TLP222A is end-of-life; TLP240A works as an alternative. |
| 10 | 330 Ω resistor | Relay LED current ≈ (3.3 − 1.3) / 330 ≈ **6 mA**, 2× trigger margin |
| 10 | 1 kΩ resistor + red LED | Indicator per channel, ~1.5 mA. Optional for the circuit, very useful for testing |
| 1 | Full-size 830-point breadboard + Adafruit T-Cobbler Plus #2028 | The v1.0 build. A soldered version is suggested, not built ([§10](#10-power--mounting)) |
| 1 | 2.54 mm 1×10 male header + 1×10 Dupont housing + 10 female→male Dupont wires | Replaces the original HD6 socket ([§6](#6-connect-to-hd6)) |
| 1 | **Separate** 5 V 2.5 A micro-USB supply for the Pi | Don't power the Pi from the treadmill |

**Not used:** 10 kΩ pull-down resistors. The GPIOs below default to pull-down at boot, and the relay needs a few mA
to turn on, which a floating pin can't supply. Add them only if you use other GPIOs.

**Don't buy:**
- *"Solid State Relay module, Omron G3MB-202P"* boards. They're **AC-only** and won't switch the DC keypad lines.
- Clicky 5 V mechanical relay modules. They'd work, but they're loud, need 5 V drive, and 10 of them is bulky.

---

## 4. GPIO assignment

All 10 use GPIOs that **default to pull-down at boot**, so nothing is pressed while the Pi starts up. Relays start
open (fail open). The same map is in `config/treadmill.example.toml` under `[hd6.gpio]`.

| Channel / HD6 pin | Ribbon color | Role | BCM GPIO | Pi physical pin |
|-------------------|--------------|------|----------|-----------------|
| 1 | black | Ground, **Go** | GPIO17 | 11 |
| 2 | white | Line | GPIO27 | 13 |
| 3 | grey | Line | GPIO22 | 15 |
| 4 | purple | Line | GPIO23 | 16 |
| 5 | blue | Line | GPIO24 | 18 |
| 6 | green | Line | GPIO25 | 22 |
| 7 | yellow | Line | GPIO16 | 36 |
| 8 | orange | Line | GPIO26 | 37 |
| 9 | red | Line | GPIO12 | 32 |
| 10 | brown | Ground | GPIO13 | 33 |
| Pi GND | | | | 39 (cobbler row 20) |

Ribbon colors follow standard rainbow order from black at pin 1 to brown at pin 10. Go by **position**, not color.

Current budget: ~6 mA per relay LED + ~1.5 mA per indicator. The software caps relays on at once with
`max_relays_on = 5` (about 38 mA worst case) to stay inside the Pi's GPIO current budget. Every command uses three
relays (two select + Go).

---

## 5. Build the board

Full schematic: [`hardware/schematic.svg`](../../hardware/schematic.svg) (one channel in detail plus the
10-channel overview). Per channel (×10):

```
        Pi side                    isolation ┆                Treadmill side
                                ┌──────────┐ ┆
 GPIOxx ──┬──[ 330 Ω ]──── 1 ──│ AQY212EH │─┆─ 4 ─────────────  HD6 pin n (ribbon wire)
          │                    │ (DIP-4)  │ ┆
          │                    │          │ ┆
 GND ─────┼─────────────── 2 ──│          │─┆─ 3 ──┐
          │                    └──────────┘ ┆      │
          └──[ 1 kΩ ]──▶|── GND             ┆      └──── SHARED LINE (pin 3 of all 10 relays)
              indicator LED
```

- **Pin 1** is the LED anode (dot end), **pin 2** the LED cathode, **pins 3/4** the switch. *Check against the
  datasheet of the part you buy.*
- The **indicator** has its own path (GPIO → 1 kΩ → LED → GND). It does not go through the relay, so a lit LED only
  proves the GPIO is high, not that the relay switched ([§7](#7-test-sequence)).
- The **shared line** joins pin 3 of all 10 relays and stays on the board. It doesn't go to the treadmill.
- **Pi GND is never connected to the treadmill.** Only relay pins 3 and 4 touch treadmill wires.
- No 10 kΩ pull-downs (optional, not used; see [§3](#3-parts)).

**On the breadboard** ([breadboard-build.md](breadboard-build.md)): the cobbler sits in rows 1–20; channel *n*
starts at row R = 23 + 4(n − 1). The relay straddles the center groove (dot in e R, pins in e R/e R+1 and
f R/f R+1). Relay pin 4 → HD6 pin *n* through the ribbon wire in i R; relay pin 3 → S rail through a green wire from
j R+1. The groove is the isolation barrier: nothing crosses it except the relays.

**On perfboard** (permanent build, not built for v1.0): keep at least 3 mm between Pi-side and treadmill-side copper
and cut the strips under the middle of each relay.

---

## 6. Connect to HD6

The original HD6 socket (white, latched, probably JST XH 2.5 mm) was half-melted. On the tested console it was
desoldered and replaced with a **2.54 mm 1×10 male header**. Over 10 pins, 2.54 mm vs 2.5 mm spacing is off by only
about 0.2 mm at each end, well inside the hole size. The cable to the relay board is a rainbow ribbon of 10
female→male Dupont wires, with the female ends pushed into a **1×10 Dupont housing** that plugs onto the header.
Step-by-step: [breadboard-build.md, Step 6](breadboard-build.md#step-6--put-a-header-on-hd6-one-time-grown-up-job)
and [Step 7](breadboard-build.md#step-7-plug-in-the-treadmill-kid-job).

**Mark pin 1 before removing the socket.** On the tested console, pin 1 is the hole the old switch box's Black
wire used.

The old switch box came off with the socket, including its Red 2 ↔ Blue 1 jumper. That jumper isn't needed: speed
down works with pins 3 + 6 joined only during the press (`select = [3, 6]`).

Then check with the multimeter in continuity mode, treadmill unplugged and Pi off:
- Each ribbon wire's breadboard end ↔ its HD6 header pin: beep, for all 10.
- **Any treadmill-side point (S rail, column f–j, ribbon wires) ↔ any Pi pin or Pi GND: no beep, ever.**

---

## 7. Test sequence

This is the sequence used on the tested build. `relay_test.py` and `probe.py` need the GPIOs, so stop the app
first if it is installed: `sudo systemctl stop treadmill`.

**Bench (treadmill unplugged, ribbon not on HD6):**

1. **Isolation check.** Pi unplugged, meter on beep. Pi GND (− rail) ↔ S rail: silent. Pi GND ↔ every hole in
   column j, rows 23–62: silent.
2. **Light show.** Power the Pi and run
   ```bash
   python3 scripts/relay_test.py              # all 10, one at a time
   python3 scripts/relay_test.py --channel 1  # just one
   ```
   Each indicator LED lights in order, 1 → 10. This proves the GPIO wiring only.
3. **Meter test (proves the relay switches).** Hold one relay on and check its switch side:
   ```bash
   python3 scripts/relay_test.py --channel 2 --on 10   # relay 2 on for 10 s
   ```
   Meter on beep between the **S rail** and **j R** of that channel (j27 for channel 2): it beeps while the relay is
   on and goes silent when it turns off. With every relay off, no j R may beep to the S rail. Repeat for all 10.
4. Reboot the Pi and check that no j R beeps to the S rail during or after boot (fail open).

**Lesson from the build:** two resistor legs touching on channel 2 kept relay 2 on permanently, and the first belt
test failed until they were bent apart. The indicator LED looked normal the whole time. **A lit LED does not prove
the relay switches; only the meter test does.**

**Live (treadmill on, safety key in, nobody on the belt, hand on the safety key):**

5. Push the ribbon plug onto the HD6 header, pin 1 to pin 1. `relay_test.py` is safe here: it only ever closes one
   relay, which can't join two treadmill wires.
6. Press **speed up** (select 2 + 7, Go on 1). The belt starts at 1.0 mph. Then **speed down** (select 3 + 6):
   the console shows 0.9. Then **stop** (select 4 + 6). Use the app once it's installed
   ([setup-pi.md](../setup-pi.md)), or the probe script:
   ```bash
   python3 scripts/probe.py 2 7     # speed up
   python3 scripts/probe.py 3 6     # speed down
   python3 scripts/probe.py 4 6     # stop
   ```
   Speed up and speed down were confirmed through the relays on 2026-11-14.
7. If one tap doesn't give exactly one 0.1 mph step, adjust `press_ms` ([§8](#8-timing)).
8. Pull the safety key at any point if something's off.

---

## 8. Timing

All values are in `[timing]` in the config.

| Setting | Default | Meaning |
|---------|---------|---------|
| `settle_ms` | 50 | Select relays closed → wait → Go |
| `press_ms` | 300 | Go held for one tap |
| `max_press_ms` | 5000 | Longest Go hold allowed (manual presses from the troubleshooting panel) |
| `gap_ms` | 200 | Pause between consecutive commands |
| `max_relays_on` | 5 | Relays closed at once (GPIO current budget) |

Observed console behavior:

| Behavior | Value |
|----------|-------|
| Single Go tap (speed up/down) | ± **0.1 mph** |
| Holding Go | After about **1 s** the console auto-repeats, with bigger and faster steps |
| speed_up or start from stopped | Belt starts at **1.0 mph** |
| Minimum Go press that registers | Not measured (300 ms works) |

Keep `press_ms` **well under ~1 s** so a tap never turns into auto-repeat. "Go to 3.0 mph" uses the 3 mph preset
button (select 7 + 8), not counted taps. The app's speed is an estimate from counted presses; the console display is
the truth.

---

## 9. Discovery mode

The measurements narrowed the search: a button grounds a combination of lines 2–9, with Go on pin 1 (ground). Pins 1
and 10 are both ground, so they're never "selected". The scan covers:

- **Single lines:** 2 … 9 with Go. 8 tests.
- **Pairs of lines:** 28 pairs.

```bash
python3 scripts/probe.py --scan     # one combo at a time: Enter = press, s = skip, q = quit
python3 scripts/probe.py 4 5        # press one combo
python3 scripts/probe.py --list     # scan combos and the answers logged so far
```

After each press it asks *"what happened?"* (e.g. "incline up", "display changed to Programs", or Enter for
nothing; "r" presses again) and logs the answer to `docs/hardware/discovery-log.csv`, together with the console's
**state** ("stopped", "running", …). Probe asks for the state at the start, or takes `--state`. A button can be
refused in one state and work in another (an error beep), so the same combo can have an answer per state. A scan
skips combos already answered in the current state, so it can be stopped and resumed. Probe stops the treadmill app
while it runs (it needs the GPIO pins) and starts it again afterwards; that uses the optional passwordless sudo rule
from [setup-pi.md](../setup-pi.md). Anything found gets added to the button map and as a `[commands]` entry in the
config.

**Filling gaps.** `--unclear` keeps only combos with no clear answer yet: nothing logged, or only "nothing", a "?"
or a beep. Re-run those in each state, then try triples if a button is still missing. With `--between 4+6`, probe
presses Stop after every probe press (after you answer), so a combo that starts the belt doesn't leave the next combo
tested in the wrong state. `--redo` asks again for combos already answered in this state.

```bash
python3 scripts/probe.py --list --unclear                        # what's still open
python3 scripts/probe.py --scan --unclear --state stopped --between 4+6   # belt stopped, Stop after each
python3 scripts/probe.py --scan --unclear --state running --setup 2+7 --between 4+6   # start, wait 5 s, probe, Stop
python3 scripts/probe.py --scan --combos 4+9 5+9 --state stopped --between 4+6 --redo   # re-ask these
python3 scripts/probe.py --scan --triples --state stopped --between 4+6  # every three lines: 56 combos
```

**Safety for discovery:** combos can start the belt or move the incline. Nobody should stand on the belt, keep
the area under the deck clear for incline movement, and keep a hand on the safety key.

---

## 10. Power & mounting

- The Pi gets its **own** 5 V 2.5 A micro-USB supply. Never power it from the treadmill. A switched outlet strip can
  power both together.
- Mount the Pi and board in the console area, away from the motor bay (heat, belt dust).
- Keep the Pi's Wi-Fi corner away from the metal frame for better 2.4 GHz range.
- Breadboard wires can work loose from treadmill vibration. v1.0 is a breadboard build. For a permanent version,
  move it 1:1 onto a solderable full-size breadboard (e.g. Adafruit Perma-Proto full-size), which has the same rows,
  columns and rails. That version is suggested, not built or tested.
