# DB Connection
DB_CONN="postgresql+psycopg2://mastrdb:mastrdb@127.0.0.1:5500/mastrdb"

# Schema naming
SCHEMA_RAW_DATA = "public"
SCHEMA_MASTR = "mastr"
SCHEMA_BUILDINGS = "building"
SCHEMA_IMAGES = 'images'
SCHEMA_REFERENCE_AREA = "ref_area"
SCHEMA_MAPPING = 'mapping'

# Column naming
COL_GEOMETRY = "geom"
COL_GEOMETRY_AREA = f'{COL_GEOMETRY}_sqm'

# Geo Params
EPSG_TARGET = "4326"
EPSG_SOURCE = "25832"
FILE_ZIP_CODE_BORDERS = "ref_area/data/zip_code_ms.shp"

# Image Params
DIR_PATH_IMG_DATA = "images/data/input"
STRIDE = 112
IMSIZE_MODEL_IN = 224
DIR_PATH_MODELS = "images/data/models"
DIR_PATH_RESULTS = "images/data/results"
PRED_MASK_DEFAULT_INIT = -1
PRED_MASK_DEFAULT_DTYPE = 'int32'
DIR_NAME_RESULTS_PRED_MASK = 'mask'

# Detection Params
SQM_PER_PANEL_LOW = 1.6  # from Mayer et al.: p = 6 m2/kwp
SQM_PER_PANEL_HIGH = 1.7  # from energie-experten (2022)
CAP_PER_PANEL_LOW = 0.25  # in kWp
CAP_PER_PANEL_HIGH = 0.35  # in kWp
DETECTION_SQM_TH = SQM_PER_PANEL_HIGH  # average size of 350-400W module according to (Burkhardt, 2022)
