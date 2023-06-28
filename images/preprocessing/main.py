import itertools
import pandas as pd
from db import engine, get_model_column_for_mapped_name
from logs.utils import start_logging
from pathlib import Path
from typing import List
import geopandas as gpd
import rasterio
from rasterio.windows import Window
import config as cfg
from images import ImgMetadata, ImgWindowClips, get_window_from_dict, get_img_tif_ds_reader_from_dir
from shapely.geometry import box
from loguru import logger


def get_img_metadata_from_tif_files(dir_path: str) -> gpd.GeoDataFrame:
    if type(dir_path) == str:
        dir_path = Path(dir_path)
    src_files = get_tif_files_in_dir(dir_path)
    metadata_dict_list = []
    for file in src_files:
        img_tif_ds = rasterio.open(file)
        file_dict = {
            get_model_column_for_mapped_name(ImgMetadata, 'img_name'): file.name.replace('.tif', ''),
            cfg.COL_GEOMETRY: get_polygon_from_boundary_coords(
                bottom_left=f"{img_tif_ds.bounds.left}:{img_tif_ds.bounds.bottom}",
                top_right=f"{img_tif_ds.bounds.right}:{img_tif_ds.bounds.top}"),
            get_model_column_for_mapped_name(ImgMetadata, 'dir_path'): dir_path.__str__(),
            get_model_column_for_mapped_name(ImgMetadata, 'file_path'): file.name
        }
        metadata_dict_list.append(file_dict)
    return get_gdf_from_dict(metadata_dict_list)

def get_tif_files_in_dir(dir_path: Path) -> List[Path]:
    return list(dir_path.glob('**/*.tif'))

def get_gdf_from_dict(geo_dict: List[dict]) -> gpd.GeoDataFrame:
    gpd_gdf = gpd.GeoDataFrame(geo_dict, geometry=cfg.COL_GEOMETRY, crs=f"EPSG:{cfg.EPSG_SOURCE}")
    gpd_gdf.to_crs(crs=f"EPSG:{cfg.EPSG_TARGET}", inplace=True)
    return gpd_gdf

def get_polygon_from_boundary_coords(bottom_left: str, top_right: str) -> box:
    return box(minx=float(bottom_left.split(":")[0]),
               miny=float(bottom_left.split(":")[1]),
               maxx=float(top_right.split(":")[0]),
               maxy=float(top_right.split(":")[1]),
               ccw=True)

def set_img_window_clips_gdf(img_tif_ds: rasterio.DatasetReader, img_name: str) -> gpd.GeoDataFrame:
    clips = []
    try:
        for y, x in itertools.product(range(0, img_tif_ds.shape[0], cfg.STRIDE), range(0, img_tif_ds.shape[1], cfg.STRIDE)):
            window = {'col_off': x, 'row_off': y, 'width': cfg.IMSIZE_MODEL_IN, 'height': cfg.IMSIZE_MODEL_IN}
            clips.append(window)
        return get_gdf_from_img_window_clips(clips=clips, img_tif_ds=img_tif_ds, img_name=img_name)
    except AttributeError as ae:
        logger.error(ae)

def get_gdf_from_img_window_clips(clips: list, img_tif_ds: rasterio.DatasetReader, img_name: str) -> gpd.GeoDataFrame:
    df = pd.DataFrame(clips)
    df[cfg.COL_GEOMETRY] = df.apply(
        lambda x: box(*rasterio.windows.bounds(get_window_from_dict(x), img_tif_ds.transform), ccw=True), axis=1)
    df[get_model_column_for_mapped_name(ImgWindowClips, 'img_name')] = img_name
    gdf = gpd.GeoDataFrame(df, geometry=cfg.COL_GEOMETRY, crs=img_tif_ds.crs)
    gdf.to_crs(crs=f"EPSG:{cfg.EPSG_TARGET}", inplace=True)
    if (
        get_model_column_for_mapped_name(ImgWindowClips, 'index')
        not in gdf.columns
    ):
        gdf.index.names = [get_model_column_for_mapped_name(ImgWindowClips, 'index')]
        gdf.reset_index(inplace=True)
    return gdf

def fill_img_metadata_table() -> None:
    metadata_df = get_img_metadata_from_tif_files(cfg.DIR_PATH_IMG_DATA)
    metadata_df.to_postgis(
        con=engine,
        name=ImgMetadata.__tablename__,
        schema=ImgMetadata.__table_args__['schema'],
        if_exists='replace',
        index=False,
        chunksize=100)

def fill_img_window_clips_table() -> None:
    metadata_df = ImgMetadata.get_all()
    for img_metadata in metadata_df.iterrows():
        tif_ds_reader = get_img_tif_ds_reader_from_dir(cfg.DIR_PATH_IMG_DATA, img_metadata[1][
            get_model_column_for_mapped_name(ImgMetadata, 'file_path')])
        window_clips = set_img_window_clips_gdf(img_tif_ds=tif_ds_reader, img_name=img_metadata[1][
            get_model_column_for_mapped_name(ImgMetadata, 'img_name')])
        window_clips.to_postgis(
            con=engine,
            name=ImgWindowClips.__tablename__,
            schema=ImgWindowClips.__table_args__['schema'],
            if_exists='append',
            index=False,
            chunksize=100)

def main() -> None:
    fill_img_metadata_table()
    fill_img_window_clips_table()


if __name__ == "__main__":
    start_logging(__file__)
    main()
