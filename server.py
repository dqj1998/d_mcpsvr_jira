"""
d MCP server for JIRA implementation
"""
import os
from mcp.server.fastmcp import FastMCP
import logging
from dotenv import load_dotenv

from sqlite import del_project_db, init_project_db, search_tickets

# Load environment variables from .env file
load_dotenv()

# Ensure the logs directory exists
log_file_path = os.getenv("LOG_FILE_PATH", "logs/mcpsvr_jira.log")
log_dir = os.path.dirname(os.getenv("LOG_DIR", "logs"))
os.makedirs(log_dir, exist_ok=True)

# Ensure the log file exists
if not os.path.exists(log_file_path):
    with open(log_file_path, 'w') as f:
        pass

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s")

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=log_format,
    handlers=[
        logging.FileHandler(log_file_path, mode='a'),
        logging.StreamHandler()
    ]
)

# Example log to verify setup
logging.info("Logging is configured.")

# Create server instance
mcp = FastMCP("d_mcpsvr_jira")

@mcp.tool()
def echo(message: str) -> str:
    """Echo tool that returns the input message as is"""
    return f"Echo from d_mcpsvr_jira: {message}"

@mcp.tool()
def search(prompt: str, conditions: str, top_n: int, resp_format: str) -> str:
    """JIRA search by Vector Search
    Args:
        prompt (str): prompt string
        conditions (str): SQL-like conditions for filtering
        top_n (int): Number of top results to return
        resp_format (str): Response format: 'json', 'readable'
    Returns:
        str: Result of the prompt search
    """
    result = search_tickets(prompt, conditions, top_n, resp_format)
    if result.startswith("Err"):
        logging.error(f"Error in search: {result}")
        return result
    logging.info(f"Search completed successfully: {result}")

    if resp_format == "json":
        return result
    elif resp_format == "readable":
        # Convert JSON to a readable format
        try:
            import json
            result_json = json.loads(result)
            readable_result = "\n".join([f"{item['ticket_id']}: {item['summary']}" for item in result_json])
            return readable_result
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e}")
            return f"Err: Failed to decode JSON response: {e}"
    else:
        logging.error(f"Invalid response format: {resp_format}")
        return f"Err101: Invalid response format '{resp_format}'. Expected 'json' or 'readable'."

@mcp.tool()
def init_project(project_name: str) -> str:
    """Initialize a SQLite database for a given project name
    Args:
        project_name (str): Name of the project
    Returns:
        str: Success message or error
    """
    rtn = init_project_db(project_name)

    if rtn.startswith("Succ"):
        logging.info(f"Project '{project_name}' initialized successfully.")

    return rtn

@mcp.tool()
def del_project(project_name: str) -> str:
    """Delete a SQLite database for a given project name
    Args:
        project_name (str): Name of the project
    Returns:
        str: Success message or error
    """
    return del_project_db(project_name)

# Main execution block (if run directly)
if __name__ == "__main__":
    mcp.run()
