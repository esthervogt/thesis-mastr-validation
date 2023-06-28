from typing import Union

import rasterio
from rasterio._err import CPLE_AppDefinedError
from rasterio.windows import Window
from rasterio import DatasetReader
from db import get_model_column_for_mapped_name
from logs.utils import start_logging
from images.models import ImgWindowClips, ImgMetadata
from images.data.models import Segmenter, Classifier
import torch
from pathlib import Path
import config as cfg
from alive_progress import alive_bar
from images.utils import (
    get_window_from_dict, normalize, get_img_tif_ds_reader_from_dir, get_img, prediction_exists, get_results_file_path)
import numpy as np
import os

DEVICE = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

def load_fully_supervised_model() -> dict:
    """
    Load the saved classifier and segmentation model and set to inference mode
    """
    model_dict = {}
    for m in ['classifier', 'segmenter']:
        model = eval(f'{m.capitalize()}()')
        model.load_state_dict(torch.load(f=Path(cfg.DIR_PATH_MODELS) / f'{m}.model', map_location=DEVICE))
        model.eval()
        model.to(DEVICE)
        model_dict[m] = model
    return model_dict

def clip_img_to_window(img: np.ndarray, window: Window) -> np.ndarray:
    img_clip = img[:, window.row_off:(window.row_off + window.height), window.col_off:(window.col_off + window.width)]
    return fill_img_clip_boundary(img_clip)

def fill_img_clip_boundary(img_clip: np.ndarray) -> np.ndarray:
    """
    This function handles windows at the image boundaries which might not be full-sized
    """
    if (img_clip.shape[1] < cfg.IMSIZE_MODEL_IN) or (img_clip.shape[2] < cfg.IMSIZE_MODEL_IN):
        img_clip_filled = np.zeros((3, cfg.IMSIZE_MODEL_IN, cfg.IMSIZE_MODEL_IN))
        img_clip_filled[:, :img_clip.shape[1], :img_clip.shape[2]] = img_clip
        return img_clip_filled
    return img_clip

def run_prediction_for_clip(img: np.ndarray, window: Window, model: dict) -> dict:
    img_tensor = get_tensor_from_np_img(clip_img_to_window(img=img, window=window))
    window_pred_class = run_classification_for_clip(model=model['classifier'], input=img_tensor)
    window_pred_mask = None
    if window_pred_class > 0.5:
        window_pred_mask = run_segmentation_for_clip(model=model['segmenter'], input=img_tensor)
    return {'pred_class': window_pred_class, 'pred_mask': window_pred_mask}

def run_classification_for_clip(model: Classifier, input: torch.Tensor) -> float:
    with torch.no_grad():
        pred_class = model(input).squeeze(1).cpu().numpy()[0]
    return pred_class

def run_segmentation_for_clip(model: Segmenter, input: torch.Tensor) -> np.ndarray:
    with torch.no_grad():
        pred_mask = model(input).squeeze(1).cpu().numpy()[0, :, :]
    pred_mask = np.where(pred_mask <= 0.5, 0, 1).astype(np.uint8)
    return pred_mask

def get_tensor_from_np_img(img: np.ndarray) -> torch.Tensor:
    """
    Apply transformation (here: normalization) and convert np image to pytorch tensor.
    Apply unsqueeze operation to provide batch dimension.
    """
    img_transformed = normalize(image=img)
    return torch.as_tensor(img_transformed.copy(), device=DEVICE).float().unsqueeze(0)

def init_total_pred(img_tif_ds: DatasetReader) -> dict:
    """
    Create a single-band template storing all predictions per mask. Initialize to the default specified in the config
    (PRED_MASK_DEFAULT_INIT) to allow visualizing which parts of the source image have been processed (i.e. in case
    prediction fails for a part of the image).
    """
    pred_mask = np.full((img_tif_ds.shape[0], img_tif_ds.shape[1]), cfg.PRED_MASK_DEFAULT_INIT)
    ds_dtype = img_tif_ds.dtypes[0] if len(set(img_tif_ds.dtypes)) == 1 else cfg.PRED_MASK_DEFAULT_DTYPE
    if ds_dtype == 'float32':
        pred_mask = pred_mask.astype('float32')
    return {'pred_class': [], 'pred_mask': pred_mask}

def update_total_pred(total_pred: dict, window_pred: dict, window: Window, img_tif_ds: DatasetReader) -> dict:
    total_pred['pred_class'] = update_total_pred_class(total_pred['pred_class'], window_pred['pred_class'])
    total_pred['pred_mask'] = update_total_pred_mask(total_pred['pred_mask'], window_pred['pred_mask'], window, img_tif_ds)
    return total_pred

def update_total_pred_class(pred_class, window_pred_class) -> list:
    pred_class.append(window_pred_class)
    return pred_class

def update_total_pred_mask(pred_mask: np.ndarray, window_pred: np.ndarray, window: Window, img_tif_ds: DatasetReader) -> np.ndarray:
    """
    Write the prediction to the corresponding window in the source image prediction mask. This compares the values
    from previous predictions and the current window and takes the element-wise maximum to prevent previous
    predictions from getting overwritten.
    If the clip is from the bottom or right boundary, it won't have the full size and thus the window size needs to
    be handled accordingly.
    """
    if window_pred is not None:
        window_height = min(img_tif_ds.shape[0] - window.row_off, cfg.IMSIZE_MODEL_IN)
        window_width = min(img_tif_ds.shape[1] - window.col_off, cfg.IMSIZE_MODEL_IN)
        row_min, col_min = window.row_off, window.col_off
        row_max, col_max = window.row_off + window_height, window.col_off + window_width
        pred_mask[row_min:row_max, col_min:col_max] = np.maximum(pred_mask[row_min:row_max, col_min:col_max],
                                                                 window_pred[:window_height, :window_width])
    return pred_mask

def write_pred_to_dir(total_pred:dict, img_name: str, img_tif_ds: DatasetReader) -> None:
    Path(cfg.DIR_PATH_RESULTS).mkdir(exist_ok=True)
    persist_to_np(total_pred['pred_class'], img_name)
    persist_to_tiff(total_pred['pred_mask'], img_name, img_tif_ds)

def persist_to_np(pred_obj: Union[np.ndarray, list], img_name:str) -> None:
    file_path = get_results_file_path(cfg.DIR_NAME_RESULTS_PRED_MASK if type(pred_obj) == np.ndarray else 'class', img_name)
    np.save(file_path, pred_obj, allow_pickle=True)

def persist_to_tiff(pred_mask: np.ndarray, img_name:str, img_tif_ds: DatasetReader) -> None:
    file_path = get_results_file_path(cfg.DIR_NAME_RESULTS_PRED_MASK, f"{img_name}.tif")
    try:
        with rasterio.open(file_path, 'w', **get_tif_ds_profile(img_tif_ds, pred_mask.dtype)) as dst:
            dst.write(np.array([pred_mask]))
    except CPLE_AppDefinedError:
        os.remove(file_path)
        persist_to_tiff(pred_mask, img_name, img_tif_ds)

def get_tif_ds_profile(img_tif_ds: DatasetReader, dtype: str) -> property:
    profile = img_tif_ds.profile
    profile.update({'dtype': eval(f'rasterio.{dtype}'), 'count': 1, 'compress': 'lzw'})
    return profile

def run_prediction_for_image(img_name: str, model: dict):
    if prediction_exists(img_name=img_name):
        return
    tif_ds_reader = get_img_tif_ds_reader_from_dir(cfg.DIR_PATH_IMG_DATA, img_name)
    img = get_img(tif_ds_reader)
    total_pred = init_total_pred(tif_ds_reader)
    window_clips = ImgWindowClips.get_single_img_clips(img_name)

    if len(window_clips) > 0:
        with alive_bar(len(window_clips), force_tty=True, bar='classic') as bar:
            for window_dict in window_clips.to_dict('records'):
                window = get_window_from_dict(window_dict)
                window_pred = run_prediction_for_clip(img, window, model)
                total_pred = update_total_pred(total_pred, window_pred, window, tif_ds_reader)
                bar()

        write_pred_to_dir(total_pred, img_name, tif_ds_reader)

def main() -> None:
    for img_metadata in ImgMetadata.get_all().iterrows():
        run_prediction_for_image(
            img_name=img_metadata[1][get_model_column_for_mapped_name(ImgMetadata, 'img_name')],
            model=load_fully_supervised_model())

if __name__ == "__main__":
    start_logging(__file__)
    main()
