"""
Minimal MCP server implementation
"""
from mcp.server.fastmcp import FastMCP

# Create server instance
mcp = FastMCP("d_mcpsvr_jira", "0.0.1")

@mcp.tool()
def echo(message: str) -> str:
    """Echo tool that returns the input message as is"""
    return f"Echo from d_mcpsvr_jira: {message}"

@mcp.tool()
def jql_search(message: str) -> str:
    """Echo tool that returns the input message as is"""
    return f"jql_search from d_mcpsvr_jira: {message}"

@mcp.prompt()
def ask(message: str) -> str:
    """Prompt tool that returns the input message as is"""
    return f"Prompt from d_mcpsvr_jira: {message}"

# Main execution block (if run directly)
if __name__ == "__main__":
    mcp.run()
