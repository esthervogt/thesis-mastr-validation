import rasterio
from rasterio.windows import Window
import numpy as np
from pathlib import Path
import config as cfg
import os

MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

def get_window_from_dict(window_dict: dict) -> Window:
    return rasterio.windows.Window(col_off=window_dict['col_off'],
                                   row_off=window_dict['row_off'],
                                   width=window_dict['width'],
                                   height=window_dict['height'])

def get_img_tif_ds_reader_from_dir(dir_path: str, file_path: str) -> rasterio.DatasetReader:
    return rasterio.open(
        Path(dir_path)
        / (f'{file_path}.tif' if '.tif' not in file_path else file_path)
    )

def get_img(img_tif_ds: rasterio.DatasetReader) -> np.ndarray:
    return img_tif_ds.read()

def prediction_exists(img_name: str) -> bool:
    target_path = Path(cfg.DIR_PATH_RESULTS) / 'mask' / str(cfg.STRIDE) / f'{img_name}.tif'
    return target_path.exists()

def get_results_file_path(sub_dir_name: str, file_name: str=None) -> [Path|str]:
    dir_path_root = Path(cfg.DIR_PATH_RESULTS) / sub_dir_name
    dir_path_root.mkdir(exist_ok=True)

    dir_path = dir_path_root / str(cfg.STRIDE)
    dir_path.mkdir(exist_ok=True)

    return dir_path if file_name is None else os.fspath(dir_path / file_name)

def normalize(image: np.ndarray) -> np.ndarray:
    """Normalized an image (or a set of images), as per
    https://pytorch.org/docs/1.0.0/torchvision/models.html

    Specifically, images are normalized to range [0, 1], and
    then normalized according to ImageNet stats.
    """
    image = image / 255

    # determine if we are dealing with a single image, or a
    # stack of images. If a stack, expected in (batch, channels, height, width)
    source, dest = 0 if len(image.shape) == 3 else 1, -1

    # moveaxis for array broadcasting, and then back so its how pytorch expects it
    return np.moveaxis((np.moveaxis(image, source, dest) - MEAN) / STD, dest, source)
