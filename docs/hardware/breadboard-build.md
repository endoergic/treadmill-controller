# Breadboard Build (kid-friendly)

A build you can do **together with kids**: the grown-up solders one header, and everything else
plugs in. The picture to follow is **[`hardware/breadboard-layout.svg`](../../hardware/breadboard-layout.svg)**
(open it in a browser and print it).

Same circuit as the [rewiring guide](rewiring-guide.md) (schematic: [`hardware/schematic.svg`](../../hardware/schematic.svg)),
laid out for a breadboard, plus a light on every channel so you can *see* each relay turn on.

When you get to the parts that need the Pi's software, set up the Pi with **[setup-pi.md](../setup-pi.md)**.

> 🧑 **Grown-up steps** are marked 🧑. Everything else is fine for kids, because the breadboard only ever sees
> 3.3 V from the Pi and the treadmill's own 3.4 V keypad signal. Kids never open the treadmill.

---

## How it works (the 1-minute version for kids)

- Each black chip is a **relay**: a switch with a tiny light inside. When the Pi turns the light on, the switch closes.
- The light side and the switch side **never touch**. That's what keeps the Pi and the treadmill safe from each other.
- On the breadboard, the chips sit across the **canyon** (the groove down the middle):
  - **Left of the canyon = Pi land** (yellow and black wires, resistors, red lights)
  - **Right of the canyon = treadmill land** (green wires and the ribbon wires only)
  - **The rule: nothing ever crosses the canyon except the chips.**
- To make the treadmill speed up, the Pi closes relays **2 and 7**, then taps relay **1** ("Go"). It's the same thing as flipping the old switches.

---

## Shopping list

Everything to buy is in **[shopping-list.md](shopping-list.md)**. There's a printable version with checkboxes at
[`hardware/shopping-list.html`](../../hardware/shopping-list.html).

**Not needed:** 10 kΩ pull-down resistors. The Pi's own built-in pull-downs keep these GPIOs off at boot, and a
relay needs a few mA to turn on, which a floating pin can't supply.

---

## Wire colors (the whole board uses only these)

| Color | Means | Lives in |
|-------|-------|----------|
| 🟡 Yellow | Pi GPIO signal | Pi land |
| ⚫ Black | Ground (− rail) | Pi land |
| 🟢 Green | Shared line (S rail) | Treadmill land |
| 🟠 Ribbon | Wire from the treadmill's HD6 plug | Treadmill land |

---

## Build steps

### Step 0: 🧑 Solder the Pi header
Solder the 2×20 header onto the Pi Zero (long pins up). That's the only soldering.

### Step 1: Label the rails
- Left side: tape **"− GND"** on the rail **next to column a**. Tape **"NOT USED"** on the outer left rail.
- Right side: tape **"S — SHARED (treadmill only)"** on the rail **next to column j**. Tape **"NOT USED"** on the outer right rail.

> Breadboards differ in which rail is printed red or blue. Ignore the printing and use the labels you just stuck on.

### Step 2: Cobbler
Plug the T-Cobbler into **rows 1–20**, straddling the canyon. Connect the ribbon to it, but **don't plug the Pi in yet**.
Add one ⚫ black wire from **GND (row 20, pin 39)** to the **− rail**.

### Step 3: Relays, one channel at a time
Each channel uses 4 rows. Channel *n* starts at row **R = 23 + 4 × (n − 1)**:

| Channel | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---------|---|---|---|---|---|---|---|---|---|----|
| Start row R | 23 | 27 | 31 | 35 | 39 | 43 | 47 | 51 | 55 | 59 |

For each channel (look at the picture):

| # | Part | From | To | Kid tip |
|---|------|------|----|---------|
| 1 | Relay chip | **e R** (dot here) | **f R+1** | **Dot goes top-left**, every time |
| 2 | ⚫ black wire | a R+1 | − rail | Relay light's ground |
| 3 | 330 Ω (orange-orange-brown) | b R | b R+2 | Hops over a row |
| 4 | 1 kΩ (brown-black-red) | c R+2 | c R+3 | |
| 5 | LED | **long leg in a R+3** | short leg in − rail | Long leg = + |
| 6 | 🟡 yellow wire | cobbler GPIO (table below) | d R+2 | Check the cobbler's printed label |
| 7 | 🟢 green wire | j R+1 | S rail | Treadmill land |

Finish channel 1 completely, run [Step 5](#step-5-light-show-test-no-treadmill) for that channel, and then do the rest.
Kids get to see it work early.

> **Relays not here yet?** You can place the 1 kΩ (#4), the LED (#5) and the yellow wire (#6) for every channel,
> plus the GND wire from Step 2, before the chips arrive. The LED has its own path (GPIO → 1 kΩ → LED → −) that
> doesn't go through the relay, so [`scripts/relay_test.py`](#step-5-light-show-test-no-treadmill) already lights
> the LEDs. When the relays arrive, add #1, #2, #3 and #7 for each channel, then run the canyon check (Step 4).
> Nothing that's already placed moves. Use red, yellow or green LEDs: through 1 kΩ at 3.3 V, blue and white LEDs are
> barely visible.

**Yellow wire table** (check against the cobbler's printed labels: if they disagree, **the labels win**):

| Channel | GPIO | Pi pin | Cobbler row/side | Lands in |
|---------|------|--------|------------------|----------|
| 1 (Go) | GPIO17 | 11 | 6 left | d25 |
| 2 | GPIO27 | 13 | 7 left | d29 |
| 3 | GPIO22 | 15 | 8 left | d33 |
| 4 | GPIO23 | 16 | 8 right | d37 |
| 5 | GPIO24 | 18 | 9 right | d41 |
| 6 | GPIO25 | 22 | 11 right | d45 |
| 7 | GPIO16 | 36 | 18 right | d49 |
| 8 | GPIO26 | 37 | 19 left | d53 |
| 9 | GPIO12 | 32 | 16 right | d57 |
| 10 | GPIO13 | 33 | 17 left | d61 |

Yellow wires from the right side of the cobbler cross over to the left. That's fine because they're still Pi wires,
and the canyon rule is about the relay area (rows 23–62).

### Step 4: Canyon check (kid job, with the multimeter)
Pi unplugged. Multimeter on **beep**. One probe on the **− rail**, then touch the other probe to:
- the **S rail** → must be **silent**
- every hole in **column j, rows 23–62** → must be **silent**

Any beep means something crosses the canyon. Find it before going on.

### Step 5: Light show test (no treadmill)
Plug the ribbon into the Pi and power it up. The Pi needs its software first: follow
[setup-pi.md](../setup-pi.md) up to the point where the repo is on the Pi. If the treadmill app is already
running, stop it first, because it holds the GPIO pins: `sudo systemctl stop treadmill`. Then, in the repo folder
on the Pi:

```bash
python3 scripts/relay_test.py              # all 10, one at a time
python3 scripts/relay_test.py --channel 1  # just one
```

Each red LED should light **in order, 1 → 10**.

**Now prove the *switch* side works too**, because a lit LED only shows the Pi's signal arrived. Hold one relay on
for 10 seconds:

```bash
python3 scripts/relay_test.py --channel 2 --on 10
```

Put the multimeter (beep) between the **S rail** and **j R** of that channel (j27 for channel 2). It beeps only
while that channel's relay is on. Do it for every channel. If a channel beeps even when its LED is off, see
[Troubleshooting](#troubleshooting).

The test only ever turns on **one relay at a time**, which can never join two treadmill wires, so it's
also safe to run with the treadmill connected.

Done? Start the app again with `sudo systemctl start treadmill`.

### Step 6: 🧑 Put a header on HD6 (one-time grown-up job)
The old HD6 socket (white, with a latch, probably JST XH 2.5 mm) is half-melted, so it gets replaced by a plain
**2.54 mm 1×10 male header**. It fits the old 2.5 mm holes: over 10 pins the spacing is only off by about 0.2 mm at each end.

Treadmill **unplugged from the wall**, console board out if you can get it out.
1. **Mark pin 1 first.** Photograph the socket with your wires in it, and put a paint-marker dot next to the **Black** wire's hole. Once the socket is gone, all 10 holes look the same. Pin 1 is often the square pad.
2. **Clip off the plastic shell** with flush cutters so only bare pins are left.
3. **Desolder one pin at a time.** Add a little fresh leaded solder and flux first (old solder flows badly), then use the pump or wick. Go gently, because old, reworked pads lift easily.
4. **Check the pads.** If one has lifted, run a short wire from the new header pin to where that trace goes.
5. **Fit the header** (short side through the board, long pins up). Solder one end pin, check it's square, then solder the rest.
6. **Look for solder bridges** under good light. Then put a dot next to pin 1 on the board again.

This replaces the old switch box: its wires came off with the socket.

### Step 7: Plug in the treadmill (kid job)
1. **Make the plug:** pull the 10 female ends out of their single housings (lift the little plastic tab) and push them, in order, into a **1×10 Dupont housing**. Put a dot on the housing at wire 1.
2. **Push the plug onto the HD6 header, dot to dot.**
3. Plug the 10 **male** ends into the breadboard: wire *n* goes in **i R** of channel *n* (i23, i27, i31 … i59).

> ⚠️ Go by position, not by matching colors to old notes. On this ribbon, **black is pin 1** (at the dot) and the rest
> follow rainbow order to **brown at pin 10** ([button-map.md](button-map.md)). Its *red* is pin 9 and its *blue* is pin 5,
> not the old Red/Blue switch-box wires.

### Step 8: 🧑 First real test
Treadmill on, **nobody on the belt**, hand on the safety key. The app must be installed and running
([setup-pi.md](../setup-pi.md)). Open **http://treadmill.local** on a phone and tap **speed up**. Watch LEDs 2 + 7
light, then 1 blink ("Go"). The belt should start at 1.0 mph. Tap **speed down**: the console should show 0.9. Then
tap **stop**.

Belt didn't move but the LEDs lit? Do the meter test from [Step 5](#step-5-light-show-test-no-treadmill) on
channels 1, 2 and 7. On our build, two resistor legs touching on channel 2 were the problem.

---

## Making it permanent (later)

Breadboard wires can wiggle loose from treadmill vibration. Once it all works, move it 1:1 onto a
**solderable breadboard** (e.g. Adafruit Perma-Proto full-size). It has the same rows, columns and rails, so the same
picture works. That's grown-up soldering, but kids can place the parts first and you solder them in.

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| LED doesn't light | LED backwards (long leg goes in a R+3), or the yellow wire is on the wrong cobbler pin |
| LED lights but the meter doesn't beep on the switch side | Relay chip backwards (dot not top-left) or not seated across the canyon |
| Every LED is dim or none light | Black GND wire from cobbler row 20 to the − rail is missing |
| Two LEDs light at once in the light show | Two yellow wires swapped or touching |
| Beep in the canyon check | A wire or resistor leg from Pi land reaching the S rail or column f–j |
| One relay is always on (meter beeps from S rail to that channel's j R even with its LED off) | Two resistor legs touching on that channel (b and c columns sit side by side). Bend them apart. Found on channel 2 on 2026-11-14 |
