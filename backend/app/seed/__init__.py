import asyncio
import sys

from .glowvita import seed_glowvita


async def _run() -> None:
    from app.db import engine

    await seed_glowvita(engine)
    await engine.dispose()
    print("Seed complete.")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
