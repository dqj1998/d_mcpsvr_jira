import logging
import os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

def init_logger():
    """
    Initializes the logger with configurations from environment variables.
    """
    load_dotenv()

    # Get logging configurations from environment variables
    log_dir = os.getenv("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.getenv("LOG_FILE_PATH", os.path.join(log_dir, "project.log"))
    log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s")
    log_file_size = int(os.getenv("LOG_FILE_SIZE", 10485760))  # Default to 10MB
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", 5))  # Default to 5 backups

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, 'DEBUG', logging.DEBUG),
        format=log_format,
        handlers=[
            RotatingFileHandler(log_file_path, maxBytes=log_file_size, backupCount=backup_count),
            logging.StreamHandler(),
        ]
    )
