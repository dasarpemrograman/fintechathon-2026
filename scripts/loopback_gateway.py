"""Fixed local TCP relay exposes an otherwise egress-isolated demo network."""

import asyncio


async def relay(reader, writer, host, port):
    remote = None
    try:
        upstream, remote = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=5
        )

        async def pump(source, target):
            while data := await source.read(65536):
                target.write(data)
                await target.drain()
            target.close()

        await asyncio.gather(pump(reader, remote), pump(upstream, writer))
    except (OSError, asyncio.TimeoutError, ConnectionError):
        pass
    finally:
        writer.close()
        if remote:
            remote.close()


async def main():
    # Destinations are fixed application services, never supplied by a request.
    servers = []
    for listen, host, target in [(3000, "web", 3000), (8000, "api", 8000)]:
        servers.append(
            await asyncio.start_server(
                lambda r, w, h=host, p=target: relay(r, w, h, p), "0.0.0.0", listen
            )
        )
    await asyncio.gather(*(server.serve_forever() for server in servers))


if __name__ == "__main__":
    asyncio.run(main())
