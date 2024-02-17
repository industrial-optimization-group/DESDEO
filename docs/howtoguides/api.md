# Running the API

!!! NOTE

    This guide assumes that you have already created a virtual environment for DESDEO and have activated it.

## Prerequisites

Install the API dependencies with the following command if you haven't already done so:

```bash
poetry install -E api
```

This will install the required dependencies for the API. The api itself is created with FastAPI and runs on Uvicorn. The API is located in the `desdeo/api` directory. The api needs a database to run, and the database connection is configured in the `desdeo/api/db.py` file. The default database connection is to a PostgreSQL database. To generate the database schema, run the following command:

```bash
python desdeo/api/db_init.py
```

Once the database schema has been generated, you can start the API with the following command:

```bash
uvicorn --app-dir=./desdeo/api/ app:app --reload
```
