#!/usr/bin/env python3
"""Relay light show: turns each relay on, one at a time, so you can see its LED light
(or hear the multimeter beep across its switch side).

Only one relay is ever on at once, so no two HD6 pins are ever joined. That makes it
safe to run with the treadmill connected.

On the Pi:      python3 scripts/relay_test.py [--channel N] [--rounds N] [--on SECONDS]
On a laptop:    GPIOZERO_PIN_FACTORY=mock python3 scripts/relay_test.py
"""
import argparse
import time
import tomllib
from pathlib import Path

from gpiozero import DigitalOutputDevice

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "treadmill.toml"
EXAMPLE_CONFIG = ROOT / "config" / "treadmill.example.toml"


def load_gpio_map(path):
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    return {int(pin): gpio for pin, gpio in sorted(cfg["hd6"]["gpio"].items(), key=lambda kv: int(kv[0]))}


def main():
    ap = argparse.ArgumentParser(description="Turn each relay on one at a time.")
    ap.add_argument("--config", type=Path,
                    default=DEFAULT_CONFIG if DEFAULT_CONFIG.exists() else EXAMPLE_CONFIG)
    ap.add_argument("--channel", type=int, help="only test this HD6 pin / channel (1-10)")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--on", type=float, default=0.5, help="seconds each relay stays on")
    args = ap.parse_args()

    gpio_map = load_gpio_map(args.config)
    if args.channel is not None:
        if args.channel not in gpio_map:
            ap.error(f"channel must be one of {sorted(gpio_map)}")
        gpio_map = {args.channel: gpio_map[args.channel]}

    relays = {ch: DigitalOutputDevice(gpio, initial_value=False) for ch, gpio in gpio_map.items()}
    try:
        for _ in range(args.rounds):
            for ch, relay in relays.items():
                print(f"relay {ch:2d}  (GPIO{gpio_map[ch]:<2d})  ON", flush=True)
                relay.on()
                time.sleep(args.on)
                relay.off()
                time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        for relay in relays.values():
            relay.off()
            relay.close()
    print("all relays off")


if __name__ == "__main__":
    main()
