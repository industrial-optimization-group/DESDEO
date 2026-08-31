---
title: 'DESDEO2: Core-Logic for Implementing Interactive Multiobjective Optimization Methods'
tags:
  - Python
  - multiobjective optimization
  - interactive multiobjective optimization
  - decision-support
  - optimization
authors:
  - name: Giovanni Misitano
    orcid: 0000-0002-4673-7388
    affiliation: 1
  - name: Bhupinder Saini
    orcid: 0000-0003-2455-3008
    affiliation: 1
  - name: Giomara Lárraga
    orcid: 0000-0001-8280-7040
    affiliation: 1
  - name: Juho Roponen
    orcid: 0000-0002-7921-0072
    affiliation: 1
  - name: Juuso Pajasmaa
    orcid: 0009-0005-9343-3028
    affiliation: 1
  - name: Matias Nieminen
    orcid: 0009-0003-7024-9880
    affiliation: 1
  - name: Babooshka Shavazipour
    orcid: 0000-0002-6516-4423
    affiliation: 1
  - name: Kaisa Miettinen
    orcid: 0000-0003-1013-4689
    affiliation: 2
affiliations:
  - name: University of Jyväskylä, Faculty of Information Technology, P.O. BOX 35 (Agora), FI-40014 University of Jyväskylä, Finland
    index: 1
  - name: University of Jyväskylä, P.O. Box 35 (C), FI-40014 University of Jyväskylä, Finland
    index: 2
date: 18 June 2026
bibliography: paper.bib
---

# Summary

Many real-world problems involve optimizing multiple conflicting objective
functions simultaneously: when designing a car, for example, reducing its
manufacturing cost typically comes at the expense of passenger safety and fuel
efficiency. In such multiobjective optimization problems, there is no single
optimal solution but, instead, multiple compromise solutions representing
different trade-offs.

To select the best compromise, a decision maker (a domain expert) must explore
the trade-offs and choose the solution they find most preferred. [Interactive
methods](https://desdeo.readthedocs.io/en/latest/tutorials/moo_primer/)
[@miettinen_nonlinear_1999; @mhp] support this task. They proceed step by step,
letting the decision maker examine candidate solutions, express preferences,
and steer the search toward more desirable solutions, learning along the way
about the problem and which preferences are achievable.

DESDEO2 is an open source software framework that provides a
foundation for implementing interactive multiobjective optimization methods. It
is a full redesign of the earlier DESDEO software [@misitano2021desdeo],
developed to address practical challenges in building reusable and reproducible
decision-support tools. We refer to the new version as DESDEO2 to distinguish
it from its predecessor; outside this context, it is simply known as DESDEO.
The scope of this paper is limited on the Python-based core-logic layer of
DESDEO2, which is fully self-contained and [usable as a standalone
library](https://desdeo.readthedocs.io/en/latest/howtoguides/full_example/).
Outside the core-logic, the broader framework also includes a web API and a
graphical web user interface, both under active development.

The core-logic provides explicit abstractions for problem modeling, method
execution, and preference handling, enabling interactive methods to be
implemented as modular, composable components that are decoupled from any
particular interface or deployment technology. This improves the
reproducibility of experiments, reusability, and extensibility. The core-logic
has been utilized in research and teaching, and is ready for broader use.

# Statement of need

Multiobjective optimization methods can be classified based on the timing when
the preference information of a decision maker is used
[@miettinen_nonlinear_1999]: *a priori* methods elicit preferences before
optimization, *a posteriori* methods first generate a representative set of
compromise solutions from which the decision maker selects one, while
*interactive* methods incorporate preferences iteratively to generate
new desirable solutions during the solution process. Because preferences unfold
in an iterative dialogue with the decision maker, interactive methods are
inherently software-intensive: any usable implementation must maintain state
across iterations, support diverse preference types, and let the decision maker
drive the control flow. Providing these capabilities as reusable components,
rather than re-implementing them for every method, is therefore valuable.

Existing open source frameworks do not explicitly provide reusable abstractions
for these iterative, preference-driven workflows. Without such software,
researchers must repeatedly reimplement not only optimization methods but also
interaction logic, state management, and preference handling, making systematic
experimentation laborious and difficult to reproduce [@afsar2021assessing;
@afsar2024experimental]. DESDEO2's core-logic is designed to fill this gap. It
targets researchers in interactive multiobjective optimization, who can
[experiment with existing
methods](https://desdeo.readthedocs.io/en/latest/home/features/) and develop
new ones; students learning about interactive methods; and practitioners
building decision-support systems.

The need for reusable implementations originally motivated the development of
earlier versions of DESDEO [@Ojalehto2019desdeo; @misitano2021desdeo], which
have enabled a range of successful research applications and practical
decision-support, e.g., [@afsar2023comparing; @afsar2023designing;
@burkotova2023interactive; @eyvindson2023multioptforest; @Kania2022integration;
@kania2023desmils]. However, accumulated experience revealed architectural
limitations: problem definitions were not clearly separated from method logic;
method state, such as iteration history and preference information, was not
explicitly modeled; and connectivity to external solvers and support for
important problem types, such as mixed-integer and scenario-based problems,
were limited.

# State of the field

Many open source frameworks support research on non-preference-based, *a
priori*, and *a posteriori* multiobjective optimization methods. Libraries, such
as jMetal [@durillo2010jmetal], PlatEMO [@PlatEMO], pymoo [@pymoo], Platypus
[@platypus], DEAP [@deap], pagmo/pygmo [@pagmo], and ParMOO [@parmoo], have
become commonplace, particularly for evolutionary multiobjective optimization
approaches; fewer software exist for scalarization-based methods, one notable
exception being vOptSolver and its successor MultiObjectiveAlgorithms.jl
[@dowson2025MOA.jl]. These tools provide rich support for solution generation
and benchmarking, and some offer preference-based mechanisms, such as reference
point integration. However, these features are designed mainly for *a priori*
use; support for the iterative, decision-maker-driven workflows that
characterize interactive methods is lacking. Since existing frameworks assume in
their core execution model a single optimization run without structured
intervention, accommodating interactive workflows would require changes to core
abstractions rather than incremental extensions, making it impractical to
contribute these features to existing tools.

Without dedicated frameworks, implementations of interactive methods
have typically been standalone prototypes or tightly coupled to specific
applications, making them difficult to reuse, compare, or extend beyond their
original context, e.g., [@Vetturini2025; @siraj2015priest]. Earlier versions of
DESDEO [@Ojalehto2016; @misitano2021desdeo] began addressing this lack by
providing an open source framework specifically for interactive methods, and
DESDEO2 builds on this foundation with its restructured and redesigned
core-logic. Rather than replacing existing optimization frameworks, DESDEO2
complements them by allowing solvers from other libraries, such as SciPy
[@2020SciPy-NMeth], to be used as computational backends within its interactive
method workflows.

# Software design

A foundational design decision in DESDEO2 is to represent optimization problems
in a serializable, language-agnostic form that can be defined once and then
evaluated, stored, and exchanged across tools and software boundaries. Building
on this, the core-logic addresses five key challenges identified from
experience with earlier versions of DESDEO: **C1** problem
modeling, **C2** language-agnostic problem representation, **C3** interactive
method state management, **C4** enabling extensions, and **C5** usage and
contribution support.

To address C1 and C2, DESDEO2 represents problem definitions as explicit
Pydantic^[<https://github.com/pydantic/pydantic>, accessed 19 August 2026.]
models in Python, which can be exported to and reconstructed from a [JSON
representation](https://desdeo.readthedocs.io/en/latest/explanation/problem_format/).
The model is designed for multiobjective optimization and supports [data-driven
settings](https://desdeo.readthedocs.io/en/latest/explanation/simulator_support/),
where objective and constraint values may be computed by external simulations
or opaque-box models. [Evaluators and
parsers](https://desdeo.readthedocs.io/en/latest/explanation/parsing_and_evaluating/)
bridge the model to external problem-definition ecosystems, and [solver
interfaces](https://desdeo.readthedocs.io/en/latest/explanation/solvers/)
connect the core-logic to external optimizers; supported backends currently
include Pyomo [@hart2011pyomo], SymPy [@meurer2017sympy], CVXPY
[@diamond2016cvxpy], Gurobi [@gurobi], Polars [@polars2025], SciPy
[@2020SciPy-NMeth], nevergrad [@nevergrad], and the COIN-OR solvers CBC
[@cbc], Bonmin [@bonami2008bonmin], and Ipopt [@wachter2006ipopt] (see the
[documentation](https://desdeo.readthedocs.io/en/latest/home/features/)).
Problems thus need to be modeled only once to be
[scalarized](https://desdeo.readthedocs.io/en/latest/explanation/scalarization/),
evaluated, and solved in numerous ways (C1), while remaining storable and
exchangeable across software boundaries, e.g., in databases [@saini2023using]
(C2).

Regarding state management (C3), earlier DESDEO versions coupled method state
tightly to execution logic, making it difficult to persist, inspect, or reuse
outside the running process. DESDEO2 instead provides explicit state
representations with well-defined transitions, leaving persistence to the
surrounding system, so interactive processes can be stored, resumed, and
compared systematically, particularly when integrated with databases in
decision-support systems; for standalone use, optional utility functions handle
common state bookkeeping locally.

To enable extensions (C4), instead of implementing methods as monolithic
algorithms, DESDEO2 decomposes functionality into reusable components for
problem handling, preference processing, and solution generation, e.g.,
scalarization and [evolutionary
operators](https://desdeo.readthedocs.io/en/latest/explanation/templates_and_pub_sub/).
Individual components can be replaced, hybridized [@sindhya2013hybrid], or
extended without re-implementing entire methods. Whereas the previous DESDEO
was distributed as four separate packages, DESDEO2 is a single cohesive package
whose [module
structure](https://desdeo.readthedocs.io/en/latest/home/structure/) mirrors
their high-level roles [@misitano2021desdeo] with fully redesigned contents: we
deliberately prioritized a solid foundation for future development over
backwards compatibility, supporting extensibility (C4) while keeping the
code-base navigable (C5).

Finally, to support usage and contribution (C5), the
[documentation](https://desdeo.readthedocs.io/en/latest/) is inspired by the
Diátaxis approach [@diataxis], separating tutorials, how-to guides,
explanations, and reference material, and the core-logic is accompanied by unit
tests targeting individual components. As a current limitation, DESDEO2's
web-facing components, which would extend it into a full decision-support
system, are not yet complete.

# Research impact statement

DESDEO has supported a sustained body of research on interactive multiobjective
optimization over several years. Earlier versions enabled comparative studies,
decision-support applications, and practical deployments across multiple
domains, such as engineering design, forest management, and production planning
(e.g., [@afsar2023comparing; @afsar2023designing; @burkotova2023interactive;
@eyvindson2023multioptforest; @Kania2022integration; @kania2023desmils]),
establishing both the community's need for reusable interactive method
implementations and the research experience that informed DESDEO2's design.

DESDEO2's redesign enables lines of research that its predecessor's
architecture could not readily support. Because interactive methods are now
decoupled from any particular interface and share common abstractions for
problems, preferences, and state, they can be implemented, hybridized, and
compared systematically rather than rebuilt as one-off prototypes. This makes
it feasible to combine scalarization-based and evolutionary methods within a
single framework, to switch methods or preference types during a
solution process, and to store, resume, and compare interactive sessions, which
supports reproducible studies of decision maker behavior, for example. The serializable
problem representation similarly extends such research to previously
impractical problem classes, including mixed-integer, scenario-based, and
simulation/data-driven problems.

DESDEO2's core-logic is actively used in ongoing research at the University of
Jyväskylä, supporting multiple Research Council of Finland funded projects and
doctoral and master-level theses; recent examples include
[@saini2025efficient; @pajasmaa2026nautili; @saini2026harvest;
@tahvanainen2026climate]. The framework has been presented at multiple
international conferences and used in university-level teaching, including an
international summer school in 2025, and in public demonstrations during
European Researchers' Night events. Since early 2024, DESDEO2's development
branches have accumulated over 2000 commits. Development is led by the
Multiobjective Optimization Group (<https://optgroup.it.jyu.fi/>) at the
University of Jyväskylä, and contributions from the broader research community
are warmly welcomed.

# AI usage disclosure

Generative tools based on large language models have been used to partly
support the development of DESDEO2: for code snippet generation, refactoring,
exploring the documentation and code bases of third-party libraries, and
writing documentation, such as parameter descriptions. All generated code and
documentation has been audited and validated by a human. Generative tools were
also used to plan the initial structure of this paper based on the authors'
earlier draft. All the final contents and ideas in this paper have been
produced and verified by the authors.

# Acknowledgements

We warmly thank the many students, trainees, researchers, and other external
contributors who have contributed, and continue to contribute, to the
development of DESDEO2 and its predecessors.

The development of DESDEO2 was supported by the Research Council of Finland
(grant numbers 355346 and 373063). The software is related to the thematic
research area DEMO (Decision Analytics utilizing Causal Models and
Multiobjective Optimization, <https://jyu.fi/demo>) of the University of
Jyväskylä.

# References
