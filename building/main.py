import argparse
import os
from loguru import logger
import config as cfg
from building import Buildings, get_base
from ref_area import ZipBorders
from images import ImgMetadata
from db import engine, get_model_column_names, setup_docker
from logs.utils import start_logging
from sqlalchemy import Integer, ARRAY, String, func, inspect
from sqlalchemy.schema import DropTable
from sqlalchemy.sql import cast
from sqlalchemy.orm import Session
from geoalchemy2.types import Geography


def get_raw_data(use_existing: bool = False):

    raw_data_dir = os.path.join(os.path.expanduser("~"), ".osm", "data", "osm")

    if not os.path.exists(raw_data_dir):
        os.makedirs(raw_data_dir)

    if use_existing:
        filepath = os.path.join(raw_data_dir, "bayern-latest.osm.pbf")
    # else:
    #     filepath = get_data("bayern", directory=raw_data_dir)
    logger.info(f"Using OSM data from filepath: {filepath}")

    setup_docker(engine=engine)
    with engine.connect() as con:
        con.execute("CREATE EXTENSION IF NOT EXISTS hstore;")

    pbf_to_td = [
        "ogr2ogr",
        # Delete the output layer and recreate it empty
        "-overwrite",
        # Display progress on terminal. Only works if input layers have the “fast feature count capability”
        "-progress",
        # SQL statement to execute. The resulting table/layer will be saved to the output.
        "-sql",
        "\"select osm_id, building, name, amenity, barrier, historic, landuse, other_tags from multipolygons "
        "where building is not null\"",
        # Output file format name
        "-f", "PostgreSQL",
        # dst_datasource_name
        f"\"PG:dbname=mastrdb user=mastrdb password=mastrdb schemas=public host='127.0.0.1'port='5500'\"",
        # src_datasource_name
        filepath,
        # Layer creation option (format specific)
        "-lco", "COLUMN_TYPES=other_tags=hstore",
        # Assign an alternate name to the new layer
        "-nln", "osm_building_raw",
        # Reproject/transform to this SRS on output, and assign it as output SRS.
        "-t_srs", "EPSG:4326",
        "-lco", "geometry_name=geom"
    ]
    logger.info(f"Extracting OSM PBF data using ogr2ogr command: {' '.join(pbf_to_td)}")
    # subprocess.run(pbf_to_td)

    logger.success("Raw OSM Building data written to schema 'public'.")

def get_ref_area_data(base) -> None:
    """
    The query used in this method:
    - keeps only buildings intersecting with the zip code boundaries
    - keeps all buildings independent of intersection with image boundaries
    """
    with Session(engine) as session:
        query = (session
            .query(
                base.ogc_fid,
                base.geometry,
                func.array_agg(func.distinct(ZipBorders.zip_code, type_=ARRAY(Integer))).label('zip_codes'),
                func.array_agg(func.distinct(ImgMetadata.img_name, type_=ARRAY(String))).label('img_names'))
            .distinct()
            .add_columns(func.ST_Area(cast(base.geometry, Geography(srid=cfg.EPSG_TARGET)), True).label('geom_sqm'))
            .join(ZipBorders, ZipBorders.geom.ST_Intersects(base.geometry))
            .outerjoin(ImgMetadata, ImgMetadata.geom.ST_Intersects(base.geometry))
            .group_by(base.ogc_fid, base.geometry))

        insert_stmt = Buildings.__table__.insert().from_select(
            names=get_model_column_names(Buildings),
            select=query)
        session.execute(insert_stmt)
        session.commit()

def main(use_existing_src_file: bool = False, create_base: bool = True) -> None:
    BuildingsBase = get_base()
    if create_base:
        engine.execute(DropTable(BuildingsBase.__table__, if_exists=True))
    if not inspect(engine).has_table(BuildingsBase.__table__):
        get_raw_data(use_existing_src_file)
    get_ref_area_data(base=BuildingsBase)


if __name__ == "__main__":
    start_logging(__file__)

    parser = argparse.ArgumentParser(description='Download raw MaStR data to PG DB.')
    parser.add_argument('--use_existing_src_file',
                        help='Specify whether an existing pbf file should be used to (re-)create the raw data.',
                        action='store_false')
    parser.add_argument('--create_base',
                        help='Specify whether the raw data should be extracted again to the public schema.',
                        action='store_true')
    args = parser.parse_args()

    main(use_existing_src_file=args.use_existing_src_file, create_base=args.create_base)
