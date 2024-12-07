import logging
import sys
import os

LOG_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "bot.log"))

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE_PATH),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger()
