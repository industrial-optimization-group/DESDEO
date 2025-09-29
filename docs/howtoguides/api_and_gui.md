# Using the web-API and web-GUI

!!! Warning

    The web-API and web-GUI are currently under heavy development, so bugs and issues are
    expected to arise with their use. Be warned!

!!! NOTE

    This guide assumes that you have already [installed DESDEO](./installing.md),
    and that you have created and activated a virtual environment.

DESDEO's web-API is developed in Python and requires some extra dependencies, compared
to the core-logic, to be installed. However, the web interface for DESDEO, the web-GUI,
is developed in TypeScript, and requires its own packages and package manager for the
dependencies to be installed. Below, instructions for setting up and running both
the web-API and web-GUI are provided.

## Web-API
### Web-API prerequisites
Install the `web` dependencies with the following command if you have not already done so:

=== "Poetry"

    ```bash
    poetry install
    ```

=== "uv"

    ```bash
    uv sync
    ```

This will install the required dependencies for the web-API. The web-API itself is
created with FastAPI and runs on Uvicorn. The source
files for the web-API are located in the `desdeo/api`
directory.

### Setting up the database
The api needs a database to run, and the database connection is
configured in the `desdeo/api/db.py` file. The default database connection is to
a SQLite database (but can be changed to a more robust solution for
production purposes, e.g., PostgreSQL). To generate the database schema, run the following
command:

```bash
python desdeo/api/db_init.py
```

Once the database schema has been generated, you can start the web-API with the
following command:

```bash
uvicorn --app-dir=./desdeo/api/ app:app --reload
```

## Web-GUI
### Web-GUI prerequisites

The source files for the web-GUI are located in the `webui` folder at the __root-level__
of the project. Unlike the core-logic and the web-API, the web-GUI is developed in
TypeScript. It is assumed that the node package manager `npm` ([link](https://www.npmjs.com/))
is available on the system. Use `npm` to install the web-GUI's dependencies

```bash
cd webui
npm install
```

!!! Note

    If errors arise related to an old or unsupported node version, the node version
    manager `nvm` ([link](https://github.com/nvm-sh/nvm)) can be used to select an appropriate version.

### Setting up the web-GUI

There are some environmental variables that need to be defined before the web-GUI can be used in combination
with the web-API and its database. Please refer to the [README](https://github.com/industrial-optimization-group/DESDEO/blob/master/webui/README.md) of
the web-GUI for additional details.

### Running the web-GUI

Assuming the web-API is setup and running correctly, the web-GUI should now be functional and
can be hosted locally with the command

```bash
npm run dev -- --open
```

## Script to automatically setting up and running the web-API and web-GUI

At the root-level of the project, there is a script defined in the file
`run_fullstack.sh`, which can be executed to easily setup and run both the web-API
and web-GUI. However, the script does not install dependencies or set environmental
variables, which must first still be configured manually as described above.

After a successful setup, the web-API and web-GUI can be readily executed with
one command:

```bash
./run_fullstack.sh
```

There is also an equivalent make-rule:

```bash
make fullstack
```

If everything works as expected, we should now see debug output in our terminal
for both the web-API and web-GUI, and the web-GUI should open in a new tab in your
default browser.