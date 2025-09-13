import asyncio
import os
from aiohttp import web
from watcher import eventsub_listener

async def handle(request):
    return web.Response(text="Twitch bot corriendo 🚀")

async def run_web():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Servidor HTTP escuchando en puerto {port}")

async def main():
    # Corre tu bot y el servidor web en paralelo
    await asyncio.gather(
        eventsub_listener(),
        run_web()
    )

if __name__ == "__main__":
    asyncio.run(main())
