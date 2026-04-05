import asyncio
import MCPClient


async def main():
    if len(sys.argv) < 2:
        print("Usage: python src/main.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient.MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())