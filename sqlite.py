import sqlite3
import sqlite_vec
import os
import logging
import json
from transformers import AutoTokenizer, AutoModel
import torch

# Load the model and tokenizer globally to avoid reloading them for every call
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

def init_project_db(project_name: str) -> str:
    # get db_dir from the environment variable
    db_dir = os.getenv("DB_DIR", "databases")
    
    db_path = os.path.join(db_dir, f"{project_name}.db")

    # Check if the database already exists
    if os.path.exists(db_path):
        msg = f"Err001: Database for project '{project_name}' already exists at {db_path}"
        logging.error(msg)
        return msg
    # Create the directory if it doesn't exist
    os.makedirs(db_dir, exist_ok=True)
    
    try:
        conn = sqlite3.connect(db_path)
        conn.close()
        
        conn = connect_db(project_name)
        cursor = conn.cursor()
        cursor.execute('''                       
            CREATE VIRTUAL TABLE jira_tickets USING vec0(
            id INTEGER PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            summary TEXT,
            description TEXT,
            status TEXT,
            priority TEXT,
            assignee TEXT,
            reporter TEXT,
            created TEXT,
            updated TEXT,
            original_estimate_seconds INT,
            due_date TEXT,
            full_json TEXT,
            embedding float[384],
            );
        ''')
        
        conn.commit()
        conn.close()
        msg = f"Succ: Database initialized for project '{project_name}' at {db_path}"
        logging.info(msg)
        return msg
    except Exception as e:
        msg = f"Err002: Error initializing database for project '{project_name}': {e}"
        logging.error(msg)
        return msg

def get_tickets_count(project_name: str) -> int:
    """
    Get the count of tickets in the database.

    Args:
        project_name (str): The name of the project (database file).

    Returns:
        int: The count of tickets in the database.
    """
    try:
        conn = connect_db(project_name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jira_tickets")
        count, = cursor.fetchone()
        conn.close()
        return count
    except Exception as e:
        msg = f"Err113: Error getting ticket count from database for project '{project_name}': {e}"
        logging.error(msg)
        return 0

def search_tickets(project_name: str, prompt: str, conditions: str = "", top_n: int = 5):
    """
    Search for tickets in the database using sqlite-vec for vector similarity.

    Args:
        project_name (str): The name of the project (database file).
        prompt_vector (list): The input vector to compare against stored vectors.
        top_n (int): The number of top similar tickets to return.

    Returns:
        list: A list of tuples containing ticket_id, summary, and similarity score.
    """
    try:
        if (not prompt or prompt.strip() == "") and (not conditions or conditions.strip() == ""):
            msg = "Err105: Prompt and conditions cannot be empty both."
            logging.error(msg)
            return msg
        
        prompt_vector_str = ""
        if prompt and prompt.strip() !="":            
            prompt_vector = make_vector(prompt)
            prompt_vector_str = ", ".join(map(str, prompt_vector)) 

        conn = connect_db(project_name)

        vec_version, = conn.execute("select vec_version()").fetchone()
        logging.debug(f"sqlite_vec={vec_version}")

        cursor = conn.cursor()        

        # Query for the top N most similar tickets
        query = f"""
        SELECT ticket_id, summary, description, status, priority, assignee, reporter, created, updated, original_estimate_seconds, due_date, full_json, distance
        FROM jira_tickets
        WHERE 
        """
        if prompt_vector_str and prompt_vector_str.strip() != "":
            query += f" embedding match '[{prompt_vector_str}]' "
        else:
            query += f" 1=1 "
        if conditions and conditions.strip() != "":
            query += f" AND {conditions} "
        query += f"""
        ORDER BY distance ASC
        LIMIT {top_n};
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        results = [
            {
            "ticket_id": row[0],
            "summary": row[1],
            "description": row[2],
            "status": row[3],
            "priority": row[4],
            "assignee": row[5],
            "reporter": row[6],
            "created": row[7],
            "updated": row[8],
            "original_estimate_seconds": row[9],
            "due_date": row[10],
            "full_json": row[11],
            "distance": row[12],
            }
            for row in results
        ]

        # Convert results to a JSON array
        results_json = json.dumps(results)
        return results_json

    except Exception as e:
        msg = f"Err004: Error searching tickets in database for project '{project_name}': {e}"
        logging.error(msg)
        return []
    
def make_vector(prompt: str) -> list:
    """
    Convert a prompt string into a vector representation using a pre-trained model.

    Args:
        prompt (str): The input string to convert.

    Returns:
        list: A list representing the vector.
    """
    try:
        # Tokenize the input text
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, padding=True)

        # Generate embeddings
        with torch.no_grad():
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().tolist()

        return embeddings
    except Exception as e:
        logging.error(f"Err005: Failed to generate vector for prompt '{prompt}': {e}")
        return []
    
def add_ticket(project_name: str, ticket: any) -> str:
    """
    Add a new ticket to the database.

    Args:
        project_name (str): The name of the project (database file).
        full_json (str): The full JSON representation of the ticket.

    Returns:
        str: Success or error message.
    """

    try:        
        ticket_data = "{}"
        # Check if the full_json is String
        if isinstance(ticket, str):
            ticket_data = json.loads(ticket)
        else:
            ticket_data = parse_issue_2_json(ticket)
            
        # Parse the JSON to extract required fields
        ticket_id = ticket_data.get("key") if ticket_data.get("key") else ticket_data.get("ticket_id")
        summary = ticket_data.get("summary")
        
        if not ticket_id or not summary:
            msg = "Err008: Missing required fields (ticket_id, summary) in JSON."
            logging.error(msg)
            return msg

        # Generate vector from the description
        description = ticket_data.get("description", "")
        if not description:
            description = ""
        vector = make_vector(summary + ":" + description)
        
        # Convert the vector (list) to float[384] format
        if len(vector) != 384:
            msg = f"Err006: Vector length is not 384, got {len(vector)}"
            logging.error(msg)
            return msg

        vector_array = sqlite3.Binary(torch.tensor(vector).numpy().tobytes())    

        conn = None
        try:
            conn = connect_db(project_name)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO jira_tickets (ticket_id, summary, description, status, priority, assignee, reporter, created, updated, original_estimate_seconds, due_date, full_json, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ticket_id, summary, 
                    description or "",
                    ticket_data.get("status", "") or "",
                    ticket_data.get("priority", "") or "",
                    ticket_data.get("assignee", "") or "", 
                    ticket_data.get("reporter", "") or "", 
                    ticket_data.get("created", "") or "", 
                    ticket_data.get("updated", "") or "", 
                    ticket_data.get("original_estimate_seconds", 0) or 0,
                    ticket_data.get("due_date", "") or "",
                  json.dumps(ticket_data) or "",  # Convert ticket_data to a JSON string
                  vector_array))
            conn.commit()
        finally:
            if conn:
                conn.close()
        
        msg = f"Succ: Ticket '{ticket_id}' added to project '{project_name}'"
        logging.debug(msg)
        return msg
    except json.JSONDecodeError as e:
        msg = f"Err009: Failed to parse JSON: {e}"
        logging.error(msg)
        return msg
    except Exception as e:
        msg = f"Err007: Error adding ticket to database for project '{project_name}': {e}"
        logging.error(msg)
        return msg
    
def parse_issue_2_json(issue) -> str:
    """
    Convert a JIRA issue object to a JSON string.

    Args:
        issue: The JIRA issue object.

    Returns:
        str: The JSON string representation of the issue.
    """
    try:
        # Convert issue to dictionary
        issue_dict = {
            'key': issue.key,
            'summary': issue.fields.summary,
            'description': issue.fields.description,
            'status': issue.fields.status.name,
            'assignee': issue.fields.assignee.displayName if issue.fields.assignee else None,
            'reporter': issue.fields.reporter.displayName if issue.fields.reporter else None,
            'created': issue.fields.created,
            'updated': issue.fields.updated,
            'priority': issue.fields.priority.name if issue.fields.priority else None,
            'labels': issue.fields.labels,
            'components': [comp.name for comp in issue.fields.components],
            'issue_type': issue.fields.issuetype.name,
            # Add more fields as needed
        }
        #issue_json = json.dumps(issue_dict, indent=4, ensure_ascii=False)
        return issue_dict
    
    except Exception as e:
        msg = f"Err110: Failed to convert issue to JSON: {e}"
        logging.error(msg)
        return ""

def append_tickets(project_name: str, tickets: list) -> int:
    """
    Add multiple tickets to the database.

    Args:
        project_name (str): The name of the project (database file).
        tickets (list): A list of ticket JSON strings.

    Returns:
        str: Success or error message.
    """
    if not tickets or len(tickets) == 0:
        return 0
    
    count = 0
    for ticket_json in tickets:
        result = add_ticket(project_name, ticket_json)
        if result.startswith("Err"):
            logging.error(result)
        else:
            count += 1

    return count


def connect_db(project_name: str):
    """
    Connect to the SQLite database for the given project name.

    Args:
        project_name (str): The name of the project (database file).

    Returns:
        sqlite3.Connection: The SQLite connection object.
    """
    db_dir = os.getenv("DB_DIR", "databases")
    db_path = os.path.join(db_dir, f"{project_name}.db")

    if not os.path.exists(db_path):
        msg = f"Err010: Database for project '{project_name}' does not exist at {db_path}"
        logging.error(msg)
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn
    except Exception as e:
        msg = f"Err011: Error connecting to database for project '{project_name}': {e}"
        logging.error(msg)
        return None
    
def del_project_db(project_name: str):
    """
    Delete the SQLite database for the given project name.

    Args:
        project_name (str): The name of the project (database file).

    Returns:
        str: Success or error message.
    """
    db_dir = os.getenv("DB_DIR", "databases")
    db_path = os.path.join(db_dir, f"{project_name}.db")

    if os.path.exists(db_path):
        os.remove(db_path)
        msg = f"Succ: Database for project '{project_name}' deleted at {db_path}"
        logging.info(msg)
        return msg
    else:
        msg = f"Err012: Database for project '{project_name}' does not exist at {db_path}"
        logging.error(msg)
        return msg
    
def create_test_db():
    """
    Create a test SQLite database for API & unit testing.
    """
    test_prj_name = os.getenv("TEST_PROJECT_NAME")
    if not test_prj_name:
        logging.info("TEST_PROJECT_NAME environment variable is not set. Skip test database creation.")
        return
    
    test_db_name = f"{test_prj_name}.db"
    db_dir = os.getenv("DB_DIR", "databases")
    os.makedirs(db_dir, exist_ok=True)

    db_path = os.path.join(db_dir, test_db_name)
    if os.path.exists(db_path):
        logging.info(f"Test database '{test_db_name}' already exists at {db_path}. Skip creation.")
        return

    try:
        # Initialize the database
        init_project_db(test_prj_name)
        
        ticket_json = '{"ticket_id": "TICKET-1", "summary": "Test Ticket", "description": "This is a test ticket.", "status": "Open", "priority": "High", "reporter": "Marry", "assignee": "John Doe", "created": "2025-05-01", "updated": "2025-05-03"}'
        result = add_ticket(test_prj_name, ticket_json)
        ## add more tickets
        ticket_json2 = '{"ticket_id": "TICKET-2", "summary": "Another Ticket", "description": "This is finished ticket.", "status": "In Progress", "priority": "Medium", "reporter": "Alice", "assignee": "Bob", "created": "2025-05-01", "updated": "2025-05-02"}'
        result = add_ticket(test_prj_name, ticket_json2)
        msg = f"Succ: Created Test database '{test_db_name}' initialized at {db_path}"
        logging.info(msg)
        return msg
    except Exception as e:
        msg = f"Err103: Error initializing test database: {e}"
        logging.error(msg)
        return msg