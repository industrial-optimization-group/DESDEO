# DESDEO REST API

The DESDEO REST API is a FastAPI application that provides a RESTful interface to the DESDEO framework. The API is designed to be used by the DESDEO WebUI, but it can also be used by other applications. The best way to get the API
docs is to use the Swagger/Redoc UI provided by the API. You can access the Swagger UI at `http://localhost:8000/docs` and the Redoc UI at `http://localhost:8000/redoc` after starting the API. This assumes that the API is running on your local machine and the default port is used.

## The Main Application
::: desdeo.api.app
    optioms:
        heading_level: 3

## Database initializer
::: desdeo.api.db_init
    options:
        heading_level: 3

## Main Database method
::: desdeo.api.db
    options:
        heading_level: 3

## Database Models
::: desdeo.api.db_models
    options:
        heading_level: 3

## Miscellaneous dataclasses used in the database
::: desdeo.api.schema
    options:
        heading_level: 3

## Routes provided by the API
### NAUTILUS Navigator
::: desdeo.api.routers.NAUTILUS_navigator
    options:
        heading_level: 4