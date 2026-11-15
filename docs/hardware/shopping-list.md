# Shopping List (v1.0 bill of materials)

Everything for the v1.0 build: the 10-relay breadboard from [breadboard-build.md](breadboard-build.md), wired as in
[`hardware/schematic.svg`](../../hardware/schematic.svg). Printable version with checkboxes:
[`hardware/shopping-list.html`](../../hardware/shopping-list.html).

**One cart:** DigiKey or Mouser stock all of the core parts, Adafruit items included. Prices are estimates
(Oct 2026) and will drift.

## Core parts

| ✓ | Qty | Item | Part # / example | ≈ Price |
|---|-----|------|------------------|---------|
| ☐ | 12 | PhotoMOS relay, DIP-4 (10 + 2 spares) | **Panasonic AQY212EH** (alt: Toshiba TLP240A). *Not* TLP222A, which is end-of-life. | $20 |
| ☐ | 1 | 40-pin T-type GPIO breakout with ribbon cable | Adafruit T-Cobbler Plus **#2028**, or any generic "GPIO Extension Board" T-board (our build used a generic one; wire by its printed labels) | $5–8 |
| ☐ | 1 | Full-size breadboard, 830 points, **63 rows** | BusBoard BB830 or Adafruit full-size | $6–9 |
| ☐ | 1 | 2×20 male header, 2.54 mm, for the Pi Zero | any (no-solder alt: GPIO "hammer header" kit) | $1–6 |
| ☐ | 15 | 330 Ω resistor, ¼ W (orange-orange-brown) | Stackpole CF14JT330R | $1 |
| ☐ | 15 | 1 kΩ resistor, ¼ W (brown-black-red) | Stackpole CF14JT1K00 | $1 |
| ☐ | 15 | LED, 5 mm diffused, red (yellow or green also fine) | any. Blue and white are barely visible through 1 kΩ at 3.3 V | $2–4 |
| ☐ | 1 | Pre-cut flat jumper wire kit, color-coded | ~140-piece U-shaped kit | $6–8 |
| ☐ | 1 | Dupont ribbon, **female → male**, 20 cm | 40-wire strip, peel off 10 | $4–6 |

## HD6 header swap (replaces the melted socket)

| ✓ | Qty | Item | Notes | ≈ Price |
|---|-----|------|-------|---------|
| ☐ | 1 | 1×40 male header strip, 2.54 mm | Break off 10. Spares are handy. | $1 |
| ☐ | 1 | 1×10 Dupont housing | Often sold as a 1×1 to 1×10 assortment | $3–6 |
| ☐ | 1 | Desoldering pump and/or solder wick | | $5–8 |
| ☐ | 1 | Flux pen | | $5 |
| ☐ | 1 | Paint marker or nail polish | Pin-1 dots on the board and plug | – |

## Only if you don't already have one

| ✓ | Item | ≈ Price |
|---|------|---------|
| ☐ | Micro-USB power supply, 5 V 2.5 A (official Raspberry Pi supply recommended) | $8 |
| ☐ | microSD card, 16–32 GB | $8 |
| ☐ | Multimeter with continuity beeper | $15–25 |
| ☐ | Masking tape + marker (rail labels) | – |
| ☐ | Soldering iron, leaded solder | – |

## Later: permanent build (optional, not part of v1.0)

A soldered version is suggested but has not been built or tested.

| ✓ | Item | ≈ Price |
|---|------|---------|
| ☐ | Full-size solderable breadboard with the same layout (Adafruit Perma-Proto full-size) | $8 |
| ☐ | Small project box | $10 |

**Estimated total:** core parts plus the header swap come to about **$65–85**.

Small parts are rounded up to 15 because things get lost, especially with kid builders.
