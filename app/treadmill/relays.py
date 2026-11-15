"""PhotoMOS relay board on the console's HD6 keypad connector.

Each relay joins its HD6 pin to the board's shared line. A press closes the select relays,
waits settle_ms, closes Go (pin 1, console ground) for press_ms, then opens everything.

Backend comes from gpiozero: lgpio on the Pi, or the mock pin factory when
GPIOZERO_PIN_FACTORY=mock (laptop and tests).
"""
import asyncio

from gpiozero import DigitalOutputDevice

from .config import Command, Config


class Relays:
    def __init__(self, cfg: Config):
        self._cfg = cfg
        # initial_value=False: every relay starts open (fail open).
        self._out = {pin: DigitalOutputDevice(bcm, initial_value=False) for pin, bcm in cfg.gpio.items()}

    def is_on(self, pin: int) -> bool:
        return bool(self._out[pin].value)

    def release_all(self) -> None:
        for dev in self._out.values():
            dev.off()

    async def press(self, cmd: Command, press_ms: int | None = None) -> None:
        """One tap: select relays closed -> settle_ms -> Go for press_ms -> all open."""
        try:
            for pin in cmd.select:
                self._out[pin].on()
            await asyncio.sleep(self._cfg.settle_ms / 1000)
            self._out[cmd.go].on()
            await asyncio.sleep((press_ms or self._cfg.press_ms) / 1000)
        finally:
            # Release Go first so the console never sees the select lines drop while Go is closed.
            self._out[cmd.go].off()
            self.release_all()

    def close(self) -> None:
        self.release_all()
        for dev in self._out.values():
            dev.close()
