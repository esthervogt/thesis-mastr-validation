import config as cfg
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, Session
from geoalchemy2 import Geometry
from db import engine
from db.base import Base
import geopandas as gpd

class ImgMetadata(Base):
    """
    This class is helpful for plotting the spatial extent of each image, i.e. in QGis.
    """
    __tablename__ = 'metadata'
    __table_args__ = {"schema": cfg.SCHEMA_IMAGES}

    img_name = Column('name', String, primary_key=True)
    geom = Column(cfg.COL_GEOMETRY, Geometry(geometry_type='POLYGON', srid=4326))
    dir_path = Column('dir', String)
    file_path = Column('file', String)

    window_clips = relationship('ImgWindowClips', cascade="all,delete", backref="img")

    @classmethod
    def get_all(cls) -> gpd.GeoDataFrame:
        with Session(engine) as session:
            query = session.query(cls)
            return gpd.read_postgis(query.statement, engine)

class ImgWindowClips(Base):
    """
    This class is helpful for plotting the spatial extent of all window clips per image, i.e. in QGis.
    """
    __tablename__ = 'window_clips'
    __table_args__ = {"schema": cfg.SCHEMA_IMAGES}

    index = Column('idx', Integer, primary_key=True)
    geom = Column(cfg.COL_GEOMETRY, Geometry(geometry_type='POLYGON', srid=4326))
    column_offset = Column('col_off', Integer)
    row_offset = Column('row_off', Integer)
    width = Column('width', Integer)
    height = Column('height', Integer)

    img_name = Column('img_name', String, ForeignKey(ImgMetadata.img_name), primary_key=True)

    @classmethod
    def get_all(cls) -> gpd.GeoDataFrame:
        with Session(engine) as session:
            query = session.query(cls)
            return gpd.read_postgis(query.statement, engine)

    @classmethod
    def get_single_img_clips(cls, img_name: str) -> gpd.GeoDataFrame:
        with Session(engine) as session:
            query = session.query(cls).filter(cls.img_name == img_name)
            return gpd.read_postgis(query.statement, engine)

class ImgRoofDetections(Base):
    """
    This class models all detections found on buildings roofs
    """
    __tablename__ = 'roof_detections'
    __table_args__ = {"schema": cfg.SCHEMA_IMAGES}

    index = Column('idx', Integer, primary_key=True)
    geom = Column(cfg.COL_GEOMETRY, Geometry(geometry_type='POLYGON', srid=4326))
    ogc_fid = Column('ogc_fid', ARRAY(Integer))

    img_name = Column('img_name', String, ForeignKey(ImgMetadata.img_name), primary_key=True)
