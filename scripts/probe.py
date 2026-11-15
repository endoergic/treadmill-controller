#!/usr/bin/env python3
"""Discovery tool: press any combination of HD6 lines and log what the console did.

A console button grounds a combination of lines 2–9 (speed up = 2 + 7, speed down = 3 + 6). A probe press
does what a real command does: close the chosen lines' relays, then tap Go (pin 1).

On the Pi:
    python3 scripts/probe.py 4 5                           # one press: lines 4 + 5, then Go
    python3 scripts/probe.py --scan                        # every single line and pair of lines 2–9
    python3 scripts/probe.py --scan --unclear --state stopped --between 4+6   # gaps, stop (4+6) after each press
    python3 scripts/probe.py --scan --combos 3+7 4+9       # just these combos
    python3 scripts/probe.py --scan --triples              # every three lines together
    python3 scripts/probe.py --list [--unclear]            # combos and the answers logged so far

Each answer is logged to docs/hardware/discovery-log.csv with the console's state (e.g. "stopped" or "running",
asked at the start unless --state is given), because a button can be refused in one state and work in another.
--scan skips combos already answered in the current state, so it can be stopped (q or Ctrl+C) and resumed; --redo
asks again anyway (the new answer replaces the old one). --unclear keeps only combos with no clear answer yet:
nothing logged, or only "nothing", "?" or a beep. --setup presses a combo before every probe press (e.g. 2+7 to start
the belt for a "running" pass) and waits --setup-wait seconds. --between presses a reset combo after every probe
press (Stop is 4+6), so a combo that starts the belt doesn't change the state the next combo is tested in.
The treadmill service holds the GPIO pins, so probe stops it while it runs and starts it again afterwards (that
resets the app's speed estimate to 0).

On a laptop:    GPIOZERO_PIN_FACTORY=mock python3 scripts/probe.py --scan

Safety: unknown combos can start the belt or move the incline. Nobody on the belt, nothing under the deck,
hand on the safety key.
"""
import argparse
import asyncio
import csv
import dataclasses
import itertools
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from treadmill import config  # noqa: E402
from treadmill.config import Command, Config  # noqa: E402
from treadmill.relays import Relays  # noqa: E402

LOG = ROOT / "docs" / "hardware" / "discovery-log.csv"
FIELDS = ["time", "state", "select", "go", "press_ms", "result"]
OLD_STATE = "unknown"   # rows logged before the state column existed
SERVICE = "treadmill"


def label(select) -> str:
    return "+".join(str(p) for p in select)


def parse_combo(text: str) -> tuple[int, ...]:
    return tuple(sorted(int(p) for p in text.split("+")))


def is_unclear(result: str) -> bool:
    r = result.lower()
    return r in ("", "nothing") or "?" in r or "beep" in r


def scan_combos(cfg: Config, triples: bool = False) -> list[tuple[int, ...]]:
    """Single lines then pairs (or every triple) of the non-ground pins, minus combos already in the config."""
    lines = [p for p in sorted(cfg.gpio) if p not in cfg.ground]
    known = {tuple(sorted(c.select)) for c in cfg.commands.values()}
    if triples:
        combos = list(itertools.combinations(lines, 3))
    else:
        combos = [(p,) for p in lines] + list(itertools.combinations(lines, 2))
    return [c for c in combos if c not in known]


def read_log(path: Path) -> list[dict]:
    """All rows, oldest first. A log from before the state column is rewritten with state = "unknown"."""
    if not path.exists():
        return []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames or []
    if "state" not in header:
        for row in rows:
            row["state"] = OLD_STATE
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    return rows


def answers(rows: list[dict]) -> dict[str, dict[str, str]]:
    """select label -> {state: latest result}."""
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        out.setdefault(row["select"], {})[row["state"]] = row["result"]
    return out


def append_log(path: Path, state: str, select, go: int, press_ms: int, result: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "state": state, "select": label(select),
                    "go": go, "press_ms": press_ms, "result": result})


def probe_config(cfg: Config, select, go: int, press_ms: int) -> tuple[Config, Command]:
    grounded = [p for p in select if p in cfg.ground]
    if grounded:
        raise ValueError(f"pins {grounded} are console ground: closing them is the same as Go")
    cmd = Command("probe", tuple(select), go)
    probe_cfg = dataclasses.replace(cfg, press_ms=press_ms, commands={"probe": cmd})
    config.validate(probe_cfg)
    return probe_cfg, cmd


def selected_combos(args, cfg: Config, known: dict[str, dict[str, str]]) -> list[tuple[int, ...]]:
    combos = [parse_combo(c) for c in args.combos] if args.combos else scan_combos(cfg, args.triples)
    if args.unclear:
        combos = [c for c in combos if all(is_unclear(r) for r in known.get(label(c), {}).values())]
    return combos


def stop_service() -> bool:
    """Stop the web app if it's running. True if it was stopped (so it gets started again)."""
    if not shutil.which("systemctl"):
        return False
    if subprocess.run(["systemctl", "is-active", "--quiet", SERVICE]).returncode != 0:
        return False
    print("stopping the treadmill app while probing (it holds the GPIO pins)")
    if subprocess.run(["sudo", "-n", "systemctl", "stop", SERVICE]).returncode != 0:
        raise SystemExit("couldn't stop it: run  sudo systemctl stop treadmill  and try again")
    return True


def start_service() -> None:
    if subprocess.run(["sudo", "-n", "systemctl", "start", SERVICE]).returncode == 0:
        print("treadmill app started again (its speed estimate is back to 0)")
    else:
        print("couldn't start the app: run  sudo systemctl start treadmill")


def press_and_ask(args, driver, cmd: Command) -> None:
    """[--setup, wait] → press → ask what happened → [--between]. "r" repeats the whole sequence."""
    while True:
        if args.setup_cmd:
            asyncio.run(driver.press(args.setup_cmd))
            print(f"  sent {label(args.setup_cmd.select)} (--setup), waiting {args.setup_wait:g} s")
            time.sleep(args.setup_wait)
        asyncio.run(driver.press(cmd))
        logged = ask_and_log(args, cmd.select, cmd.go)
        if args.between_cmd:
            asyncio.run(driver.press(args.between_cmd))
            print(f"  sent {label(args.between_cmd.select)} (--between)")
        if logged:
            return


def ask_and_log(args, select, go: int) -> bool:
    """Ask what happened after a press. False means press again."""
    while True:
        result = input("  what happened? (Enter = nothing, r = press again) > ").strip()
        if result.lower() == "r":
            return False
        if result.lower() not in ("q", "s"):
            break
        print("  that's the answer for the press you just saw: describe it, or Enter for nothing")
    append_log(args.log, args.state, select, go, args.press_ms, result or "nothing")
    return True


def run_scan(args, cfg: Config, driver, go: int, combos) -> None:
    done = answers(read_log(args.log))
    todo = [c for c in combos if args.redo or args.state not in done.get(label(c), {})]
    if not todo:
        print(f"every selected combo already has an answer for state {args.state!r} in {args.log}")
        return
    print(f"{len(todo)} combos to go (state: {args.state}). Enter = press, s = skip, q = quit")
    for i, select in enumerate(todo, 1):
        _, cmd = probe_config(cfg, select, go, args.press_ms)
        before = done.get(label(select))
        hint = "  [so far: " + "; ".join(f"{s}: {r}" for s, r in before.items()) + "]" if before else ""
        while True:
            a = input(f"[{i}/{len(todo)}] lines {label(select)}, Go on {go}{hint} > ").strip().lower()
            if a == "q":
                return
            if a == "s":
                break
            if a == "":
                press_and_ask(args, driver, cmd)
                break
            print("  Enter = press, s = skip, q = quit")


def main() -> None:
    ap = argparse.ArgumentParser(description="Press any HD6 combination and log what the console did.")
    ap.add_argument("select", nargs="*", type=int, help="HD6 lines to join for one press, e.g. 4 5")
    ap.add_argument("--scan", action="store_true", help="walk the selected combos one by one")
    ap.add_argument("--list", action="store_true", help="show the selected combos and logged answers")
    ap.add_argument("--triples", action="store_true", help="scan every three lines instead of singles + pairs")
    ap.add_argument("--combos", nargs="+", metavar="A+B", help="scan only these combos, e.g. 3+7 4+9")
    ap.add_argument("--unclear", action="store_true", help="only combos with no clear answer yet")
    ap.add_argument("--state", help='console state for this session, e.g. "stopped" or "running" (asked if omitted)')
    ap.add_argument("--redo", action="store_true", help="--scan: ask again even if answered in this state")
    ap.add_argument("--setup", metavar="A+B", help="press this before every probe press, e.g. 2+7 (start the belt)")
    ap.add_argument("--setup-wait", type=float, default=5.0,
                    help="seconds between --setup and the probe press (default 5, time for the belt to get going)")
    ap.add_argument("--between", metavar="A+B", help="press this after every probe press, e.g. 4+6 (stop)")
    ap.add_argument("--go", type=int, help="Go pin (default: the first ground pin, 1)")
    ap.add_argument("--press-ms", type=int, help="how long Go is held (default: press_ms from the config)")
    ap.add_argument("--config", type=Path, default=config.default_config_path())
    ap.add_argument("--log", type=Path, default=LOG)
    args = ap.parse_args()
    if sum(map(bool, (args.select, args.scan, args.list))) != 1:
        ap.error("give HD6 lines to press, or --scan, or --list")
    if args.select and (args.combos or args.unclear or args.triples):
        ap.error("--combos, --unclear and --triples go with --scan or --list")

    cfg = config.load(args.config)
    go = args.go if args.go is not None else (cfg.ground[0] if cfg.ground else 1)
    args.press_ms = args.press_ms or cfg.press_ms
    known = answers(read_log(args.log))

    if args.list:
        for select in selected_combos(args, cfg, known):
            got = known.get(label(select), {})
            print(f"{label(select):>7}  " + ("; ".join(f"{s}: {r}" for s, r in got.items()) or "-"))
        return

    try:
        combos = [tuple(args.select)] if args.select else selected_combos(args, cfg, known)
        if not combos:
            raise SystemExit("no combos selected")
        for select in combos:
            probe_config(cfg, select, go, args.press_ms)
        args.setup_cmd, args.between_cmd = (
            probe_config(cfg, parse_combo(c), go, args.press_ms)[1] if c else None
            for c in (args.setup, args.between))
    except ValueError as e:
        ap.error(str(e))

    print("Nobody on the belt, nothing under the deck, hand on the safety key.")
    try:
        while not args.state:
            args.state = input('console state for this session (e.g. "stopped", "running") > ').strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return
    restart = stop_service()
    probe_cfg, cmd = probe_config(cfg, combos[0], go, args.press_ms)
    driver = Relays(probe_cfg)
    try:
        if args.scan:
            run_scan(args, cfg, driver, go, combos)
        else:
            input(f"lines {label(cmd.select)}, Go on {go}, {args.press_ms} ms. Enter = press, Ctrl+C = cancel > ")
            press_and_ask(args, driver, cmd)
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        driver.close()
        print("all relays off")
        if restart:
            start_service()


if __name__ == "__main__":
    main()
