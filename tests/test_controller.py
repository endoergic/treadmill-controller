"""Controller + relay safety behavior, run against gpiozero's mock pins.

    GPIOZERO_PIN_FACTORY=mock PYTHONPATH=app python3 -m pytest tests
"""
import asyncio
import dataclasses

import pytest
from gpiozero import Device

from treadmill import config
from treadmill.config import Command
from treadmill.controller import Controller, Rejected
from treadmill.relays import Relays


@pytest.fixture
def cfg():
    base = config.load(config.EXAMPLE_CONFIG)
    commands = dict(base.commands, stop=Command("stop", (4,), 1))
    return dataclasses.replace(base, commands=commands, settle_ms=5, press_ms=10, gap_ms=0,
                               max_speed=1.0, max_commands_per_sec=100, start_speed=0.5)


@pytest.fixture(autouse=True)
def fresh_pins():
    yield
    Device.pin_factory.reset()


def test_press_closes_select_before_go_and_releases_everything(cfg):
    relays = Relays(cfg)
    cmd = cfg.commands["speed_up"]
    seen = []

    async def scenario():
        task = asyncio.create_task(relays.press(cmd))
        await asyncio.sleep(0.002)  # inside settle window
        seen.append(("settle", {p: relays.is_on(p) for p in cfg.gpio}))
        await asyncio.sleep(0.008)  # inside press window
        seen.append(("press", {p: relays.is_on(p) for p in cfg.gpio}))
        await task

    asyncio.run(scenario())
    settle, press = seen[0][1], seen[1][1]
    assert {p for p, on in settle.items() if on} == set(cmd.select)
    assert {p for p, on in press.items() if on} == {*cmd.select, cmd.go}
    assert not any(relays.is_on(p) for p in cfg.gpio)


def test_press_releases_relays_when_cancelled_mid_press(cfg):
    relays = Relays(cfg)

    async def scenario():
        task = asyncio.create_task(relays.press(cfg.commands["speed_up"]))
        await asyncio.sleep(0.008)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert not any(relays.is_on(p) for p in cfg.gpio)


def test_stop_clears_queue_and_bypasses_rate_limit(cfg):
    cfg = dataclasses.replace(cfg, max_commands_per_sec=2)

    async def scenario():
        ctl = Controller(cfg, Relays(cfg))
        ctl.submit("speed_up")
        ctl.submit("speed_up")
        with pytest.raises(Rejected):
            ctl.submit("speed_up")
        ctl.submit("stop")
        return list(ctl.state()["queued"])

    assert asyncio.run(scenario()) == ["stop"]


def test_max_speed_counts_queued_taps(cfg):
    # start_speed 0.5, step 0.1, max 1.0 -> 0.5 + 5 taps reaches 1.0; the 7th tap is refused.
    async def scenario():
        ctl = Controller(cfg, Relays(cfg))
        for _ in range(6):
            ctl.submit("speed_up")
        with pytest.raises(Rejected, match="max speed"):
            ctl.submit("speed_up")
        ctl.submit("speed_down")  # going down is always allowed

    asyncio.run(scenario())


def test_worker_presses_in_order_and_tracks_speed(cfg):
    async def scenario():
        ctl = Controller(cfg, Relays(cfg))
        ctl.start()
        for name in ["speed_up", "speed_up", "speed_down", "speed_up"]:
            ctl.submit(name)
        while ctl.busy or ctl.state()["queued"]:
            await asyncio.sleep(0.005)
        await ctl.stop_worker()
        return ctl.speed

    assert asyncio.run(scenario()) == pytest.approx(0.6)


def test_reset_during_press_is_not_overwritten(cfg):
    async def scenario():
        ctl = Controller(cfg, Relays(cfg))
        ctl.start()
        ctl.submit("speed_up")
        ctl.submit("speed_up")
        await asyncio.sleep(0.008)  # first tap in flight
        assert ctl.busy == "speed_up"
        ctl.reset_speed()
        await asyncio.sleep(0.05)
        await ctl.stop_worker()
        return ctl.speed, ctl.state()["queued"]

    assert asyncio.run(scenario()) == (0.0, [])


def run_until_idle(ctl):
    async def scenario(submit):
        ctl.start()
        submit()
        while ctl.busy or ctl.state()["queued"]:
            await asyncio.sleep(0.005)
        await ctl.stop_worker()
    return scenario


def test_presets_set_the_estimate_and_are_refused_above_max_speed(cfg):
    cfg = dataclasses.replace(cfg, max_speed=6.0)

    async def scenario():
        ctl = Controller(cfg, Relays(cfg))
        with pytest.raises(Rejected, match="max speed"):
            ctl.submit("speed_7")
        await run_until_idle(ctl)(lambda: (ctl.submit("speed_4"), ctl.submit("speed_up")))
        return ctl.speed

    assert asyncio.run(scenario()) == pytest.approx(4.1)


def test_start_only_moves_the_estimate_from_stopped(cfg):
    async def scenario():
        ctl = Controller(cfg, Relays(cfg))
        await run_until_idle(ctl)(lambda: ctl.submit("start"))
        first = ctl.speed
        await run_until_idle(ctl)(lambda: (ctl.submit("speed_up"), ctl.submit("start")))
        return first, ctl.speed

    assert asyncio.run(scenario()) == pytest.approx((cfg.start_speed, cfg.start_speed + cfg.step))


@pytest.mark.parametrize("select, go, press_ms, error", [
    ([1, 5], 1, 300, "ground"),
    ([4, 6], 1, 99999, "hold time"),
    ([2, 3, 4, 5, 6], 1, 300, "max_relays_on"),
    ([4, 11], 1, 300, "no GPIO"),
])
def test_manual_press_is_refused_when_unsafe(cfg, select, go, press_ms, error):
    ctl = Controller(cfg, Relays(cfg))
    with pytest.raises(Rejected, match=error):
        ctl.submit_manual(select, go, press_ms)


def test_manual_press_holds_go_for_its_own_time_and_keeps_the_estimate(cfg):
    relays = Relays(cfg)
    seen = []

    async def scenario():
        ctl = Controller(cfg, relays)
        ctl.speed = 2.0
        ctl.start()
        ctl.submit_manual([4, 6], 1, 60)
        await asyncio.sleep(0.04)  # past settle_ms + the config's 10 ms press, inside the 60 ms hold
        seen.append({p for p in cfg.gpio if relays.is_on(p)})
        while ctl.busy or ctl.state()["queued"]:
            await asyncio.sleep(0.005)
        await ctl.stop_worker()
        return ctl.speed

    assert asyncio.run(scenario()) == 2.0
    assert seen == [{4, 6, 1}]
    assert not any(relays.is_on(p) for p in cfg.gpio)
