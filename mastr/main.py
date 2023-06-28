import argparse
from loguru import logger
from open_mastr import Mastr
import config as cfg
from models import MastrSolar, get_base
from db import engine, get_model_column_names
from sqlalchemy.orm import Session
from logs.utils import start_logging
from sqlalchemy import func

def get_raw_data(existing_file_date:str=None) -> None:
    """
    Download a xml file called "Gesamtdatenexport_yyyymmdd.zip" to the directory root\.open-MaStR.
    The file is preprocessed and data written to the corresponding tables in the PG DB (schema: public).
    :param existing_file_date: If specified in the format "yyyymmdd" an existing download should be used.
    :return:
    """
    logger.info("Starting download of MaStR Data.")
    db = Mastr(engine=engine)
    db.download(
        method='bulk',
        data=["solar", "storage"],
        date=existing_file_date,
        bulk_cleansing=True
    )
    logger.success(f"MaStR Data written to schema={cfg.SCHEMA_RAW_DATA}.")

def get_ref_area_data(base) -> None:
    with Session(engine) as session:

        query = session \
            .query(base.EinheitMastrNummer, base.DatumDownload, base.Registrierungsdatum,
                   base.Inbetriebnahmedatum, base.NetzbetreiberpruefungDatum,
                   base.NetzbetreiberpruefungStatus, base.EinheitBetriebsstatus,
                   base.Bruttoleistung, base.Nettonennleistung, base.AnzahlModule,
                   base.Lage, base.Hauptausrichtung, base.HauptausrichtungNeigungswinkel) \
            .filter(base.Landkreis == 'München', base.Nettonennleistung > 30) \
            .add_columns((func.ST_SetSRID(func.ST_MakePoint(base.Laengengrad, base.Breitengrad), 4326)).label(
            cfg.COL_GEOMETRY))

        insert_stmt = MastrSolar.__table__.insert().from_select(
            names=get_model_column_names(MastrSolar),
            select=query)
        session.execute(insert_stmt)
        session.commit()

def main(date: str = None, create_base: bool = False) -> None:
    SolarExtended = get_base()
    if create_base:
        get_raw_data(existing_file_date=date)
    get_ref_area_data(base=SolarExtended)


if __name__ == "__main__":
    start_logging(__file__)

    parser = argparse.ArgumentParser(description='Download raw MaStR data to PG DB.')
    parser.add_argument('--date',
                        help='Specify a datetime of format "yyyymmdd" if an existing download should be used.',
                        type=str,
                        default=None)
    parser.add_argument('--create_base',
                        help='Specify whether the raw data should be extracted again to the public schema.',
                        action='store_true')
    args = parser.parse_args()

    main(date=args.date, create_base=args.create_base)
