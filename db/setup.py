from sqlalchemy import create_engine
from config import DB_CONN
from docker import setup_docker

def create_database():
    engine = create_engine(DB_CONN, execution_options={"schema_translate_map":{None: "public"}})
    setup_docker(engine=engine, delete_container=False)

if __name__ == "__main__":
    create_database()