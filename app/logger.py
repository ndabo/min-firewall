"""
Log requests and threats
- incoming requests (with IP, prompt, timestamp, etc.) are logged at the INFO level.
- Threats are logged at the WARNING level.
- Logs are saved to mif_logs.log file
"""
import csv
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import pathlib
import sys

# Create logs directory if it doesn't exist
LOG_DIR = pathlib.Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "mif-firewall.log"

#ncoming requests (with IP, prompt, timestamp, etc.) are logged at the INFO level.
# Threats are logged at the WARNING level.
def get_logger(name:str)->logging.Logger:
    logger = logging.getLogger(name)
    #avoid duplicate handlers
    if logger.hasHandlers():
        return logger
    logger.setLevel(logging.DEBUG)  # Capture DEBUG+; filter later in handlers

    #rotating file handler
    file_handler = RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=10*1024*1024, #10MB
        backupCount=3 #keep 3 backups
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger
    
