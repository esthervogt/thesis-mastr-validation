import config as cfg
from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.automap import automap_base
from geoalchemy2 import Geometry
from db import engine, as_dict
from db.base import Base

def get_base():
    BaseAutomap = automap_base()
    BaseAutomap.prepare(engine, reflect=True)

    ZipBordersBase = BaseAutomap.classes.zip_borders_raw
    ZipBordersBase.as_dict = as_dict
    return ZipBordersBase

class ZipBorders(Base):
    __tablename__ = 'zip_borders'
    __table_args__ = {"schema": cfg.SCHEMA_REFERENCE_AREA}

    zip_code = Column('zip_code', String, primary_key=True)
    index = Column('index', Integer, primary_key=True)
    geom = Column(cfg.COL_GEOMETRY, Geometry(geometry_type='POLYGON', srid=4326))
