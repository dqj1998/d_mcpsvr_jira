"""
d MCP server for JIRA implementation
"""
import logging
import os
import json
from fastapi import FastAPI
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

from jira_caller import jql_query
from sqlite import (
    append_tickets,
    create_test_db,
    del_project_db,
    init_project_db,
    search_tickets,
)



# Determine log file path
actual_log_file_path = os.getenv("LOG_FILE_PATH", "logs/mcpsvr_jira.log")

# Ensure the logs directory exists
actual_log_dir = os.path.dirname(actual_log_file_path)
if actual_log_dir: # Ensure dirname is not empty (e.g. if log file is in CWD)
    os.makedirs(actual_log_dir, exist_ok=True)

# Ensure the log file exists
if not os.path.exists(actual_log_file_path):
    with open(actual_log_file_path, 'w') as f:
        pass # Just to create it

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
# actual_log_file_path is now defined above and will be used by the handler
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s")
log_file_size = int(os.getenv("LOG_FILE_SIZE", 10485760))  # Default to 10MB
backup_count = int(os.getenv("LOG_BACKUP_COUNT", 5))  # Default to 5 backups

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=log_format,
    handlers=[
        logging.handlers.RotatingFileHandler(  # Use logging.handlers to access RotatingFileHandler
            actual_log_file_path, maxBytes=log_file_size, backupCount=backup_count
        )
    ]
)

# Suppress DEBUG and INFO logs from mcp.server.lowlevel.server in the terminal
for logger_name in logging.root.manager.loggerDict:
    logging.getLogger(logger_name).setLevel(logging.INFO)
logging.getLogger("mcp.server.lowlevel.server").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)


# Example log to verify setup
logging.info("Logging is configured.")

create_test_db()

# Create server instance
mcp = FastMCP("d_mcpsvr_jira")

@mcp.tool()
def echo(message: str) -> str:
    """Echo tool that returns the input message as is"""
    return f"Echo from d_mcpsvr_jira: {message}"

@mcp.tool()
def search(project: str, prompt: str="", conditions: str="", top_n: int=5, resp_format: str="json") -> str:
    """JIRA search by Vector Search
    Args:
        project (str): Project name
        prompt (str): prompt string
        conditions (str): SQL-like conditions for filtering
        top_n (int): Number of top results to return
        resp_format (str): Response format: 'json', 'readable'
    Returns:
        str: Result of the prompt search
    """
    result = search_tickets(project, prompt, conditions, top_n)
    if result is str and result.startswith("Err"):
        logging.error(f"Error in search: {result}")
        return result
    logging.info(f"Search completed successfully: {result}")

    if resp_format == "json":
        return result
    elif resp_format == "readable":
        # Convert JSON to a readable format
        try:            
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

    if rtn.startswith("Err"):
        logging.error(rtn)
        return rtn

    logging.info(f"Project '{project_name}' initialized successfully.")

    jql = f"""
    project = "{project_name}" AND 
    (created >= -30d OR
    status changed TO "In Progress" AFTER -30d OR
    status changed TO "Done" AFTER -30d OR
    status = "In Progress")
    and type = Task ORDER BY due ASC
    """

    tickets = jql_query(jql)
    logging.info(f"JQL query executed successfully: {jql}")

    count = append_tickets(project_name, tickets)

    msg = f"Succ: Init project DB of {project_name} and appended {count} tickets to the database."
    logging.info(msg)
    
    return msg

@mcp.tool()
def load_tickets(project_name: str, jql: str) -> str:
    """Load tickets from JIRA using a JQL query
    Args:
        jql (str): JQL query string
    Returns:
        str: Result of the JQL query
    """
    try:
        issues = jql_query(jql)
        if issues and len(issues) > 0:
            logging.info(f"Loaded {len(issues)} tickets from JIRA.")
            count = append_tickets(project_name, issues)
            msg = f"Succ: Appended {count} tickets to the database."
            logging.info(msg)
            return msg
        
    except Exception as e:
        msg = f"Err111: Failed to load tickets from JIRA: {e}"
        logging.error(msg)
        return msg

@mcp.tool()
def del_project(project_name: str) -> str:
    """Delete a SQLite database for a given project name
    Args:
        project_name (str): Name of the project
    Returns:
        str: Success message or error
    """
    return del_project_db(project_name)

#app = FastAPI()
#app.mount("/", mcp.sse_app())

# Main execution block (if run directly)
if __name__ == "__main__":
    mcp.run()
