from jira import JIRA
import os
import logging

JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_USERNAME = os.getenv("JIRA_USER")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

if not JIRA_SERVER or not JIRA_USERNAME or not JIRA_API_TOKEN:
    msg = "WARN901:JIRA_SERVER, JIRA_USERNAME, and JIRA_API_TOKEN are not set in environment variables. Only can use local SQLite database."
    logging.warning(msg)

def get_jira_client():
    """
    Returns a JIRA client instance.
    """
    try:
        jira = JIRA(
            server=JIRA_SERVER,
            basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN)
        )
        return jira
    except Exception as e:
        msg = "Err108:Failed to connect to JIRA. Please check your credentials and server URL."
        logging.error(msg)
        raise RuntimeError(msg) from e
    
def jql_query(jql: str) -> list:
    """
    Executes a JQL query and returns the results.
    """
    jira = get_jira_client()
    try:
        issues = jira.search_issues(jql)
        return issues
    except Exception as e:
        msg = f"Err109: Failed to execute JQL query: {e}"
        logging.error(msg)
        raise RuntimeError(msg) from e