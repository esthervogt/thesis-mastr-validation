import os
import subprocess
import time
from loguru import logger
import sqlalchemy
from sqlalchemy import exc


def setup_docker(engine, delete_container: bool = False) -> None:
    """Initialize a PostgreSQL database with docker-compose"""
    conf_file_path = os.path.abspath(os.path.dirname(__file__))

    if delete_container:

        subprocess.run(
            ["docker", "rm", "-f", "etwin"],
            cwd=conf_file_path,
        )
        try:
            subprocess.run(
                ["docker", "volume", "rm", "-f", "etwinetl_etwinVolume"],
            )
        except FileNotFoundError:
            logger.error("Command 'docker volume rm' could not find the volume to delete.")

    subprocess.run(
        ["docker-compose", "up", "-d"],
        cwd=conf_file_path,
    )
    test_connection(engine=engine)
    logger.success("Dockered database is up and running!")


def test_connection(engine: sqlalchemy.engine.Engine) -> None:
    """Test connection to the specified database

    Parameters
    ----------
    engine : sqlalchemy.engine.Engine
        Engine of the database
    """
    counter_connection_test = 0
    number_total_retries = 5
    while counter_connection_test < number_total_retries:
        try:
            connection = engine.connect()
            connection.close()
            logger.success("Dockerized database was started and can be accessed.")
            return None
        except exc.DBAPIError:
            time.sleep(3)
            counter_connection_test += 1
            logger.warning(
                "Connection to database could not be established."
                f" Retries {counter_connection_test}/{number_total_retries}"
            )
