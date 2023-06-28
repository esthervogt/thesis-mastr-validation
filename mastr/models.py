import config as cfg
from sqlalchemy import Column, Integer, String, Date, Float
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.automap import automap_base
from geoalchemy2 import Geometry
from db import engine, as_dict
from building.models import Buildings
from db.base import Base

def get_base():
    BaseAutomap = automap_base()
    BaseAutomap.prepare(engine, reflect=True)

    SolarExtended = BaseAutomap.classes.solar_extended
    SolarExtended.as_dict = as_dict
    return SolarExtended

class MastrSolar(Base):
    __tablename__ = 'solar_units'
    __table_args__ = {"schema": cfg.SCHEMA_MASTR}

    einheitmastrnummer = Column('EinheitMastrNummer', String, primary_key=True)
    datumdownload = Column('DatumDownload', Date)
    registrierungsdatum = Column('Registrierungsdatum', Date)
    inbetriebnahmedatum = Column('Inbetriebnahmedatum', Date)
    netzbetreiberpruefungdatum = Column('NetzbetreiberpruefungDatum', Date)
    netzbetreiberpruefungstatus = Column('NetzbetreiberpruefungStatus', String)
    einheitbetriebsstatus = Column('EinheitBetriebsstatus', String)
    bruttoleistung = Column('Bruttoleistung', Float)
    nettonennleistung = Column('Nettonennleistung', Float)
    anzahlmodule = Column('AnzahlModule', Integer)
    lage = Column('Lage', String)
    hauptausrichtung = Column('Hauptausrichtung', String)
    hauptausrichtungneigungswinkel = Column('HauptausrichtungNeigungswinkel', String)
    geom = Column(cfg.COL_GEOMETRY, Geometry(geometry_type='POINT', srid=4326))

    building = relationship(
        Buildings,
        primaryjoin='func.ST_Contains(foreign(Buildings.geom), MastrSolar.geom).as_comparison(1, 2)',
        backref=backref(__tablename__, uselist=True),
        viewonly=True,
        uselist=True,
    )
