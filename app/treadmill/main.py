"""Starlette web app: static phone UI + one WebSocket per phone.

Run from the repo root:
    On the Pi:   PYTHONPATH=app python3 -m treadmill.main
    On a laptop: GPIOZERO_PIN_FACTORY=mock PYTHONPATH=app python3 -m treadmill.main --port 8000

Client -> server:  {"type": "press", "command": "speed_up"} | {"type": "reset"}
                   | {"type": "manual", "select": [4, 6], "go": 1, "press_ms": 300}   (troubleshooting panel)
Server -> client:  {"type": "state", ...} | {"type": "error", "message": "..."}
"""
import argparse
import contextlib
import hmac
import json
import logging
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from . import config as config_mod
from .config import Config
from .controller import Controller, Rejected
from .relays import Relays

log = logging.getLogger("treadmill")
STATIC = Path(__file__).resolve().parent / "static"
BAD_PIN = 4001  # WebSocket close code the UI treats as "ask for the PIN"


class NoCacheStatic(StaticFiles):
    """Browsers revalidate the UI on every load (a cheap 304 on the LAN), so a deploy shows up on the next reload.
    Without this they cache app.js heuristically for hours and keep running the old UI."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


def create_app(cfg: Config) -> Starlette:
    @contextlib.asynccontextmanager
    async def lifespan(app):
        relays = Relays(cfg)
        ctl = Controller(cfg, relays)
        ctl.start()
        app.state.ctl = ctl
        log.info("ready: commands %s", ", ".join(cfg.commands) or "(none)")
        try:
            yield
        finally:
            await ctl.stop_worker()
            relays.close()
            log.info("all lines released")

    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        if cfg.pin and not hmac.compare_digest(ws.query_params.get("pin", ""), cfg.pin):
            await ws.close(code=BAD_PIN)
            return

        ctl: Controller = ws.app.state.ctl

        async def send(msg: dict) -> None:
            await ws.send_text(json.dumps(msg))

        ctl.subscribe(send)
        await ctl.broadcast()  # new phone gets state; others see the client count change
        try:
            while True:
                try:
                    msg = json.loads(await ws.receive_text())
                    if msg.get("type") == "press":
                        ctl.submit(str(msg.get("command")))
                    elif msg.get("type") == "reset":
                        ctl.reset_speed()
                    elif msg.get("type") == "manual":
                        ctl.submit_manual([int(p) for p in msg.get("select", [])], int(msg.get("go")),
                                          int(msg.get("press_ms")))
                    else:
                        raise Rejected(f"unknown message type: {msg.get('type')}")
                except (Rejected, json.JSONDecodeError, AttributeError, TypeError, ValueError) as e:
                    await send({"type": "error", "message": str(e)})
                    continue
                await ctl.broadcast()
        except WebSocketDisconnect:
            pass
        finally:
            ctl.unsubscribe(send)
            await ctl.broadcast()

    return Starlette(
        routes=[
            WebSocketRoute("/ws", ws_endpoint),
            Mount("/", NoCacheStatic(directory=STATIC, html=True)),
        ],
        lifespan=lifespan,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Treadmill controller web app")
    ap.add_argument("--config", type=Path, default=config_mod.default_config_path())
    ap.add_argument("--host")
    ap.add_argument("--port", type=int)
    args = ap.parse_args()

    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cfg = config_mod.load(args.config)
    log.info("config: %s", args.config)
    uvicorn.run(create_app(cfg), host=args.host or cfg.host, port=args.port or cfg.port,
                ws="websockets", log_level="info")


if __name__ == "__main__":
    main()
