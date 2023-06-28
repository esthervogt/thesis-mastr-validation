import argparse

from models import ZipBorders, get_base
from db import engine, get_model_column_names
from sqlalchemy.orm import Session
from logs.utils import start_logging
import geopandas as gpd
import config as cfg

def get_raw_data() -> None:
    df = gpd.read_file(cfg.FILE_ZIP_CODE_BORDERS, dtype={'plz': str})
    if 'OBJECTID' in df.columns:
        df.drop(columns='OBJECTID', inplace=True)
    df['plz_idx'] = df.groupby(['plz'])['ort'].rank(method="first", ascending=True).astype(int)
    df.to_crs(crs=f"EPSG:{cfg.EPSG_TARGET}", inplace=True)

    table_name = 'zip_borders_raw'
    df.to_postgis(con=engine,name=table_name, schema=cfg.SCHEMA_RAW_DATA, if_exists='replace', index=False, chunksize=100)
    with engine.connect() as con:
        con.execute(f'ALTER TABLE {cfg.SCHEMA_RAW_DATA}.{table_name} ADD PRIMARY KEY (plz, plz_idx);')

def get_ref_area_data(base) -> None:
    with Session(engine) as session:
        query = session.query(base.plz, base.plz_idx,  base.geometry)

        insert_stmt = ZipBorders.__table__.insert().from_select(
            names=get_model_column_names(ZipBorders),
            select=query)
        session.execute(insert_stmt)
        session.commit()

def main(create_base: bool = False) -> None:
    ZipBordersBase = get_base()
    if create_base:
        get_raw_data()
    get_ref_area_data(base=ZipBordersBase)


if __name__ == "__main__":
    start_logging(__file__)

    parser = argparse.ArgumentParser(description='Download raw MaStR data to PG DB.')
    parser.add_argument('--create_base',
                        help='Specify whether the raw data should be extracted again to the public schema.',
                        action='store_true')
    args = parser.parse_args()

    main(create_base=args.create_base)
