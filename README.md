![Latest release](https://img.shields.io/github/v/release/industrial-optimization-group/DESDEO?label=Latest%20release)
[![PyPI version](https://img.shields.io/pypi/v/desdeo?label=PyPI)](https://pypi.org/project/desdeo/)
[![Documentation Status](https://img.shields.io/readthedocs/desdeo.svg?version=desdeo2&label=Documentation)](https://desdeo.readthedocs.io/en/latest/)
![Core-logic / Web-API Tests](https://img.shields.io/github/actions/workflow/status/industrial-optimization-group/DESDEO/unit_tests.yaml?branch=master&label=Core-logic%20and%20Web-API%20Tests)
![Web-UI Tests](https://img.shields.io/github/actions/workflow/status/industrial-optimization-group/DESDEO/webui_tests.yaml?branch=master&label=WebUI%20Tests)
[![codecov](https://codecov.io/gh/industrial-optimization-group/DESDEO/branch/master/graph/badge.svg)](https://codecov.io/gh/industrial-optimization-group/DESDEO)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20748206.svg)](https://doi.org/10.5281/zenodo.20748206)
[![Discord](https://img.shields.io/discord/1382614276409266206?style=flat&label=Join%20our%20Discord&labelColor=%237289da)](https://discord.gg/uGCEgQTJyY)


# DESDEO: the open-source software framework for interactive multiobjective optimization
## Introduction

DESDEO is an open-source framework for interactive multiobjective optimization
methods. The framework contains implementations of both scalarization- and
population-based interactive methods. There are currently no other open-source
software frameworks that focus solely on the implementation of interactive
multiobjective optimization methods.

The mission of DESDEO is to increase awareness of the benefits of interactive
multiobjective optimization methods, make interactive methods openly available,
and to function as _the_ central hub for implementations of various interactive
methods. Apart from existing methods, DESDEO offers various tools to facilitate
the development of new methods and their application as well.  Another important
goal of DESDEO is to answer the needs of decision makers and practitioners when
it comes to modeling and solving real-life multiobjective optimization problems.

In the bigger picture, DESDEO will be composed of three major components:

1. The __core-logic__, which contains the algorithmic implementation of
interactive methods, various tools related to multiobjective optimization, and
means to model a variety of multiobjective optimization problems. The core-logic
can be considered stable enough for use in research and applications.
2. The __web-API__ (WIP), which implements a web-based application programming
interface (API) to allow the use of the various functionalities found in
DESDEO's core-logic through a web connection. The web-API implements also a
database, which is a vital component for managing and enabling
decision-support using the framework. __The
web-API is currently under heavy development, and is subject to changes.__
3. The __web-GUI__ (WIP), which implements a web-based interface for utilizing
the interactive methods and tools for modeling and solving multiobjective
optimization problems.

> __The web-GUI relies heavily on the web-API, and is also being actively developed currently, and therefore subject to sudden changes.__

For developing and experimenting with interactive multiobjective optimization
methods on a "grass root" level, the __core-logic__ provides the necessary
tools.  For deploying interactive methods, the __web-API__ and the __web-GUI__
play a central role.

> Users interested in using or developing the web-API and/or web-GUI are highly encouraged to express such intentions on our [Discord server](https://discord.gg/uGCEgQTJyY)!.

DESDEO is an open-source project and everybody is welcome to contribute!

## Core-logic: key features

DESDEO's core-logic offers various features that can facilitate the application and
development of new interactive multiobjective optimization methods. Some
of the key features include, but are not limited to,

-   A powerful, pydantic-based, schema for modeling multiobjective optimization
problem of various kinds. Including, analytically defined problems, data-based
problems, surrogate-based problems, and simulation-based problems.
Both continuous and (mixed-)integer problems are supported as well.
-   Support to interface to many popular and powerful optimization software for
solving multiobjective optimization problems. Including Gurobi, various solvers
from the COIN-OR project, and nevergrad, for instance.
-   A wide assortment of modular software components for implementing existing
and new interactive multiobjective optimization methods. For example, many
scalarization functions and evolutionary operators for multiobjective
optimization are available.
-   An extensive documentation suitable for both newcomers to DESDEO and
interactive multiobjective optimization in general, and seasoned veterans.

For a complete overview of the interactive methods, algorithms, and tools
currently implemented, see [Implemented methods and
features](https://desdeo.readthedocs.io/en/latest/home/features/).

## Web-API: key features

DESDEO's web-API is currently under active development. Once it stabilized, its
key features will be listed here. In the meantime, the interested user can
follow (and contribute!) the development progress of the web-API in [this
issue](https://github.com/industrial-optimization-group/DESDEO/issues/245).

## Web-GUI: key features

DESDEO's web-GUI is currently under active development. Once it stabilized, its
key features will be listed here. In the meantime, the interested user can
follow (and contribute!) the development progress of the web-API in [this
issue](https://github.com/industrial-optimization-group/DESDEO/issues/251).

## Installation instructions (core-logic)

DESDEO is available on PyPI to be installed via pip:

```bash
pip install desdeo
```

However, some of DESDEO's features rely on 3rd party optimizers, which should be available on your system.
To read more on these, and on instructions on how to install the latest version of DESDEO directly from Github,
[check out the documentation](https://desdeo.readthedocs.io/en/latest/howtoguides/installing/).

## Documentation

Care has been taken to make sure DESDEO is well documented, making it accessible
to both newcomers and seasoned users alike.  [The documentation of DESDEO is
available online.](https://desdeo.readthedocs.io/en/latest/)

### Documentation for LLMs

An [`llms.txt`](https://desdeo.readthedocs.io/en/latest/llms.txt) and
[`llms-full.txt`](https://desdeo.readthedocs.io/en/latest/llms-full.txt) file are available to
appease our AI overlords.

## Contributing, reporting issues, and getting support

As DESDEO is an open source-project, anybody is welcome to contribute.

- **Contribute:** see [`CONTRIBUTING.md`](https://github.com/industrial-optimization-group/DESDEO/blob/master/CONTRIBUTING.md)
  for a quick start, and the [extensive contribution tutorial](https://desdeo.readthedocs.io/en/latest/tutorials/contributing/)
  in the documentation for the full development workflow.
- **Report a bug or suggest an idea:**
  [open an issue](https://github.com/industrial-optimization-group/DESDEO/issues/new/choose)
  using one of the provided templates.
- **Get help or discuss:** join the DESDEO Discord server
  [through this invite](https://discord.gg/uGCEgQTJyY).

All participation in the project is governed by our
[Code of Conduct](https://github.com/industrial-optimization-group/DESDEO/blob/master/CODE_OF_CONDUCT.md).

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

__Note__: A new article describing the latest iteration of the framework,
also known as _DESDEO 2.0_, is currently being prepared for submission to the
[Journal of Open Source Software (JOSS)](https://joss.theoj.org/). The content of
this repository's master branch is considered to be _DESDEO 2.0_. Once the JOSS
paper is published it will become the preferred reference. Until then, please use
the IEEE Access reference above. See the
[Citing DESDEO](https://desdeo.readthedocs.io/en/latest/home/citing/) page and the
[`CITATION.cff`](https://github.com/industrial-optimization-group/DESDEO/blob/master/CITATION.cff)
file for up-to-date citation metadata.

## Funding

Currently, DESDEO's development has been funded by projects granted by the
[Research Council of Finland](https://www.aka.fi/en/). The most recent ones
include:

- DESIDES (project 355346)
- UTOPIA (project 352784)
- DAEMON (project 322221)
- DESDEO (project 287496)
