"""Load and validate config/treadmill.toml (falls back to the example file)."""
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "treadmill.toml"
EXAMPLE_CONFIG = ROOT / "config" / "treadmill.example.toml"


def default_config_path() -> Path:
    return DEFAULT_CONFIG if DEFAULT_CONFIG.exists() else EXAMPLE_CONFIG


@dataclass(frozen=True)
class Command:
    name: str
    select: tuple[int, ...]
    go: int
    sets_speed: float | None = None   # presets: the speed the console jumps to (for the estimate)


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    pin: str
    ground: tuple[int, ...]       # HD6 pins that are console ground (Go side); never used as select lines
    gpio: dict[int, int]          # HD6 pin -> BCM GPIO
    settle_ms: int
    press_ms: int
    max_press_ms: int
    gap_ms: int
    max_relays_on: int
    max_speed: float
    max_commands_per_sec: float
    unit: str
    step: float
    start_speed: float
    commands: dict[str, Command]


def load(path: Path) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    hd6 = raw["hd6"]
    gpio = {int(pin): int(bcm) for pin, bcm in hd6["gpio"].items()}
    timing, safety, speed = raw["timing"], raw["safety"], raw["speed"]
    commands = {
        name: Command(name, tuple(int(p) for p in c["select"]), int(c["go"]),
                      float(c["sets_speed"]) if "sets_speed" in c else None)
        for name, c in raw.get("commands", {}).items()
    }
    cfg = Config(
        host=raw["server"]["host"],
        port=int(raw["server"]["port"]),
        pin=str(raw["server"].get("pin", "")),
        ground=tuple(int(p) for p in hd6.get("ground", [])),
        gpio=gpio,
        settle_ms=int(timing["settle_ms"]),
        press_ms=int(timing["press_ms"]),
        max_press_ms=int(timing["max_press_ms"]),
        gap_ms=int(timing["gap_ms"]),
        max_relays_on=int(timing["max_relays_on"]),
        max_speed=float(safety["max_speed"]),
        max_commands_per_sec=float(safety["max_commands_per_sec"]),
        unit=speed["unit"],
        step=float(speed["step"]),
        start_speed=float(speed["start_speed"]),
        commands=commands,
    )
    validate(cfg)
    return cfg


def validate(cfg: Config) -> None:
    if len(set(cfg.gpio.values())) != len(cfg.gpio):
        raise ValueError("[hd6.gpio]: two HD6 pins share one GPIO")
    if cfg.press_ms > cfg.max_press_ms:
        raise ValueError("[timing] press_ms must not exceed max_press_ms")
    for c in cfg.commands.values():
        grounded = [p for p in c.select if p in cfg.ground]
        if grounded:
            raise ValueError(f"[commands.{c.name}] select includes ground pins {grounded} (that's the same as Go)")
        pins = (*c.select, c.go)
        unknown = [p for p in pins if p not in cfg.gpio]
        if unknown:
            raise ValueError(f"[commands.{c.name}] uses HD6 pins with no GPIO: {unknown}")
        if c.go in c.select:
            raise ValueError(f"[commands.{c.name}] go pin is also in select")
        if len(set(pins)) > cfg.max_relays_on:
            raise ValueError(f"[commands.{c.name}] closes {len(set(pins))} relays; max_relays_on is {cfg.max_relays_on}")
        if c.sets_speed is not None and c.sets_speed <= 0:
            raise ValueError(f"[commands.{c.name}] sets_speed must be above 0 (stop is its own command)")
