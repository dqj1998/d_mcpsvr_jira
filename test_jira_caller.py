import unittest
from jira_caller import *  # Import all functions and classes from jira.py
import logging.handlers  # Import the handlers module to access RotatingFileHandler
import os
from util import init_logger

class TestJiraFeatures(unittest.TestCase):

    def test_jira_flow(self):
        project = os.getenv("JIRA_PROJECT_NAME", "TEST")
        tickets = jql_query(f"project = {project} order by created DESC")
        self.assertIsInstance(tickets, list)
        self.assertGreater(len(tickets), 0)
       
if __name__ == "__main__":
    try:
        init_logger()  # Initialize the logger       

        unittest.main()
        
    except Exception as e:
        # Log the error
        logging.error(f"Test failed: {e}")