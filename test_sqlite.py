import unittest
import os
from util import init_logger
from sqlite import init_project_db, add_ticket, search_tickets, del_project_db, get_tickets_count
import sqlite3
import sqlite_vec
import json
import logging
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

        count = get_tickets_count(project_name)
        self.assertEqual(count, 0)
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

        count = get_tickets_count(project_name)
        self.assertEqual(count, 2)

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
       
       init_logger()  # Initialize the logger
        
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
