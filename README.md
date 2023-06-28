# Masterthesis: Validation and extension of data on solar plants in the Marktstammdatenregister using aerial images and building data

This repository contains a stripped down demo version of the code base for my Master Thesis (GPA: 1.0, DE Grading Scale) in the Mannheim Master in Data Science.
While my thesis conducted a case study on the city and district of Munich, this code base filters on data for the city area only.
Also, segmentation is performed for a single image only.
The compiled thesis report including results and visualizations for the entire area can be found under: `report/MastersThesis_VogtEsther.pdf`.

## Abstract

The goal of the German government to heavily increase the amount of solar capacity induces the challenge to efficiently
monitor an ever more decentralized energy system.

In this work, I present a methodology for automated validation and extension of the MaStR for building-mounted solar PV
systems.
It is based on extraction of information on systems from image and building data and generation of mappings to units in
the public registry.
It extends previous work by using freely accessible building data from OSM and comparing a variety of approaches for
creating correspondences to MaStR units.
The approach is evaluated on datasets covering the city and district of Munich.

My evaluation identifies erroneous entries for several fields:
For example, the capacity detected in images exceeds the registered capacity by 13\% which indicates an incorrect amount
of units registered as in operation.
Especially locational information is often inaccurate and not coherent:
For 16\% of large units no PV system could be detected at the reported place of installation.

My approach demonstrates the potential to fill these gaps by automatically generating more precise localizations of
systems and corresponding buildings.
It allows to complement the MaStR with building properties such as standardized roof shapes or building levels.

## Execution Instructions

Logging is included for all steps described thereafter. 
Log files can be found under `logs/<script-dir>/<script-name>.log`.

### Pre-Requisites

1. Make sure you have Docker installed locally.
2. Make sure the Docker Engine is running (i.e. Docker Desktop is started).

### Database Initialization and Startup

1. To initialize the DB by creating all relevant schemata and ORM models, run: `python db/main.py --drop_results=True`
   - If not yet existent, this script will create and run a PostGIS DB inside a Docker container. 
   - By default, `create_all` will not overwrite existing tables.
   - Consequently, pass the parameter `drop_results=True` to overwrite existing results.

**Note**: To test the connection to the DB in the CLI, connect to the DB with `psql postgres://mastrdb:mastrdb@127.0.0.1:5500/mastrdb`.
For example, to list all tables in the database, use the command `\dt`. 
To run a simple select query, just type the query in the psql cli, i.e. `mastrdb=# SELECT COUNT(*)  FROM public.solar_extended;`
For more details on psql, see [its official documentation](https://www.postgresql.org/docs/current/app-psql.html).

### Data Download and Extraction 

After manual download of relevant source data, all scripts mentioned thereafter can be sequentially executed by running the cli script `pipeline.bat`.
Note that the current version of the script assumes that the raw data is already available (files as well as tables in the PG DB).
Consequently, the respective parameters would have to be added to run a new extraction as specified by the argparse descriptions.

1. The original high-resolution image dataset used in my thesis is restricted by a NDA.
   Therefore, I used a sample image that was manually downloaded from the [OpenData](https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=dop40) platform of the Bavarian Agency for Digitisation, High-Speed Internet and Surveying.
   However, the images in this dataset have a lower resolution of 0.4m/px which worsens results as discussed in my thesis report. 
   To test other sample images, place them in the following directory: `images/data/input`.
2. To extract the **zip code reference data**, run: `python ref_area/main.py`.
   - This script reads and preprocesses the shapefile containing the raw zip code reference data (manually downloaded) and writes its contents to the `public` schema (table: `zip_borders_raw`).
   - In contrast, the zip code data for the given case study is written to the `ref_area` schema.
   - Originally, I manually download the zip code reference data as Shapefile from the [Esri Deutschland OpenData Platform](https://opendata-esri-de.opendata.arcgis.com/datasets/5b203df4357844c8a6715d7d411a8341_0/explore). 
   - At the time this thesis was finalized, the Esri file still contained information on the city and district which eliminated the need for an additional file to filter on relevant zip codes. 
   - Unfortunately, this information was removed in the most recent version on the OpenData Platform wherefore I included an extract shapefile of my zip code data considered in this case study (see: `ref_area/data/zip_code_ms.shp`).
3. To download and preprocess the raw **MaStR data for solar**, run: `python mastr/main.py`.
   - The raw data will be written to the `public` schema (relevant table: `solar_extended`).
   - The relevant MaStR data for solar installations with >30kWp in the reference area is written to the `mastr` schema.
4. To download and preprocess the raw **OSM building data for Bavaria**, run: `python building/main.py`.
   - The raw data will be written to the `public` schema (relevant table: `osm_building_raw`).
   - The relevant building data for the reference area is written to the `building` schema.
   - **Note: this step requires the image metadata to be already existing in the DB as well as the zip code reference data.**
   - The download of the raw OSM building data is performed by the package [pyrosm](https://pyrosm.readthedocs.io/en/latest/installation.html). 
   It downloads the OSM PBF files and has [geopandas](https://geopandas.org/en/stable/) as a dependency.
     - It is recommended to use conda instead of pip for pyrosm installation: `conda install -c conda-forge pyrosm`
     - In case you run into issues installing geopandas on Windows, I recommend [this tutorial](https://towardsdatascience.com/geopandas-installation-the-easy-way-for-windows-31a666b3610f).
       Although the named download page does not include a binary for geopandas, a simple `pip install geopandas` should do the trick after installing the dependencies mentioned in the article.

### Solar System Detection

The extraction of solar systems from the image data is performed in three steps:
1. To extract **image metadata** like geographic extend and crop the image to the required model input size, run `python images/preprocessing/main.py`.
2. To generate a **binary segmentation mask** for each image, run `python images/prediction/main.py`.
    - The output of this step will be a local TIFF file stored in the directory `images/data/results/mask/<stride>/<img_name>.tif`.
    - The scripts and models script and corresponding models are (partially) based on/copied from the fixMatchSeg-Muc repository of Yasmin Elsharnoby: https://github.com/yasminhossam/fixMatchSeg-Muc.
3. To extract the **boundary polygons** of all roof mounted systems detected per image, run `python images/postprocessing/main.py`.

### Mapping of MaStR Units to detected roof-mounted solar systems

To search for correspondences between solar MaStR units and solar systems detected in images, run `python mapping/main.py`.
Overall the search is performed in three steps:
1. First, solar MaStR units are mapped to buildings.
2. Secondly, solar systems detected in images are mapped to and grouped by buildings.
3. Finally, a mapping is created between the MaStR units and solar systems mapped to the same buildings. 
The following screenshot is an example visualization of a mapping between a MaStR unit (red diamond) and a detected system (polygon with blue filling):
![img.png](sample_mapping_result.png)

As mentioned above, check my final report (`report/MastersThesis_VogtEsther.pdf`) for a more detailed and extensive analysis of results for the Munich area.

## Further References
Extracts of my thesis report contributed to the following publication: 

Tepe, D., Kotthoff, F., Muschner, C., Vogt, E., & Hülk, L. (2023). Improving Data Reliability in Germany's Energy System: A Validation of Unit Locations of the Marktstammdatenregister. [arXiv preprint arXiv:2304.10581](https://arxiv.org/pdf/2304.10581.pdf).
