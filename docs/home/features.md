# Implemented methods and features

This page gives an overview of what is currently implemented in DESDEO's
core-logic, so you can quickly find the interactive methods, algorithms, and
tools that are available and jump to the relevant guide and API reference.

Each entry links to a how-to guide (where one exists) and to the corresponding
section of the [API reference](../api/index.md).

!!! note "Keeping this page current"

    This page is maintained by hand. When adding a new interactive method,
    algorithm, operator, solver, or test problem to the core-logic, please add a
    row here as part of the same contribution.

## Interactive methods

### Scalarization-based (MCDM) methods

| Method | Description | Reference | Guide | API |
| --- | --- | --- | --- | --- |
| Reference Point Method | Projects a reference point onto the Pareto front using an achievement scalarizing function. | Wierzbicki, A. P. (1982). A mathematical basis for satisficing decision making. Mathematical Modelling, 3(5), 391-405. | [MCDM methods](../howtoguides/how_to_utilize_mcdm_methods.ipynb) | [mcdm](../api/desdeo_mcdm.md) |
| Synchronous NIMBUS | Classification-based method where the decision maker improves/relaxes objectives. | Miettinen, K., & Mäkelä, M. M. (2006). Synchronous approach in interactive multiobjective optimization. European Journal of Operational Research, 170(3), 909-922. | [MCDM methods](../howtoguides/how_to_utilize_mcdm_methods.ipynb) | [mcdm](../api/desdeo_mcdm.md) |
| G-NIMBUS | Group decision making variant of NIMBUS with a voting procedure. | No dedicated publication yet; group extension of NIMBUS (see the NIMBUS reference above). | [MCDM methods](../howtoguides/how_to_utilize_mcdm_methods.ipynb) | [mcdm](../api/desdeo_mcdm.md) |
| NAUTILUS | Approaches the Pareto front from the nadir point without trading off. | Miettinen, K., Eskelinen, P., Ruiz, F., & Luque, M. (2010). NAUTILUS method: An interactive technique in multiobjective optimization based on the nadir point. European Journal of Operational Research, 206(2), 426-434. | [MCDM methods](../howtoguides/how_to_utilize_mcdm_methods.ipynb) | [mcdm](../api/desdeo_mcdm.md) |
| NAUTILUS Navigator | Interactive navigation toward the Pareto front without trading off. | Ruiz, A. B., et al. (2019). NAUTILUS Navigator: free search interactive multiobjective optimization without trading-off. Journal of Global Optimization, 74(2), 213-231. | [NAUTILUS Navigator](../howtoguides/nautilus_navigator.md) | [mcdm](../api/desdeo_mcdm.md) |
| NAUTILI | Group decision making variant of the NAUTILUS family. | Pajasmaa, J., Saini, B. S., Shavazipour, B., Ruiz, F., Podkopaev, D., & Miettinen, K. (2026). NAUTILI: A trade-off-free interactive multiobjective optimization method for group decision making. Journal of Global Optimization. https://doi.org/10.1007/s10898-026-01617-6 | [NAUTILI](../howtoguides/nautili.md) | [mcdm](../api/desdeo_mcdm.md) |
| E-NAUTILUS | Computationally light NAUTILUS variant working from a precomputed set. | Ruiz, A. B., Sindhya, K., Miettinen, K., Ruiz, F., & Luque, M. (2015). E-NAUTILUS: A decision support system for complex multiobjective optimization problems based on the NAUTILUS method. European Journal of Operational Research, 246(1), 218-231. | [MCDM methods](../howtoguides/how_to_utilize_mcdm_methods.ipynb) | [mcdm](../api/desdeo_mcdm.md) |
| Pareto Navigator | Interactive navigation over a polyhedral approximation of the Pareto front. | Eskelinen, P., et al. (2010). Pareto navigator for interactive nonlinear multiobjective optimization. OR Spectrum, 32, 211-227. | [Pareto Navigator](../howtoguides/pareto_navigator.md) | [mcdm](../api/desdeo_mcdm.md) |

### Evolutionary (EMO) methods

Evolutionary methods are configured through option helpers in
`desdeo.emo.options.algorithms` and run with the templates in
`desdeo.emo.methods.templates`. Mixed-integer variants are available for RVEA,
NSGA-III, and IBEA.

| Algorithm | Description | Reference | Guide | API |
| --- | --- | --- | --- | --- |
| RVEA | Reference Vector Guided Evolutionary Algorithm. | Cheng, R., Jin, Y., Olhofer, M., & Sendhoff, B. (2016). A reference vector guided evolutionary algorithm for many-objective optimization. IEEE Transactions on Evolutionary Computation, 20(5), 773-791. | [Evolutionary algorithms](../howtoguides/ea.ipynb) | [emo](../api/desdeo_emo.md) |
| NSGA-II | Non-dominated sorting genetic algorithm with crowding distance. | Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. IEEE Transactions on Evolutionary Computation, 6(2), 182-197. | [Evolutionary algorithms](../howtoguides/ea.ipynb) | [emo](../api/desdeo_emo.md) |
| NSGA-III | Reference-point based many-objective genetic algorithm. | Deb, K., & Jain, H. (2014). An evolutionary many-objective optimization algorithm using reference-point-based nondominated sorting approach, part I: solving problems with box constraints. IEEE Transactions on Evolutionary Computation, 18(4), 577-601. | [Evolutionary algorithms](../howtoguides/ea.ipynb) | [emo](../api/desdeo_emo.md) |
| IBEA | Indicator-based evolutionary algorithm. | Zitzler, E., & Künzli, S. (2004). Indicator-based selection in multiobjective search. In Parallel Problem Solving from Nature (PPSN VIII), LNCS 3242, 832-842. Springer. | [Evolutionary algorithms](../howtoguides/ea.ipynb) | [emo](../api/desdeo_emo.md) |

See [Configuring evolutionary algorithms](../howtoguides/ea_options.ipynb) and
the [EMO Pydantic interface](../api/EMO%20Options.md) for the available options.

## Building blocks and components

### Scalarization functions

Available in `desdeo.tools.scalarization` (single decision maker) and
`desdeo.tools.group_scalarization` (group decision making). Most come in both
differentiable (`_diff`) and non-differentiable (`_nondiff`) forms.

| Family | Single DM | Group |
| --- | --- | --- |
| Achievement scalarizing function (ASF) | yes (incl. generic forms) | yes (incl. aggregated) |
| NIMBUS | yes | yes (incl. compromise) |
| STOM | yes | yes (incl. aggregated) |
| GUESS | yes | yes (incl. aggregated) |
| Weighted sums | yes | |
| Epsilon-constraint | yes | |
| Objective as scalarization | yes | |
| Desirability functions | yes | |
| IOPIS | yes | |
| Scenario-based | | yes |

Guides: [Scalarization](../explanation/scalarization.ipynb),
[Scalarization methods](../explanation/scalarization_methods.ipynb).
API: [tools](../api/desdeo_tools.md).

### Evolutionary operators

| Component | Examples | API |
| --- | --- | --- |
| Generators | random, Latin hypercube, binary/integer/mixed-integer, archive, seeded hybrid | [emo](../api/desdeo_emo.md) |
| Crossover | simulated binary, single-point binary, blend-alpha, exponential, mixed-integer | [emo](../api/desdeo_emo.md) |
| Mutation | bounded polynomial, binary flip, integer/mixed-integer, power, non-uniform, self-adaptive Gaussian | [emo](../api/desdeo_emo.md) |
| Selection | RVEA, NSGA-II, NSGA-III, IBEA selectors | [emo](../api/desdeo_emo.md) |
| Scalar selection | tournament, roulette wheel | [emo](../api/desdeo_emo.md) |
| Termination | max generations, max evaluations | [emo](../api/desdeo_emo.md) |
| Archivers | non-dominated and feasibility archives | [emo](../api/desdeo_emo.md) |

Guide: [Implementing evolutionary algorithms](../howtoguides/how_to_implement_ea.md).

### Solvers and interfaces

DESDEO interfaces with several optimizers; `desdeo.tools.guess_best_solver`
selects a suitable one automatically based on the problem.

| Solver | Type | Notes |
| --- | --- | --- |
| Gurobi (`GurobipySolver`, `PersistentGurobipySolver`) | LP / MIP | Commercial; license required |
| Pyomo (`PyomoGurobiSolver`, `PyomoIpoptSolver`, `PyomoBonminSolver`, `PyomoCBCSolver`) | LP / NLP / MINLP / MIP | Via the Pyomo interface |
| SciPy (`ScipyMinimizeSolver`, `ScipyDeSolver`) | NLP / global | `scipy.optimize` |
| CVXPY (`CVXPYSolver`) | Convex | Requires a convex formulation |
| Nevergrad (`NevergradGenericSolver`) | Derivative-free | Black-box optimization |
| Proximal (`ProximalSolver`) | Data-based | For discrete, data-based problems |

Guide: [Solvers](../explanation/solvers.ipynb). API: [tools](../api/desdeo_tools.md).

### Quality indicators

Available in `desdeo.tools.indicators_unary` and
`desdeo.tools.indicators_binary`: hypervolume, IGD+, R2, R-metric, additive
epsilon (unary and binary), and related batch variants.
API: [tools](../api/desdeo_tools.md).

## Decision-support utilities

| Feature | Description | Guide | API |
| --- | --- | --- | --- |
| Artificial decision makers (ADMs) | Automated decision makers for benchmarking interactive methods (Chen et al. and Afsar et al. variants). | [Using ADMs](../howtoguides/how_to_use_adms.ipynb) | [adm](../api/desdeo_adm.md) |
| Group decision making (GDM) | Voting rules (majority, plurality), preference aggregation, and SCORE bands. | [GDM with SCORE bands](../howtoguides/gdm_score.ipynb) | [gdm](../api/desdeo_gdm.md) |
| Explanations | SHAP-based explanations of solutions and Lagrange multiplier utilities. | | [explanations](../api/desdeo_explanations.md) |
| Representative solution sets | Generate a representative subset of solutions (iterative Pareto representer). | [Representative sets](../howtoguides/IPR.ipynb) | [tools](../api/desdeo_tools.md) |

## Problem modeling and test problems

### Problem types

DESDEO's [problem format](../explanation/problem_format.ipynb) supports
analytical, data-based, simulation-based, and surrogate-based problems, with
continuous and (mixed-)integer variables, as well as scenario-based problems.

Guides: [How to define a problem](../howtoguides/how_to_define_a_problem.ipynb),
[Problems with surrogates](../howtoguides/advancedSurrogates.ipynb),
[Simulator support](../explanation/simulator_support.ipynb).
API: [problem](../api/desdeo_problem.md).

### Built-in test problems

Available in `desdeo.problem.testproblems`.

| Category | Problems |
| --- | --- |
| Benchmark suites | DTLZ (1, 2, 4), ZDT (1-4, 6), RE (21-24) |
| Engineering design | multiobjective welded beam (6 variants), rocket injector design |
| Real-world | river pollution, forest management, Spanish sustainability, summer cabin battery |
| Combinatorial / mixed-integer | knapsack, MOMIP |
| Pedagogical / synthetic | various `simple_*` problems, the cake problem |

Guide: [Test problems](../explanation/test_problems.ipynb).
API: [problem](../api/desdeo_problem.md).
