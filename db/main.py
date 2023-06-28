import argparse
from logs.utils import start_logging, logger
from db.base import Base
from db import engine, create_schema, start_database
from building import Buildings
from images import ImgMetadata, ImgRoofDetections, ImgWindowClips
from mapping import MastrPerBuilding, RoofDetectionsPerMastr, RoofDetectionsPerBuilding
from mastr import MastrSolar
from ref_area import ZipBorders

def main(drop_results: bool = True) -> None:
    """
    Creates/deletes all tables and schemata that are used to store the results of processing of the raw source data.
    This requires to import all models subclassing the Base model, although they are not used explicitly.
    """
    start_database()
    if drop_results:
        Base.metadata.drop_all(engine)
    for schema in Base.metadata._schemas:
        create_schema(schema)
    Base.metadata.create_all(engine)
    logger.info(f'Loaded models: {Buildings, ImgMetadata, ImgRoofDetections, ImgWindowClips, MastrPerBuilding, RoofDetectionsPerMastr, RoofDetectionsPerBuilding, MastrSolar, ZipBorders}')


if __name__ == "__main__":
    start_logging(__file__)

    parser = argparse.ArgumentParser(description='Download raw MaStR data to PG DB.')
    parser.add_argument('--drop_results',
                        help='Specify whether result tables should be dropped and thus re-created or kept if they exist.',
                        action='store_true')
    args = parser.parse_args()

    main(drop_results=args.drop_results)
