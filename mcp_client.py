import asyncio
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

# Path to the server script
server_script = "server.py"

# Start the server using PythonStdioTransport
transport = PythonStdioTransport(script_path=server_script)

async def list_tools():
    # Create a client and communicate with the server
    async with Client(transport) as client:
        # Retrieve available tools
        tools = await client.list_tools()
        return tools
    
async def call_tool(tool_name, tool_args):
    # Create a client and communicate with the server
    try:
        async with Client(transport) as client:
            # Call a specific tool with arguments
            result = await client.call_tool(tool_name, tool_args)
            return result
    except Exception as e:
        return f"Error calling tool {tool_name}: {str(e)}"

if __name__ == "__main__":
    # List available tools
    tools = asyncio.run(list_tools())
    print("Available tools:", tools)

    # Call the "echo" tool with a message
    result = asyncio.run(call_tool("echo", {"message": "Hello, World!"}))
    print("Tool result:", result)
