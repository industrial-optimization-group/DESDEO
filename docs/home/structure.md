# The structure of DESDEO

In the big picture, DESDEO is not just a collection of interactive
multiobjective optimization methods, but a __full stack__ solution (which can be
run as an application) to provide decision-support for decision makers to tackle
real-life multiobjective optimization problems by utilizing interactive methods.
Being a full stack solution, it consists of three main components:

1. [__the core-logic__](#the-core-logic),
2. [__the web-API__](#the-web-api), and
3. [__the web-GUI__](#the-web-gui).

We will describe each of these components in the following sections.

## The core-logic

The core-logic of DESDEO is implemented in Python and contains tools and
functionalities for modeling multiobjective optimization problems and
implementing interactive multiobjective optimization methods. This also includes
a plethora of other functionalities that are required, such as scalarization
utilities and (programmatic) interfaces to existing optimization software.

The core-logic itself consists of __four main modules__. The first of these is
`desdeo.problem`, which has functions and classes for problem modeling, parsing,
and evaluation. In addition, the module contains also pre-defined test problems
that can be utilized to readily benchmark and pilot, e.g., interactive methods.
[The problem model](../explanation/problem_format.ipynb) is also defined in
`desdeo.problem`, which is at the very core when it comes to how multiobjective
optimization problems are handled in the core-logic.

The second main module is `desdeo.tools`. This module contains additional
utilities, which can be considered to be generic, and not specific to any type
of interactive methods (such as MCDM or EMO, covered next). This includes
scalarization and solver interfaces to existing optimization algorithms, for
example, Gurobi, or utilities, such as the payoff-table method.

Next, we have the first of the main modules that are contain logic for
implementing interactive multiobjective optimization methods, `desdeo.mcdm`. The
name _MCDM_ refers to interactive methods that have been inspired by more
traditional approaches in the field of multi-criteria decision-making. In
practice, these are interactive methods that often rely on scalarization in one
way or another, and utilize exact optimizers to generate solutions that can be
guaranteed (to a varying degree) to be Pareto optimal. The methods have been
implemented in a modular fashion, meaning, that relevant steps of different
methods are implemented as functions. These functions can be mixed and matched
to create existing interactive methods, or completely new ones with relative
little effort.

Lastly, the second of the main modules containing logic for implementing interactive
methods is `desdeo.emo`. This module is for evolutionary multiobjective optimization
methods, which utilize heuristic to improve a population of solutions iteratively.
Unlike MCDM methods, EMO (evolutionary multiobjective optimization) methods are implemented
using [templates and publish-subscribe patterns](../explanation/templates_and_pub_sub.ipynb).
Nonetheless, the `desdeo.emo` contains many different cross-over, mutation, selection, and
termination operators, which can be combined in different way to create existing
or new EMO methods.

Apart from the main modules, other modules exist as well. The main modules,
and other, can be found in the `/desdeo/` directory of the source tree.

## The web-API

The web-API (application programming interface) is a web interface that allows
software and applications to utilize DESDEO through HTTP endpoints over a web
connection. Its main purpose is to enable other applications to have access
to the core-logic of DESDEO.

In addition, the web-API introduced a __database__. This allows DESDEO
to handle users and users sessions, which is critical for building
decision-support tools.

!!! Note "WIP"

    The web-API is currently under heavy development. Be free to explore it
    and contribute, but understand things will be changing fast and nothing is stable!

The web-API can be found in the directory `desdeo/api/` in the project source tree.

## The web-GUI

The web-GUI is the frontend part of DESDEO. It implements an interface, which
allows users to utilize DESDEO through a graphical user interface.
Development of the web-GUI is in early stages of development.

!!! Note "WIP"

    The web-GUI is currently under heavy development. Be free to explore it
    and contribute, but understand things will be changing fast and nothing is stable!

The web-GUI will be found in the directory `desdeo/gui/` in the project source tree.