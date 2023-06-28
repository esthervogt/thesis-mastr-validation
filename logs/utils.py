from loguru import logger
from datetime import datetime as dt
from pathlib import Path
import os

def start_logging(filename) -> logger:
    logger.remove(0)
    logger.add(Path('logs') / Path(f"{os.path.relpath(filename, os.getcwd()).replace('.py', '')}.log"))
    logger.info(
        f"*************************** Start log: {dt.now().strftime('%y-%m-%d %H:%M:%S')} ****************************")
