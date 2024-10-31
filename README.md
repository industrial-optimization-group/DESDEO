# DESDEO: the open source software framework for interactive multiobjective optimization

[![Documentation Status](https://img.shields.io/readthedocs/desdeo.svg?version=desdeo2&label=Documentation)](https://desdeo.readthedocs.io/en/desdeo2) ![Tests](https://img.shields.io/github/actions/workflow/status/industrial-optimization-group/DESDEO/unit_tests.yaml?branch=desdeo2&label=Tests)

[![Discord server](https://dcbadge.vercel.app/api/server/TgSnUmzv5M)](https://discord.gg/TgSnUmzv5M)

__Everything in this repository is currently subject to change. Stay tuned for updates.__

## Introduction

DESDEO is an open source framework for interactive multiobjective optimization
methods. The framework contains implementations of both scalarization- and
population-based methods interactive methods. There are currently no other
software frameworks that focus solely on the the implementation of
interactive multiobjective optimization methods.

The mission of DESDEO is to increase awareness of the benefits of interactive
multiobjective optimization methods, make interactive methods openly available,
and to function as _the_ central hub for implementations of various interactive
methods. Apart from existing methods, DESDEO offers various tools to facilitate
the development of new methods and their application as well.

DESDEO is an open source project and everybody is welcome to contribute!

## Key features

DESDEO offers various features that can facilitate the application and
development of new interactive multiobjective optimization methods. Some
of the key features include, but are not limited to,

-   A powerful, pydantic-based, schema for modeling multiobjective optimization problem of various kinds. Including, analytically defined problems, data-based problems, surrogate-based problems (WIP), and simulation-based problems (WIP). Both continuous and (mixed-)integer problems are supported as well.
-   Support to interface to many popular and powerful optimization software for solving multiobjective optimization problems. Including Gurobi, various solvers
from the COIN-OR project, and nevergrad, for instance. 
-   A wide assortment of modular software components for implementing existing
and new interactive multiobjective optimization methods. For example, many scalarization functions and evolutionary operators for multiobjective optimization are available.
-   A web application programming interface (API), which allows utilizing the
interactive multiobjective optimization methods found in DESDEO in virtually any application. The web API also implements a database, and user authentication and session management, allowing DESDEO to be used in building modern web applications as well.
-   An extensive documentation suitable for both newcomers to DESDEO and interactive multiobjective optimization in general, and seasoned veterans.

## Installation instructions

### Pre-requisites

DESDEO is currently being developed and supported on __Python versions 3.12 and
newer__. Otherwise, DESDEO is mostly a Python-based framework, depending mostly
on other Python packages. However, it does offer interfaces to many powerful
existing optimizers. It is recommended to have at least some of these installed
and available on the system DESDEO is utilized on to help ensure timely and
accurate optimization results.

Some optimizers to consider are:

-   Optimizers from the COIN-OR project, such as Bonmin and Couenne
-   Gurobi

For running the web API, the following external dependencies should be installed
and made available to DESDEO:

-   Postgres (https://www.postgresql.org/download/) to run the API.

Since this version of DESDEO is not currently available in any public
repositories (such as PyPI) as a Python package, it is highly recommended
to utilize a Python package management tool to install DESDEO. For this,

-   [Poetry](https://python-poetry.org/docs/#installation) is recommended.

### Installation

This version of DESDEO is currently under heavy development and thus is not
available in any Python package repositories. DESDEO will be available
on PyPI once it reaches a stable version.

We will assume for the reamainder of these instruction that the
[Poetry](https://python-poetry.org/docs/#installation) is available
on the system DESDEO is being installed on.

To intall DESDEO:

-   Clone this repository
    ```bash
    git clone https://github.com/industrial-optimization-group/DESDEO.git
    ```
-   Create a virtual environment for DESDEO
    ```bash
    python -m venv .venv
    ``` 
    or with Poetry
    ```bash
    poetry shell
    ```
-   Activate the virtual environment
    ```bash
    source .venv/bin/activate
    ```
    or with poetry
    ```bash
    poetry shell
    ```
-   Install DESDEO
    ```bash
    poetry install -E standard  # for relatively modern CPUs
    ```
    or
    ```bash
    poetry install -E legacy  # for older or certain Apple CPUs, slower
    ```
-   For installing web API dependencies as well, run
    ```bash
    # replace 'standard' with 'legacy' if needed
    poetry install -E "standard api"  

DESDEO should now be installed and available on your local machine inside the activated virtual environmnet.

### Running the web API

Make sure the dependencies of the web API have been installed first. See the previous section.

To run the DESDEO web API, run the following commands,

```bash
# assuming the present working directory is the root of the project
cd desdeo/api/
uvicorn app:app --reload
```

Follow the console output to see on address and port the web API is running.

## Documentation

Care has been taken to make sure DESDEO is well docmumented, making
it accessible to both newcomes and seasoned users.

[The documentation of DESDEO is available online.](https://desdeo.readthedocs.io/en/desdeo2/)

## Contributing

As DESDEO is an open source project, anybody is welcome to contribute.
An extensive tutorial to get started contributing to DESDEO
[is available in the documentation](https://desdeo.readthedocs.io/en/desdeo2/tutorials/contributing/).
Be sure to check it out!

For additional support for contributing to DESDEO,
be sure to check out the DESDEO channels
in the MCDM Community's Discord server. You may join the server
[through this invite](https://discord.gg/TgSnUmzv5M).

## License

DESDEO is licensed under the MIT license. For more information,
check the `LICENSE` file.

## Citing DESDEO

To cite DESDEO, please include the following reference:

[Misitano, G., Saini, B. S., Afsar, B., Shavazipour, B., & Miettinen, K. (2021). DESDEO: The modular and open source framework for interactive multiobjective optimization. IEEE Access, 9, 148277-148295.](https://doi.org/10.1109/ACCESS.2021.3123825)

```
@article{misitano2021desdeo,
  title={DESDEO: The modular and open source framework for interactive multiobjective optimization},
  author={Misitano, Giovanni and Saini, Bhupinder Singh and Afsar, Bekir and Shavazipour, Babooshka and Miettinen, Kaisa},
  journal={IEEE Access},
  volume={9},
  pages={148277--148295},
  year={2021},
  publisher={IEEE}
}
```



