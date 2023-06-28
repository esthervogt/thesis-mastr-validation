import config as cfg
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.dialects.postgresql import ARRAY
from geoalchemy2 import Geometry
from db.base import Base
from building.models import Buildings
from mastr.models import MastrSolar


class MastrPerBuilding(Base):
    __tablename__ = 'mastr_building'
    __table_args__ = {"schema": cfg.SCHEMA_MAPPING}

    einheitmastrnummer = Column('EinheitMastrNummer', String, ForeignKey(MastrSolar.einheitmastrnummer), primary_key=True)
    geom = Column(cfg.COL_GEOMETRY, Geometry(geometry_type='POINT', srid=4326))
    ogc_fid = Column('ogc_fid', Integer, ForeignKey(Buildings.ogc_fid), primary_key=True)

class RoofDetectionsPerBuilding(Base):
    __tablename__ = 'roof_detections_building'
    __table_args__ = {"schema": cfg.SCHEMA_MAPPING}

    ogc_fid = Column('ogc_fid', Integer, ForeignKey(Buildings.ogc_fid), primary_key=True)
    geom = Column(cfg.COL_GEOMETRY, Geometry())
    index = Column('idx', ARRAY(Integer))
    img_name = Column('img_name', ARRAY(String))
    geom_sqm = Column('geom_sqm', Float)
    panelcount_low = Column('pc_low', Float)
    panelcount_high = Column('pc_high', Float)
    cap_low = Column('cap_low', Float)
    cap_high = Column('cap_high', Float)

class RoofDetectionsPerMastr(Base):
    __tablename__ = 'roof_detections_mastr'
    __table_args__ = {"schema": cfg.SCHEMA_MAPPING}

    einheitmastrnummer = Column('EinheitMastrNummer', String, ForeignKey(MastrSolar.einheitmastrnummer),
                                primary_key=True)
    geom_mastr = Column(f'{cfg.COL_GEOMETRY}_mastr', Geometry(geometry_type='POINT', srid=4326))
    ogc_fid = Column('ogc_fid', Integer, ForeignKey(Buildings.ogc_fid), primary_key=True)
    geom_roof_detection = Column(f'{cfg.COL_GEOMETRY}_rd', Geometry())
    img_name = Column('img_name', ARRAY(String))
