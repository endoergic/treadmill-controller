"""Command queue, estimated speed, and safety limits.

One worker presses jobs one at a time, so two phones can never produce
overlapping half-presses. STOP (if mapped) clears the queue and runs next.
Speed is open-loop: counted presses, so it is an estimate.

Jobs are config commands (by name) or manual presses from the troubleshooting
panel (any select lines + Go pin + hold time). Manual presses don't change the
speed estimate: their effect on the console is unknown.
"""
import asyncio
import dataclasses
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from . import config
from .config import Command, Config
from .relays import Relays

Listener = Callable[[dict], Awaitable[None]]
log = logging.getLogger("treadmill")


class Rejected(Exception):
    """A command the controller refused (limit hit, unknown name)."""


@dataclass(frozen=True)
class Job:
    name: str                    # config command name, or "manual …" for the troubleshooting panel
    cmd: Command
    press_ms: int | None = None  # None = [timing] press_ms
    manual: bool = False


class Controller:
    def __init__(self, cfg: Config, relays: Relays):
        self._cfg = cfg
        self._relays = relays
        self._queue: deque[Job] = deque()
        self._wake = asyncio.Event()
        self._recent: deque[float] = deque()  # submit times, for the rate limit
        self._listeners: set[Listener] = set()
        self._worker: asyncio.Task | None = None
        self._generation = 0  # bumped by reset_speed so an in-flight tap can't overwrite the reset
        self.speed = 0.0
        self.busy: str | None = None
        self._busy_job: Job | None = None

    # ---- lifecycle -------------------------------------------------------

    def start(self) -> None:
        self._worker = asyncio.create_task(self._run())

    async def stop_worker(self) -> None:
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
        self._relays.release_all()

    # ---- listeners -------------------------------------------------------

    def subscribe(self, listener: Listener) -> None:
        self._listeners.add(listener)

    def unsubscribe(self, listener: Listener) -> None:
        self._listeners.discard(listener)

    def state(self) -> dict:
        cfg = self._cfg
        return {
            "type": "state",
            "speed": round(self.speed, 1),
            "unit": cfg.unit,
            "max_speed": cfg.max_speed,
            "busy": self.busy,
            "queued": [job.name for job in self._queue],
            "commands": list(cfg.commands),
            "presets": {c.name: c.sets_speed for c in cfg.commands.values() if c.sets_speed is not None},
            "clients": len(self._listeners),
            "manual": {
                "pins": sorted(cfg.gpio),
                "ground": list(cfg.ground),
                "press_ms": cfg.press_ms,
                "max_press_ms": cfg.max_press_ms,
                "max_relays_on": cfg.max_relays_on,
            },
        }

    async def broadcast(self) -> None:
        msg = self.state()
        await asyncio.gather(*(send(msg) for send in list(self._listeners)), return_exceptions=True)

    # ---- commands --------------------------------------------------------

    def submit(self, name: str) -> None:
        if name not in self._cfg.commands:
            raise Rejected(f"unknown command: {name}")
        job = Job(name, self._cfg.commands[name])

        if name == "stop":
            # Safety: never rate-limited, jumps the queue, drops everything pending.
            self._queue.clear()
            self._queue.append(job)
            self._wake.set()
            return

        self._rate_limit()
        if self._projected_speed(extra=job) > self._cfg.max_speed + 1e-9:
            raise Rejected(f"max speed is {self._cfg.max_speed:g} {self._cfg.unit}")
        self._enqueue(job)

    def submit_manual(self, select: list[int], go: int, press_ms: int) -> None:
        """Troubleshooting: press any lines + Go, held for press_ms. Same checks as a config command."""
        cfg = self._cfg
        select = tuple(sorted(set(select)))
        grounded = [p for p in select if p in cfg.ground]
        if grounded:
            raise Rejected(f"pins {grounded} are ground: selecting them is the same as Go")
        if not 0 < press_ms <= cfg.max_press_ms:
            raise Rejected(f"hold time must be 1–{cfg.max_press_ms} ms")
        cmd = Command("manual", select, go)
        try:
            config.validate(dataclasses.replace(cfg, commands={"manual": cmd}))
        except ValueError as e:
            raise Rejected(str(e).replace("[commands.manual] ", "")) from None
        self._rate_limit()
        lines = "+".join(map(str, select)) or "none"
        self._enqueue(Job(f"manual {lines}, Go {go}, {press_ms} ms", cmd, press_ms, manual=True))

    def reset_speed(self) -> None:
        """User says the belt is stopped (e.g. safety key pulled): zero the estimate, drop pending taps."""
        self._queue.clear()
        self._generation += 1
        self.speed = 0.0

    def _rate_limit(self) -> None:
        now = time.monotonic()
        while self._recent and now - self._recent[0] >= 1.0:
            self._recent.popleft()
        if len(self._recent) >= self._cfg.max_commands_per_sec:
            raise Rejected("too many taps, slow down")

    def _enqueue(self, job: Job) -> None:
        self._recent.append(time.monotonic())
        self._queue.append(job)
        self._wake.set()

    def _apply(self, speed: float, job: Job) -> float:
        if job.manual:
            return speed
        if job.cmd.sets_speed is not None:
            return job.cmd.sets_speed
        name = job.name
        if name == "speed_up":
            return self._cfg.start_speed if speed <= 0 else speed + self._cfg.step
        if name == "speed_down":
            return max(0.0, speed - self._cfg.step)
        if name == "start":
            return self._cfg.start_speed if speed <= 0 else speed  # refused (beep) while running
        if name == "stop":
            return 0.0
        return speed

    def _projected_speed(self, extra: Job) -> float:
        speed = self.speed
        for job in ([self._busy_job] if self.busy else []) + list(self._queue) + [extra]:
            speed = self._apply(speed, job)
        return speed

    # ---- worker ----------------------------------------------------------

    async def _run(self) -> None:
        while True:
            if not self._queue:
                self._wake.clear()
                await self._wake.wait()
                continue
            job = self._queue.popleft()
            self._busy_job, self.busy = job, job.name
            generation = self._generation
            if job.manual:
                log.info("%s", job.name)
            await self.broadcast()
            try:
                await self._relays.press(job.cmd, job.press_ms)
                if generation == self._generation:
                    self.speed = self._apply(self.speed, job)
            finally:
                self.busy = None
            await self.broadcast()
            await asyncio.sleep(self._cfg.gap_ms / 1000)
