from sqlalchemy.ext.automap import automap_base

import config as cfg
from sqlalchemy import Column, Integer, Float, String
from sqlalchemy.dialects.postgresql import ARRAY
from geoalchemy2 import Geometry
from db import as_dict
from db.base import Base, engine

def get_base():
    BaseAutomap = automap_base()
    BaseAutomap.prepare(engine, reflect=True)

    BuildingsBase = BaseAutomap.classes.osm_building_raw
    BuildingsBase.as_dict = as_dict
    return BuildingsBase

class Buildings(Base):
    __tablename__ = 'layout'
    __table_args__ = {"schema": cfg.SCHEMA_BUILDINGS}

    ogc_fid = Column('ogc_fid', Integer, primary_key=True)
    geom = Column(cfg.COL_GEOMETRY, Geometry(geometry_type='MultiPolygon', srid=4326))
    zip_codes = Column('zip_codes', ARRAY(String))
    img_names = Column('img_names', ARRAY(String))
    geom_sqm = Column(cfg.COL_GEOMETRY_AREA, Float)
