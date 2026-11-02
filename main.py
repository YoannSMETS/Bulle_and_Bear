"""Bulle & Bear launcher: starts all agents in one process plus the UI."""
import argparse

from agents.wiring import Platform, default_device
from ui.ui import UI


def main():
    ap = argparse.ArgumentParser(description="Bulle & Bear")
    ap.add_argument("--device", default=None, help="Ingescape network device (default: first non-loopback)")
    ap.add_argument("--port", type=int, default=5670)
    ap.add_argument("--speed", type=float, default=1.0, help="time acceleration (1 = 6 min match)")
    ap.add_argument("--seed", type=int, default=None, help="reproducible market and news")
    ap.add_argument("--windowed", action="store_true", help="don't use full screen (F11 toggles)")
    args = ap.parse_args()

    ui = UI(fullscreen=not args.windowed)
    platform = Platform(ui_agent=ui, speed=args.speed, seed=args.seed)
    platform.start(args.device or default_device(), args.port)
    try:
        ui.run()
    finally:
        platform.stop()


if __name__ == "__main__":
    main()
