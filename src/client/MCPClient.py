import asyncio
import json
import os
from contextlib import AsyncExitStack
from pathlib import Path
from urllib import error, request

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

load_dotenv()  # load environment variables from .env

# Ollama model constant
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "minimax-m2.7:cloud")


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

    def _chat_with_ollama(self, messages: list[dict], tools: list[dict]) -> dict:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.ollama_host}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if "does not support tools" in body:
                raise RuntimeError(
                    f"Model '{OLLAMA_MODEL}' does not support tools in Ollama. "
                    "Use a tool-capable model and set OLLAMA_MODEL accordingly."
                ) from exc
            raise RuntimeError(f"Ollama API error {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(
                "Could not connect to Ollama. Make sure it is running and reachable at "
                f"{self.ollama_host}."
            ) from exc

    async def connect_to_server(self, server_target: str):
        """Connect to an MCP server via SSE URL or a local script path.

        Args:
            server_target: HTTP/HTTPS URL of a running MCP server, or path to a .py/.js script
        """



        path = Path(server_target).resolve()
        server_params = StdioServerParameters(
            command="uv",
            args=["--directory", str(path.parent), "run", path.name],
            env=None,
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available tools"""
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                },
            }
            for tool in response.tools
        ]

        # Initial Ollama API call
        response = self._chat_with_ollama(messages=messages, tools=available_tools)

        # Process response and handle tool calls
        final_text = []

        while True:
            message = response.get("message", {})
            text = message.get("content") or ""
            if text:
                final_text.append(text)

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                break

            messages.append(message)

            for call in tool_calls:
                tool_name = call["function"]["name"]
                tool_args = call["function"].get("arguments", {})

                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                messages.append(
                    {
                        "role": "tool",
                        "name": tool_name,
                        "content": str(result.content),
                    }
                )

            response = self._chat_with_ollama(messages=messages, tools=available_tools)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
