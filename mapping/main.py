from geoalchemy2 import Geography
import config as cfg
from mastr.models import MastrSolar
from building.models import Buildings
from mapping.models import MastrPerBuilding, RoofDetectionsPerBuilding, RoofDetectionsPerMastr
from images.models import ImgRoofDetections
from db import engine, get_model_column_names, get_model_column_for_mapped_name
from logs.utils import start_logging
from sqlalchemy import func, Column, Numeric
from sqlalchemy.sql import cast
from sqlalchemy.orm import Session


def map_mastr_units_to_buildings() -> None:
    """
    Creates an n:n mapping between solar MaStR units and buildings
    """

    with Session(engine) as session:
        query = session\
            .query(MastrSolar.einheitmastrnummer,MastrSolar.geom, Buildings.ogc_fid)\
            .distinct()\
            .join(MastrSolar.building)\

        insert_stmt = MastrPerBuilding.__table__.insert().from_select(
            names=get_model_column_names(MastrPerBuilding),
            select=query)
        session.execute(insert_stmt)
        session.commit()

def map_detections_to_buildings() -> None:
    """
    This method serves to unify all detections per building in contrast to the src table for the detections.
    """

    with Session(engine) as session:
        query_distinct_detections = (
            session.query(
                ImgRoofDetections.index, ImgRoofDetections.geom, ImgRoofDetections.img_name,
                func.unnest(ImgRoofDetections.ogc_fid).label('ogc_fid'))
            .distinct()
            .subquery())

        query_grouped_detections_per_building = (
            session.query(
                func.array_agg(func.distinct(ImgRoofDetections.index)).label(
                    get_model_column_for_mapped_name(ImgRoofDetections, 'index')),
                Column('ogc_fid'),
                func.ST_UNARYUNION(func.ST_Collect(ImgRoofDetections.geom)).label(get_model_column_for_mapped_name(ImgRoofDetections, 'geom')),
                func.array_agg(func.distinct(ImgRoofDetections.img_name)).label(get_model_column_for_mapped_name(ImgRoofDetections, 'img_name')),
            )
            .select_entity_from(query_distinct_detections)
            .group_by('ogc_fid')
            .subquery()
        )

        query_area_calculation = (
            session.query(
                query_grouped_detections_per_building,
                func.ST_Area(cast(Column('geom'), Geography(srid=cfg.EPSG_TARGET)), True).label('geom_sqm')
            )
            .select_entity_from(query_grouped_detections_per_building)
            .subquery()
        )

        query_estimation = (
            session.query(
                Column('idx'),
                func.round(cast(Column('geom_sqm') / cfg.SQM_PER_PANEL_LOW, Numeric), 3).label('pc_low'),
                func.round(cast(Column('geom_sqm') / cfg.SQM_PER_PANEL_HIGH, Numeric), 3).label('pc_high'),
                Column('ogc_fid'), Column('geom'), Column('img_name'), Column('geom_sqm'),
                func.round(cast(Column('geom_sqm') * cfg.CAP_PER_PANEL_LOW / cfg.SQM_PER_PANEL_LOW, Numeric), 3).label('cap_low'),
                func.round(cast(Column('geom_sqm') * cfg.CAP_PER_PANEL_HIGH / cfg.SQM_PER_PANEL_LOW, Numeric), 3).label('cap_high')
            )
            .select_entity_from(query_area_calculation)
        )

        insert_stmt = RoofDetectionsPerBuilding.__table__.insert().from_select(
            names=get_model_column_names(RoofDetectionsPerBuilding),
            select=query_estimation)
        session.execute(insert_stmt)
        session.commit()

def map_mastr_units_to_detections() -> None:
    """
    This method serves to create n:n mappings between all unified detections per building and each MaStR unit mapped to it.
    As such, the same building (and all detections mapped to it) can map to several MaStR units.
    """

    with Session(engine) as session:
        query = (session
                 .query(
                    MastrPerBuilding.einheitmastrnummer,
                    RoofDetectionsPerBuilding.geom.label(get_model_column_for_mapped_name(RoofDetectionsPerMastr, 'geom_roof_detection')),
                    MastrPerBuilding.geom.label(get_model_column_for_mapped_name(RoofDetectionsPerMastr, 'geom_mastr')),
                    MastrPerBuilding.ogc_fid,
                    RoofDetectionsPerBuilding.img_name,
                    )
                 .join(RoofDetectionsPerBuilding, MastrPerBuilding.ogc_fid == RoofDetectionsPerBuilding.ogc_fid)
        )

        insert_stmt = RoofDetectionsPerMastr.__table__.insert().from_select(
            names=get_model_column_names(RoofDetectionsPerMastr),
            select=query)
        session.execute(insert_stmt)
        session.commit()


def main() -> None:
    map_mastr_units_to_buildings()
    map_detections_to_buildings()
    map_mastr_units_to_detections()


if __name__ == "__main__":
    start_logging(__file__)
    main()
