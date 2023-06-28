# Masterthesis: Validation and extension of data on solar plants in the Marktstammdatenregister using aerial images and building data

This repository contains the code base for the Master Thesis of Esther Vogt in the Mannheim Master in Data Science.
The compiled thesis report can be found under: `report/20230323_MastersThesis_VogtEsther.pdf`

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

### Pre-Requisites

1. Make sure you have Docker installed locally.

### Database Initialization

1. Make sure the Docker Engine is running (i.e. Docker Desktop is started).
2. Run `db/setup.py` to create a PostGIS DB inside a Docker container.

**Note**: To test the connection to the DB in the CLI, connect to the DB with `psql postgres://mastrdb:mastrdb@127.0.0.1:5500/mastrdb`.
For example, to list all tables in the database, use the command `\dt`. 
For more details on psql, see [its official documentation](https://www.postgresql.org/docs/current/app-psql.html).


