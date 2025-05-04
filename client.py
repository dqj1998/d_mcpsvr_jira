# An MCP client that calls the server locally, following the original MCP approach.
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python",  # Executable
    args=["server.py"],  # Optional command line arguments
    env=None,  # Optional environment variables
)

async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read, write
        ) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print("Available tools:", tools)

            # Call a tool
            result = await session.call_tool("echo", arguments={"message": "Msg from client"})
            print("Result from echo tool:", result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
