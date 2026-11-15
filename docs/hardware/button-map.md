# Button Map

Reference for the console's keypad connector: pinout, measurements and every confirmed command. The commands in
`config/treadmill.example.toml` match this page.

- Treadmill: **NordicTrack C2100** (model NTL1085), Solaris console
- Motor controller: **MC-2100WA**
- Factory diagram: [`hardware/schematics/IMG_2176.jpeg`](../../hardware/schematics/IMG_2176.jpeg) (Icon drawing #214876, 8/2004)
- Old switch-box wiring (hand drawn, historical): [`hardware/schematics/IMG_2175.jpeg`](../../hardware/schematics/IMG_2175.jpeg)
- Relay board schematic: [`hardware/schematic.svg`](../../hardware/schematic.svg)
- Keypad and build photos: [`hardware/photos/`](../../hardware/photos/)

## Keypad connector HD6 (10 pins, on the console)

The original socket was half-melted. It was replaced with a 2.54 mm 1×10 male header and a rainbow ribbon plug
(1×10 Dupont housing). Pin 1 is the hole the old switch box's Black wire used. Relay channel *n* drives HD6 pin *n*.

| HD6 pin | Ribbon color | Role | BCM GPIO (Pi pin) |
|---------|--------------|------|-------------------|
| 1 | black | **Ground**, used as **Go** (0 V to pin 10; 111 Ω to earth) | GPIO17 (11) |
| 2 | white | Signal line, idles at 3.4 V | GPIO27 (13) |
| 3 | grey | Signal line, idles at 3.4 V | GPIO22 (15) |
| 4 | purple | Signal line, idles at 3.4 V | GPIO23 (16) |
| 5 | blue | Signal line, idles at 3.4 V | GPIO24 (18) |
| 6 | green | Signal line, idles at 3.4 V | GPIO25 (22) |
| 7 | yellow | Signal line, idles at 3.4 V | GPIO16 (36) |
| 8 | orange | Signal line, idles at 3.4 V | GPIO26 (37) |
| 9 | red | Signal line, idles at 3.4 V | GPIO12 (32) |
| 10 | brown | **Ground** (0 V to pin 1; 111 Ω to earth) | GPIO13 (33) |

The ribbon's *red* is pin 9 and its *blue* is pin 5. They are not the old switch box's Red/Blue wires.

## How the keypad works

Pins 2–9 are eight lines the console holds at 3.4 V. A button grounds a **combination** of them (speed up = 2 + 7).
The relay board does this in two steps: the select relays join their lines to the board's shared line, then the Go
relay joins the shared line to pin 1 (ground). Go is required: closing the select lines alone does nothing.

Press sequence: close select relays → wait 50 ms (`settle_ms`) → close Go for 300 ms (`press_ms`) → release Go →
release all. One tap = ± 0.1 mph. Holding Go longer than about 1 s makes the console auto-repeat.

Details: [rewiring guide](rewiring-guide.md).

## Measurements

| Date | Condition | Measurement | Result |
|------|-----------|-------------|--------|
| 2026-11-08 | Unplugged | Every ribbon wire → plug ground prong | Pins 1 and 10: **111 Ω**. Pins 2–9: OL |
| 2026-11-08 | Unplugged | Every ribbon wire → both flat prongs (live, neutral) | All OL: no path to mains |
| 2026-11-08 | Powered, key in | DC volts, pins 2–9 vs pin 1 (and vs pin 10) | All **+3.4 V**, steady. No AC |
| 2026-11-08 | Powered, key in | Pin 1 ↔ pin 10 | 0 V: both ground |

So HD6 is 3.3 V logic, a button grounds a combination of lines 2–9, and Go = pin 1 (ground).

## Commands

All confirmed on the belt on 2026-11-14, each a tap of Go on pin 1.

| Command | Select lines | Ribbon wires (select + Go) | Notes |
|---------|--------------|----------------------------|-------|
| speed_up | 2 + 7 | white + yellow, then black | +0.1 mph. From stopped, starts the belt at 1.0 mph |
| speed_down | 3 + 6 | grey + green, then black | −0.1 mph |
| start | 3 + 7 | grey + yellow, then black | Starts at 1.0 mph when stopped; error beep while running |
| stop | 4 + 6 | purple + green, then black | |
| incline_up | 4 + 7 | purple + yellow, then black | |
| incline_down | 5 + 6 | blue + green, then black | |
| 1 mph | 3 + 9 | grey + red, then black | Preset |
| 2 mph | 2 + 9 | white + red, then black | Preset |
| 3 mph | 7 + 8 | yellow + orange, then black | Preset |
| 4 mph | 6 + 8 | green + orange, then black | Preset |
| 5 mph | 5 + 8 | blue + orange, then black | Preset |
| 6 mph | 4 + 8 | purple + orange, then black | Preset |
| 7 mph | 3 + 8 | grey + orange, then black | Preset |
| 8 mph | 2 + 8 | white + orange, then black | Preset |
| 9 mph | 6 + 7 | green + yellow, then black | Preset |
| 10 mph | 5 + 7 | blue + yellow, then black | Preset |
| fan | 8 + 9 | orange + red, then black | |
| programs | 6 + 9 | green + red, then black | |
| odometer | 7 + 9 | yellow + red, then black | |

In the config, presets are `speed_1` … `speed_10` with `sets_speed`. The app refuses presets above `max_speed`
(6.0 by default).

### Keypad grid

Every pair of lines 2–9, each followed by Go on pin 1:

| Lines | 6 | 7 | 8 | 9 |
|-------|---|---|---|---|
| **2** | nothing | speed up | 8 mph | 2 mph |
| **3** | speed down | start | 7 mph | 1 mph |
| **4** | stop | incline up | 6 mph | error beep |
| **5** | incline down | 10 mph | 5 mph | error beep |
| **6** | – | 9 mph | 4 mph | programs |
| **7** | | – | 3 mph | odometer |
| **8** | | | – | fan |

Nothing happens for any single line, or for any two of lines 2–5 together (2+3, 2+4, 2+5, 3+4, 3+5, 4+5).

### Not identified

| Combo | Result | Notes |
|-------|--------|-------|
| 4 + 9 | Error beep in every state | Likely Heart Rate ▲ or ▼, which needs a heart-rate sensor |
| 5 + 9 | Error beep in every state | Likely Heart Rate ▲ or ▼, which needs a heart-rate sensor |
| 2 + 6 | Nothing | |
| Single line 6 | Once, while running: "beep, slows, back to 1.0" | Unexplained, not re-tested |

## Console keypad (from photos)

1–10 mph "1StepSpeed" presets · Incline ▲▼ · Start · Stop · Speed ▲▼ ·
AutoBreeze Fans · Odometer · Programs · Heart Rate ▲▼ · "Interactive In" (iFit audio) jack

## Behavior

| Question | Answer |
|----------|--------|
| Speed step per press | 0.1 mph per single tap |
| Speed after speed_up or start from stopped | **1.0 mph**. Each tap after that: ± 0.1 mph (1.0 → speed_down → 0.9) |
| Does holding Go auto-repeat? | Yes: after ~1 s it repeats on its own with larger/faster steps |
| Min / max speed | Not measured (the presets go to 10 mph) |
| Minimum Go press duration that registers | Not measured (300 ms works; must stay under ~1 s) |
| What happens when the safety key is pulled and reinserted | Not measured |

## Discovery log

Raw probe answers: [`discovery-log.csv`](discovery-log.csv) (columns: time, state, select, go, press_ms, result).
Written by `scripts/probe.py` ([rewiring guide §9](rewiring-guide.md#9-discovery-mode)). Read it with care:

- Rows with state `unknown` are from the first scan.
- In the first `running` pass the belt never ran, so those rows were not taken with the belt moving.
- In the second `running` pass, the answer "start" means the belt started from probe's own `--setup` press, not
  from the combo being tested.

The tables above are the interpreted result.

## Old manual circuit (removed with the socket)

Before the relay board, a household switch box was wired across HD6 (hand drawing:
[`IMG_2175.jpeg`](../../hardware/schematics/IMG_2175.jpeg)). It came off with the melted socket.

```
Black ──[SW0 "Go", momentary]──┬──[SW1]── Red 1
                               ├──[SW2]── Blue 2
                               └──[SW3]── Red 2 + Blue 1 (tied)
```

Set SW1–SW3 (on/off toggles), then tap **Go**. Go is required: closing everything at once doesn't work.

| Command | SW1 | SW2 | SW3 | Wires tied together | HD6 pins |
|---------|-----|-----|-----|---------------------|----------|
| speed_up / start | on | on | off | Black + Red 1 + Blue 2 | 1 + 2 + 7 |
| speed_down | off | off | on | Black + Red 2 + Blue 1 | 1 + 3 + 6 |

Old wire → HD6 pin: Black = 1, Red 1 = 2, Red 2 = 3, Blue 1 = 6, Blue 2 = 7. The Red 2 ↔ Blue 1 jumper isn't
needed: speed down works with 3 + 6 joined only during the press.
