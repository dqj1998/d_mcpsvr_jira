import unittest
from server import *
import os
from util import init_logger

class TestServerFeatures(unittest.TestCase):

    def test_init_project(self):
        project = os.getenv("JIRA_PROJECT_NAME", "TEST")
        result = init_project(project)

        if result.startswith("Err"):
            logging.error(f"Error initializing project: {result}")
            self.fail(result)

        # Check if the project database was created
        db_dir = os.getenv("DB_DIR", "databases")
        db_path = os.path.join(db_dir, f"{project}.db")
        self.assertTrue(os.path.exists(db_path), f"Database for project {project} was not created.")
       
if __name__ == "__main__":
    try:
        init_logger()  # Initialize the logger       

        unittest.main()
        
    except Exception as e:
        # Log the error
        logging.error(f"Test failed: {e}")