import logging
import sys


def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logger/bot.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger()
