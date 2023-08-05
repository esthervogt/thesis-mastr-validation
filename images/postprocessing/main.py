import numpy as np
from rasterio import DatasetReader
import rasterio.features as rf
from sqlalchemy.orm import Session
from sqlalchemy import select
from building.models import Buildings
from images.models import ImgMetadata, ImgRoofDetections
from images.utils import prediction_exists, get_img, get_img_tif_ds_reader_from_dir, get_results_file_path
from logs.utils import start_logging
from db import engine, get_model_column_for_mapped_name
import config as cfg
import geopandas as gpd
from shapely.geometry import shape, MultiPolygon

def detection_exists(img_name: str) -> bool:
    with Session(engine) as session:
        stmt = select(ImgRoofDetections.index).where(ImgRoofDetections.img_name == img_name)
        return len(session.execute(stmt).fetchall()) > 0

def load_pred_mask(img_tif_ds: DatasetReader) -> np.ndarray:
    return get_img(img_tif_ds)

def extract_detections(pred_mask: np.ndarray, img_tif_ds: DatasetReader) -> gpd.GeoDataFrame:
    detections = (pred_mask == 1).astype(np.uint8)
    panel_polygons = [
        img_shape
        for img_shape, img_value in rf.shapes(
            detections, transform=img_tif_ds.profile['transform']
        )
        if img_value == 1
    ]
    detection_polygons = MultiPolygon([shape(s) for s in panel_polygons])
    detection_polygons_gdf = gpd.GeoDataFrame(detection_polygons, columns=[cfg.COL_GEOMETRY], geometry=cfg.COL_GEOMETRY, crs=cfg.EPSG_SOURCE)
    detection_polygons_gdf.to_crs(crs=f"EPSG:{cfg.EPSG_TARGET}", inplace=True)
    detection_polygons_gdf = _threshold_geom_area(detection_polygons_gdf)
    return detection_polygons_gdf

def _threshold_geom_area(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Exclude detections smaller than expected size of single panel
    """
    gdf[cfg.COL_GEOMETRY_AREA] = gdf[cfg.COL_GEOMETRY].to_crs('epsg:32633').map(lambda p: p.area)
    gdf = gdf.loc[gdf[cfg.COL_GEOMETRY_AREA] >= cfg.DETECTION_SQM_TH]
    gdf.drop(columns=cfg.COL_GEOMETRY_AREA, inplace=True)
    return gdf

def add_building_reference(img_name: str, detections_gdf: gpd.GeoDataFrame = None) -> gpd.GeoDataFrame:
    """
    Perform spatial join between detected panel and osm building polygons: only keep detections with join to buildings
    """
    with Session(engine) as session:
        buildings_in_image_query = session.query(Buildings.ogc_fid, Buildings.geom)\
            .distinct()\
            .filter(Buildings.img_names.contains([img_name]))
        buildings_in_image_gdf = gpd.read_postgis(
            sql=buildings_in_image_query.statement, con=buildings_in_image_query.session.bind)
        return _remove_detections_wo_buildings(detections_gdf, buildings_in_image_gdf)


def _remove_detections_wo_buildings(detections_gdf, buildings_in_image_gdf):
    """"
    Filter on detections being positioned on a building and add the corresponding building ids
    """
    detections_with_buildings_gdf = gpd.sjoin(
        detections_gdf, buildings_in_image_gdf, how='inner', predicate='intersects')
    detections_with_buildings_gdf.drop(columns='index_right', inplace=True)
    detections_with_buildings_gdf.drop_duplicates(inplace=True)
    detections_with_buildings_gdf[cfg.COL_GEOMETRY] = detections_with_buildings_gdf[cfg.COL_GEOMETRY].to_wkt()
    detections_with_buildings_gdf = detections_with_buildings_gdf\
        .groupby(detections_with_buildings_gdf[cfg.COL_GEOMETRY])\
        [get_model_column_for_mapped_name(Buildings, 'ogc_fid')]\
        .apply(list)\
        .reset_index()
    detections_with_buildings_gdf[get_model_column_for_mapped_name(Buildings, 'ogc_fid')] = detections_with_buildings_gdf[get_model_column_for_mapped_name(Buildings, 'ogc_fid')].apply(lambda x: set(x))
    detections_with_buildings_gdf[cfg.COL_GEOMETRY] = gpd.GeoSeries.from_wkt(detections_with_buildings_gdf[cfg.COL_GEOMETRY], crs=f"EPSG:{cfg.EPSG_TARGET}")
    return gpd.GeoDataFrame(detections_with_buildings_gdf, crs=f"EPSG:{cfg.EPSG_TARGET}", geometry=cfg.COL_GEOMETRY)

def format_detections_gdf_to_model(img_name:str, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf.index.names = [get_model_column_for_mapped_name(ImgRoofDetections, 'index')]
    gdf.reset_index(inplace=True)
    gdf[get_model_column_for_mapped_name(ImgRoofDetections, 'img_name')] = img_name
    return gdf

def get_detections_gdf_from_pred_mask(img_name:str, img_tif_ds: DatasetReader) -> gpd.GeoDataFrame:
    return format_detections_gdf_to_model(img_name, add_building_reference(img_name, extract_detections(load_pred_mask(img_tif_ds), img_tif_ds)))


def run_postprocessing_for_image(img_name:str) -> None:
    if prediction_exists(img_name) and not detection_exists(img_name):
        tif_ds_reader = get_img_tif_ds_reader_from_dir(get_results_file_path(cfg.DIR_NAME_RESULTS_PRED_MASK), img_name)
        detection_gdf = get_detections_gdf_from_pred_mask(img_name, tif_ds_reader)

        detection_gdf.to_postgis(
            con=engine,
            name=ImgRoofDetections.__tablename__,
            schema=ImgRoofDetections.__table_args__['schema'],
            if_exists='append',
            index=False,
            chunksize=100)

def main() -> None:
    for img_metadata in ImgMetadata.get_all().iterrows():
        run_postprocessing_for_image(
            img_name=img_metadata[1][get_model_column_for_mapped_name(ImgMetadata, 'img_name')],)

if __name__ == "__main__":
    start_logging(__file__)
    main()
