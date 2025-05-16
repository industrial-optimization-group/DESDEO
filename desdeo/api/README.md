# DESDEO web API
Experimental. The instructions below assume that the current working directory
is `desdeo/api` and that the DESDEO framework has been installed successfully
with the extra dependencies in the `api` group.

## API configuration

The API configuration is handled by the settings found in `config.toml`. This
file should be used for reading existing configuration parameters and adding
new ones. Except for deployment (TODO).

## Initializing the database

To initialize the database, run the script `db_init.py` with the following command:

```shell
python db_init.py
```

This will create an initial databse, which allows testing for, e.g., testing
the databse. However, the tests themselves (see below), do not depend on this
database, and handle the database for running the tests on their own.

Importantly, this will create an analyst user, which can be used to test out
the end-points using the FastAPI generated documentation (see below). The
default name of the analyst user will be 'analyst' with the password 'analyst'.

This is mainly for testing purposes, which will create and manage a local
dblite-databse.

## Running the API

To run the API, invoke `uvicorn` as followsi:

```shell
uvicorn --app-dir=./ app:app --reload
```
See the outputs of the command to figure out where the API is running. This is
likely something along the lines `http:127.0.0.1:8000`, but may vary.

## Exploring the API

Once the API is running, its endpoints can be interactively explored by accessing
`<api_url>/docs`. For example, `http:127.0.0:8000/docs`. The `analyst` user created by
invoking `init_db.py` can be used to authorize and access the protected endpoints.

## Running (unit) tests

Pytest can be used to run tests relate to the API with the following command:

```shell
pytest
```
Again, it is assumed for the current working directory to be `desdeo/api`.
Otherwise a lot of tests will be executed.

## How the API works

The API consists of two important concepts: __models__ and __routers__. At the
core of the API, is a database.

Models utilize SQLite to define databse models. In other words, it describes
stuff we want to store in the databse. These models are very similar to
pydantic models, and are almost interchangeable. One major difference is that
the models are relational. This means that models often relate to each other.
E.g., an `ArchiveEntryDB` is the child of the model `User`.

Routers define HTTP endpoints to access and database and the models within.
These endpoints often modify the contents of the database, e.g., by solving a
problem with an interactive method, and then saving the solutions back to the
database. Endpoints often make use of code found in the core-logic (the
algorithms containing part of DESDEO), and are, in fact, a way to utilize this
code through the web (which is the whole point of this API!).
