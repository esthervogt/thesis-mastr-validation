import sqlalchemy as db
from sqlalchemy import inspect
from sqlalchemy.schema import CreateSchema
import pandas as pd
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import DropTable
from db.base import engine
from db import setup_docker

def start_database():
    setup_docker(engine=engine, delete_container=False)

def create_schema(schema:str) -> None:
    if not engine.dialect.has_schema(engine, schema):
        engine.execute(CreateSchema(schema))

def as_dict(obj) -> dict:
    data = obj.__dict__
    data.pop('_sa_instance_state')
    return data

def get_model_column_for_mapped_name(model, mapped_name: str) -> str:
    mapped_object = inspect(model)
    return [v.name for k,v in mapped_object.columns.items() if k == mapped_name][0]

def get_model_column_names(model, exclude: list[str] = None) -> list[str]:
    with engine.connect() as conn:
        result = conn.execute(db.select(model))
    if exclude is not None and exclude:
        return [i for i in result.keys() if i not in exclude]
    return list(result.keys())

@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    """
    This function is relevant to allow dropping tables with foreign key constraints.
    """
    return f"{compiler.visit_drop_table(element)} CASCADE"