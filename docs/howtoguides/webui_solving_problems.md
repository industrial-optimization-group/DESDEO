# Solving problems with the DESDEO web-GUI

!!! Warning

    The web-API and web-GUI are currently under heavy development, so bugs and issues
    are expected to arise with their use. Be warned!

This guide walks through the practical steps of getting the DESDEO web-GUI running
and using it to solve a multiobjective optimization problem, from setting up a
database to interacting with an optimization method in the browser.

!!! NOTE

    This guide assumes that you have already [installed DESDEO](./installing.md) with
    the web dependencies, as described in [Running the web-API and web-GUI](./api_and_gui.md).
    It does not repeat the installation steps in detail.

## Overview

Solving a problem with the web-GUI generally involves these steps:

1. Set up a database containing at least one problem (and a user to own it).
2. Start the web-API and web-GUI.
3. Log in.
4. Make sure the problem you want to solve is available. If it isn't yet, add it
   either through the UI (for simple, purely algebraic problems) or by writing a
   custom database initialization script (for anything that needs a simulator,
   surrogate, custom UI description, or a scenario model).
5. Select the problem and an interactive method, and start solving.

## 1. Set up the database

The web-API needs a database to store users and problems. The simplest way to
create one is to run the default initialization script:

```bash
cd desdeo/api
python db_init.py
```

This creates the database schema and populates it with a test analyst user and a
handful of test problems (`dtlz2`, `simple_knapsack`, `river_pollution_problem`).
See [`desdeo/api/db_init.py`](https://github.com/industrial-optimization-group/DESDEO/blob/master/desdeo/api/db_init.py)
for the exact details, such as the test user's credentials (by default `analyst` /
`analyst`, configurable in `desdeo/api/config.toml`).

!!! Warning "Run it from inside `desdeo/api/`"

    By default the database is a SQLite file at the relative path `./test.db`
    (see `db_database` in `desdeo/api/config.toml`), resolved against the current
    working directory of whichever process opens it. `just fullstack` (i.e.,
    `run_fullstack.py`, used [below](#2-run-the-web-api-and-web-gui)) starts the
    backend with its working directory set to `desdeo/api/`, so it looks for
    `desdeo/api/test.db`. If you run the init script from the repository root
    instead, it will create a `test.db` there, and the backend started by
    `just fullstack`/`run_fullstack.py` won't find it. Either run the init script
    from inside `desdeo/api/` (as shown above), or, if you already ran it from the
    repository root, just move the resulting `test.db` into `desdeo/api/`.

!!! Note

    Running an init script against an existing database drops and recreates all
    tables, so any problems or results you have created through the UI will be lost.
    Only do this when you actually want a fresh database.

### Adding your own problems ahead of time with a custom init script

If you already know which problems you want available, and especially if a
problem needs more than what a plain [`Problem`][desdeo.problem.schema.Problem]
object provides, it is often easier to add it to the database directly with your
own initialization script, instead of adding it later through the UI (see
[below](#4-make-sure-your-problem-is-in-the-database)).

[`desdeo/api/db_init_summer_cabin.py`](https://github.com/industrial-optimization-group/DESDEO/blob/master/desdeo/api/db_init_summer_cabin.py)
is a good example to copy and adapt. It does everything `db_init.py` does, and
additionally:

- builds a problem programmatically (`summer_cabin_battery_robust_ev_problem()`),
  modifies it (e.g., demoting some objectives to extra functions), and stores it
  with `ProblemDB.from_problem(...)`;
- attaches a `SolutionDescriptionMetaData` to a problem, which the UI uses to
  render a nicer, human-readable description of a solution than just a list of
  objective values;
- attaches a `ScenarioModelDB` to a base problem, which lets the Cumulus method
  build a combined scenario problem with uncertainty measures automatically.

None of this extra metadata can currently be uploaded through the "Create custom
problem" screen in the UI (see below) — it has to be inserted into the database
this way.

To use a custom script instead of the default one, just run it the same way, from
inside `desdeo/api/`, e.g.:

```bash
cd desdeo/api
python db_init_summer_cabin.py
```

## 2. Run the web-API and web-GUI

The easiest way to start both the web-API and the web-GUI at once is the `just`
recipe (see [Running the web-API and web-GUI](./api_and_gui.md) for the manual,
step-by-step alternative and for setting up the required environment variables the
first time):

```bash
just fullstack
```

`just fullstack` simply runs `python run_fullstack.py` from the repository root, so
if `just` isn't available on your machine (e.g., it doesn't support shell recipes),
you can run that directly instead:

```bash
python run_fullstack.py
```

This starts the web-API (FastAPI/Uvicorn) and the web-GUI (SvelteKit dev server),
and should open the web-GUI in a new browser tab. If it doesn't open automatically,
the web-GUI is normally served at `http://localhost:5173`.

## 3. Log in

On the login page, sign in with a user that exists in your database. If you used
the default `db_init.py` (or a script based on it, like the summer cabin one), the
test analyst user's credentials are defined in `desdeo/api/config.toml` under
`[server-debug]` — by default `analyst` / `analyst`.

After logging in, you land on the **Dashboard**, which has shortcuts to the main
parts of the UI: browsing problems, browsing methods, creating a custom problem,
and a few example workflows.

## 4. Make sure your problem is in the database

If the problem you want to solve is already in the database (because it was
included in the init script you ran), you can skip ahead to
[solving the problem](#5-select-a-problem-and-solve-it).

If it isn't there yet, you have two options:

### Option A: Add it through the UI (algebraic problems only)

This works well for problems that are purely algebraic, i.e., they don't rely on a
simulator or a surrogate model, and don't need any of the extra metadata mentioned
above.

1. From the dashboard, click **Create Problem** (or navigate to `/problems/define`).
2. Switch to the **Upload JSON** tab.
3. Choose a JSON file containing a serialized DESDEO `Problem`.
4. Click **Submit JSON** — not **Populate form from JSON**. "Populate form from
   JSON" only fills in the form fields on the **Define via Form** tab so you can
   inspect or tweak them by hand; it does not create the problem. "Submit JSON"
   uploads the file directly and creates the problem in the database.

You can produce a suitable JSON file from any `Problem` object with
[`save_to_json`][desdeo.problem.schema.Problem.save_to_json]. For example, to
export the summer cabin example problem used in the
[scenario documentation](../explanation/scenarios.md):

```python
from desdeo.problem.testproblems.summer_cabin_electricity import summer_cabin_battery_robust_ev_problem
from pathlib import Path

p = Path("test_problem.json")
problem = summer_cabin_battery_robust_ev_problem()
problem.save_to_json(p)
```

Then upload the resulting `test_problem.json` on the upload screen as described
above.

!!! Note "Limitations of the JSON upload"

    Uploading a JSON file only creates the `Problem` itself. It cannot attach a
    custom `SolutionDescriptionMetaData` (for a nicer solution description in the
    UI) or a `ScenarioModelDB` (for automatically building a combined scenario
    problem in Cumulus). If you need either of those, use
    [a custom init script](#adding-your-own-problems-ahead-of-time-with-a-custom-init-script)
    instead, as done in `db_init_summer_cabin.py`.

### Option B: Write a custom init script

If your problem needs a simulator, surrogate, custom solution description, or a
scenario model, add it to the database the way
[`desdeo/api/db_init_summer_cabin.py`](https://github.com/industrial-optimization-group/DESDEO/blob/master/desdeo/api/db_init_summer_cabin.py)
does, then run your script as described in [step 1](#adding-your-own-problems-ahead-of-time-with-a-custom-init-script)
before starting the web-API.

## 5. Select a problem and solve it

1. From the dashboard, click **Explore Problems** (or navigate to `/problems`).
   This lists every problem available to your user, with tabs showing its
   objectives, variables, constraints, and extra functions.
2. Pick the problem you want to work on and click **Solve** to select it.
3. Go to **Optimization Methods** (from the dashboard, or `/methods/initialize`).
   This lists the interactive methods available in DESDEO (e.g., NIMBUS, NAUTILUS
   Navigator, NAUTILI, Cumulus, ...), filtered by what kind of preference
   information they use. Some methods may be disabled if they aren't compatible
   with the selected problem.
4. Choose a method to start an interactive solution process for your selected
   problem.

From here on, how you interact with the method depends on the method itself.
See the method-specific how-to guides for details, for example
[NAUTILUS Navigator](./nautilus_navigator.md) or [NAUTILI](./nautili.md), and
[Implementing method interfaces](./implementing_method_interfaces.md) if you are
looking to add a UI for a new method.
