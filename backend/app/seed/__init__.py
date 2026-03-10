import asyncio
import uuid

from .glowvita import seed_glowvita


async def _run() -> None:
    from app.db import engine

    user_id: uuid.UUID | None = None
    await seed_glowvita(engine, user_id=user_id)
    await engine.dispose()
    print("Seed complete.")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
