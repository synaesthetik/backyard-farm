import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bridge")

async def main():
    logger.info("Bridge service starting — waiting for plan 01-05 implementation")
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
