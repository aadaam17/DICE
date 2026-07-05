from __future__ import annotations

import argparse
import asyncio

from dice.service.client import DEFAULT_HOST, DEFAULT_PORT
from dice.service.server import DiceService


async def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    service = DiceService(host=host, port=port)
    print(f"DICE daemon listening on {host}:{port}")
    try:
        await service.serve_forever()
    finally:
        await service.stop()


def run() -> None:
    parser = argparse.ArgumentParser(description="Run the DICE background job service.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port))


if __name__ == "__main__":
    run()
