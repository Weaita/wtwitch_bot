import asyncio
from watcher import eventsub_listener

if __name__ == "__main__":
    asyncio.run(eventsub_listener())
