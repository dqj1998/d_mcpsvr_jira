import unittest
from sqlite import *  # Import all functions and classes from sqlite.py
import logging.handlers  # Import the handlers module to access RotatingFileHandler

class TestSQLiteFeatures(unittest.TestCase):

    def test_db_flow(self):
        # initialize the database
        project_name = "test_project"
        result = init_project_db(project_name)
        self.assertIn("Succ", result)
        self.assertIn("test_project.db", result)
        # Check if the database file was created
        db_dir = os.getenv("DB_DIR", "databases")
        db_path = os.path.join(db_dir, f"{project_name}.db")
        self.assertTrue(os.path.exists(db_path))

        # add some tickets
        ticket_json = '{"ticket_id": "TICKET-1", "summary": "Test Ticket", "description": "This is a test ticket.", "status": "Open", "priority": "High", "reporter": "Marry", "assignee": "John Doe", "created": "2023-10-01", "updated": "2023-10-02"}'
        result = add_ticket(project_name, ticket_json)
        self.assertIn("Succ", result)
        self.assertIn("TICKET-1", result)
        ## add more tickets
        ticket_json2 = '{"ticket_id": "TICKET-2", "summary": "Another Ticket", "description": "This is finished ticket.", "status": "In Progress", "priority": "Medium", "reporter": "Alice", "assignee": "Bob", "created": "2023-10-03", "updated": "2023-10-04"}'
        result = add_ticket(project_name, ticket_json2)
        self.assertIn("Succ", result)
        self.assertIn("TICKET-2", result)

        # Check if the ticket was added to the database
        conn = sqlite3.connect(db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        cursor = conn.cursor()

        cursor.execute("SELECT * FROM jira_tickets WHERE ticket_id = 'TICKET-1'")
        ticket = cursor.fetchone()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket[1], "TICKET-1")
        self.assertEqual(ticket[2], "Test Ticket")
        self.assertEqual(ticket[3], "This is a test ticket.")  

        cursor.execute("SELECT * FROM jira_tickets WHERE status = 'In Progress'")
        ticket = cursor.fetchone()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket[1], "TICKET-2")

        conn.close()

        # search for the test ticket
        result = search_tickets(project_name, "Test")  
        #parse the result as JSON
        result_json = json.loads(result)      
        self.assertIn("TICKET-1", result_json[0]["ticket_id"])

        # search for the finished ticket
        result = search_tickets(project_name, "finished")  
        #parse the result as JSON
        result_json = json.loads(result)      
        self.assertIn("TICKET-2", result_json[0]["ticket_id"])

        # search for the finished ticket
        result = search_tickets(project_name, "ticket", "(status = 'In Progress')")  
        #parse the result as JSON
        result_json = json.loads(result)
        self.assertEqual(len(result_json), 1)
        self.assertIn("TICKET-2", result_json[0]["ticket_id"])

        # search for the finished ticket
        result = search_tickets(project_name, "", "(status = 'In Progress')")  
        #parse the result as JSON
        result_json = json.loads(result)
        self.assertEqual(len(result_json), 1)
        self.assertIn("TICKET-2", result_json[0]["ticket_id"])

        # delete the project database
        result = del_project_db(project_name)
        self.assertIn("Succ", result)
        

if __name__ == "__main__":
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv()

        # Configure logging
        log_file_path = os.getenv("LOG_FILE_PATH", "project.log")
        log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s")
        log_file_size = int(os.getenv("LOG_FILE_SIZE", 10485760))  # Default to 10MB
        backup_count = int(os.getenv("BCKUP_COUNT", 5))  # Default to 5 backups

        logging.basicConfig(
            level=getattr(logging, 'DEBUG', logging.DEBUG),
            format=log_format,
            handlers=[
                logging.handlers.RotatingFileHandler(  # Use logging.handlers to access RotatingFileHandler
                    log_file_path, maxBytes=log_file_size, backupCount=backup_count
                ),
                logging.StreamHandler(),
            ]
        )

        try:
            unittest.main()
        finally:
            db_dir = os.getenv("DB_DIR", "databases")
            db_path = os.path.join(db_dir, "test_project.db")
            if os.path.exists(db_path):
                os.remove(db_path)
    except Exception as e:
        # Log the error
        logging.error(f"Test failed: {e}")
