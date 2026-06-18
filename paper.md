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
functions simultaneously, where improving the value of one objective
necessarily comes at the expense of at least one of the others. Such problems
are called multiobjective optimization problems. For example, when designing a
car, reducing its manufacturing cost typically comes at the expense of
passenger safety and fuel efficiency. Since not all objective functions can
reach their individual optima simultaneously, there are trade-offs to be
balanced with. Thus, there is no single optimal solution but, instead,
multiple compromise solutions representing different trade-offs.

To select the best compromise, a decision maker (a person with expertise in the
problem domain) must explore the trade-offs and choose the solution they find
most preferred. This choice is inherently subjective, reflecting the decision
maker's own priorities and domain knowledge. Interactive methods
[@miettinen_nonlinear_1999; @mhp] support this task. They proceed step by step,
letting the decision maker examine candidate solutions, express what they
prefer, and steer the search toward more desirable solutions. Along the way,
the decision maker learns about the problem and about which preferences are
achievable, and can revise those preferences between steps.

DESDEO2 is an open source software framework that provides a complete
foundation for implementing interactive multiobjective optimization methods. It
is a full redesign of the earlier DESDEO software [@misitano2021desdeo],
developed to address practical challenges in building reusable and reproducible
decision-support tools. Throughout this paper, we refer to the new version as
DESDEO2 to distinguish it from its predecessor. Outside this context, it is
simply known as DESDEO. This paper focuses on the Python-based core-logic layer
of DESDEO2, which is fully self-contained and usable as a standalone library.
However, the broader software framework also includes web-facing components,
including a web API and a graphical web user interface, both of which are
currently under active development.

The core-logic provides explicit abstractions for problem modeling, method
execution, and preference handling. This enables interactive methods to be
implemented as modular, composable components. Crucially, it separates the
algorithmic aspects of interactive methods from any particular interface or
deployment technology. This design avoids problems that arise when interaction
logic, computation, and presentation, such as visualizations, are tightly
coupled, improving the reproducibility of experiments, as well as reusability
and extensibility. Therefore, different interactive methods can conveniently be
added.

The core-logic of DESDEO2 has been successfully utilized in research and
teaching, and it is now ready for broader use. It provides the necessary
abstractions for systematically experimenting with interactive multiobjective
optimization methods. Its modular design ensures that future methodological
developments can be incorporated without breaking changes to its fundamental
components.

# Statement of need

Besides interactive multiobjective optimization methods, there are also other
approaches. They can be classified based on the timing when the preference
information (preferences for short) of a decision maker are used
[@miettinen_nonlinear_1999]. *A priori* methods elicit preferences before
optimization and use them to find a solution that best reflects them, while *a
posteriori* methods first generate a representative set of compromise solutions
from which the decision maker then must select a preferred one. Unlike the
other classes, *interactive* methods incorporate preference information
iteratively during the solution process [@miettinen_nonlinear_1999] and
generate solutions that reflect the preferences giving the decision maker an
opportunity to update the preferences. Because they unfold as an iterative
dialogue with the decision maker, interactive methods are inherently
software-intensive: any usable implementation must maintain state across
iterations, support diverse preference models, and let the decision maker drive
the control flow. Providing these capabilities as reusable components, rather
than re-implementing them for every method, is therefore especially valuable.

Existing open source frameworks do not explicitly provide reusable abstractions
for these iterative, preference-driven workflows. Without such software,
researchers must repeatedly reimplement not only optimization methods but also
interaction logic, state management, and preference handling. This makes
systematic experimentation laborious and difficult to
reproduce [@afsar2021assessing; @afsar2024experimental]. DESDEO2's core
logic is designed to fill this gap. It targets researchers in interactive
multiobjective optimization, who can experiment with existing methods and
develop new ones; students, for whom it serves as a tool for learning about
interactive methods; and practitioners building decision-support systems.

The need for reusable implementations of interactive multiobjective
optimization methods originally motivated the development of earlier versions
of DESDEO [@Ojalehto2019desdeo; @misitano2021desdeo], which have enabled a
range of successful research applications and practical decision-support, e.g.,
[@afsar2023comparing; @afsar2023designing; @burkotova2023interactive;
@eyvindson2023multioptforest; @Kania2022integration; @kania2023desmils].
However, accumulated experience revealed architectural limitations. In
particular, optimization problem definitions were not clearly separated from
method logic, and method state, such as iteration history, and preference
information, was not explicitly modeled. This made it difficult to reuse,
extend, or compose methods independently of specific interfaces. The earlier
design also offered limited connectivity to external solvers and limited
support for important problem types, such as mixed-integer and scenario-based
problems.

The modular structure has enabled implementing different interactive
multiobjective optimization methods, both scalarization-based and evolutionary
ones in DESDEO2. It is also convenient to add new implementations, including
hybrids of existing methods. This environment with different methods enables
their comparison and flexible usage, e.g., switching the methods during the
solution process if the decision maker wishes to change the type of preference
information, for instance.

# State of the field

Many open source software frameworks support research on non-preference-based,
*a priori*, and *a posteriori* multiobjective optimization methods. Libraries,
such as jMetal [@durillo2010jmetal], PlatEMO [@PlatEMO], pymoo [@pymoo], Platypus
[@platypus], DEAP [@deap], pagmo/pygmo [@pagmo], and ParMOO [@parmoo],
have become commonplace for developing and evaluating multiobjective
optimization methods, particularly evolutionary multiobjective optimization
(EMO) approaches; while fewer software exist for scalarization-based methods,
one notable exception being vOptSolver and its successor
MultiObjectiveAlgorithms.jl [@dowson2025MOA.jl]. The existing tools provide
rich support for solution generation, algorithm benchmarking and performance
evaluation for *a posteriori* approaches in particular. Some offer
preference-based mechanisms such as reference point integration or
decomposition-based approaches. However, these features are designed for *a
priori* approaches. Support for iterative, decision-maker-driven workflows that
characterize interactive methods is lacking.

Existing frameworks typically assume a single optimization run that proceeds to
completion without structured intervention in their core execution model.
Accommodating workflows for interactive methods would require changes to these
core abstractions rather than incremental extensions. This makes it impractical
to address the research goals motivating DESDEO2 by contributing features to
existing tools.

In the absence of dedicated frameworks, implementations of interactive methods
have typically been developed as standalone prototypes or tightly coupled to
specific applications, making them difficult to reuse, compare, or extend
beyond their original context, e.g., [@Vetturini2025; @siraj2015priest].
Earlier versions of DESDEO [@Ojalehto2016; @misitano2021desdeo] began
addressing the lack of general tools by providing an open source framework
specifically for interactive methods. DESDEO2 builds on this foundation with
its restructured and redesigned core-logic.

DESDEO2 is positioned as a research infrastructure for interactive
multiobjective optimization. Rather than replacing existing optimization
frameworks, it complements them by allowing solvers from other libraries, such
as SciPy [@2020SciPy-NMeth], to be used as computational backends within
DESDEO2's interactive method workflows. This allows researchers to leverage
mature optimization tools while working within an architecture designed for the
specific demands of interactive multiobjective optimization.

# Software design

A foundational design decision in DESDEO2 is to represent optimization problems
in a serializable, language-agnostic form that can be defined once and then
evaluated, stored, and exchanged across tools and software boundaries. Building
on this, the core-logic of DESDEO2 has been designed to address five key
challenges identified from experiences with earlier versions of DESDEO:

- **C1** problem modeling,
- **C2** language-agnostic problem representation,
- **C3** interactive method state management,
- **C4** enabling extensions, and
- **C5** usage and contribution support.

To address problem modeling (C1) and a language-agnostic problem representation
(C2), DESDEO2 represents problem definitions in Python as explicit models built
with Pydantic^[<https://github.com/pydantic/pydantic>, accessed 17 June 2026.], a Python
library for data validation. These models can be exported to and reconstructed
from a JSON representation. The problem model is explicitly designed for
multiobjective optimization and also supports data-driven evaluation settings
in which objective and constraint function values may be computed using
external simulations or opaque-box models. This JSON-based representation makes
the problem structure accessible across the core-logic while enabling
validation, serialization, and interoperability beyond the Python runtime,
e.g., when utilizing databases [@saini2023using]. The problem model is fed to
evaluators and parsers, which bridge the model to external problem-definition
ecosystems when needed. Optimization is done through solver interfaces that
connect the core-logic to external optimization libraries or executables. At
present, problems can be parsed and evaluated using Pyomo [@hart2011pyomo],
SymPy [@meurer2017sympy], CVXPY [@diamond2016cvxpy], Gurobi [@gurobi], and Polars
[@polars2025], and solved through optimizers from SciPy [@2020SciPy-NMeth], the
COIN-OR^[<https://www.coin-or.org/>, accessed 17 June 2026.] suite (CBC [@cbc],
Bonmin [@bonami2008bonmin], and Ipopt [@wachter2006ipopt], accessed via Pyomo),
Gurobi, CVXPY, and nevergrad [@nevergrad]. For
example, a problem can be parsed and evaluated as a Pyomo model and then
solved, after scalarization (turning a multiobjective problem into one or more
single-objective subproblems), using a COIN-OR optimizer. This design
prioritizes compatibility with diverse problem types and existing optimization
ecosystems (C1), while allowing problem and method information to be stored and
exchanged across software boundaries (C2). The result is flexible, as problems
need to be modeled only once in DESDEO2 to be solved and manipulated in
numerous ways.

Another key redesign decision concerns the interactive method state management
(C3). In earlier DESDEO versions, a method state was tightly coupled to
execution logic, making it difficult to persist, inspect, or reuse outside the
running process. Instead, DESDEO2 provides explicit state representations with
well-defined transitions, leaving persistence and management to the surrounding
system. This enables interactive processes to be stored, resumed, and compared
systematically, particularly when integrated with databases in broader
decision-support systems. For standalone use as a Python library, optional
utility functions handle common state bookkeeping locally.

To address enabling extensions (C4), DESDEO2 adopts a component-based structure
for interactive methods, reflected in the separation between method components
and the supporting problem and solver infrastructure. Instead of implementing
methods as monolithic algorithms, DESDEO2 decomposes functionality into
reusable components for problem handling, preference processing, and solution
generation. This supports research workflows where individual components (e.g.,
preference processing, scalarization, and evolutionary operators) must be
replaced, hybridized (combined into new hybrid methods) [@sindhya2013hybrid],
or extended without re-implementing entire methods. This enables novel concepts
and future research directions to be incorporated with minimal architectural
friction.

Whereas the previous DESDEO was distributed as four separate packages, each
maintained in its own repository, DESDEO2 brings them together in a single
repository as one cohesive package. Its core-logic is organized into modules
that mirror the high-level roles of those predecessors [@misitano2021desdeo]:
problem modeling, general utilities, scalarization-based methods, and
evolutionary methods. Their contents, however, have been fully redesigned: we
deliberately chose a clean redesign over backwards compatibility, prioritizing a
solid foundation for future development over preserving the previous interfaces.
This structure supports extensibility (C4) while keeping the code-base navigable
for users and contributors (C5).

Finally, to support usage and contribution (C5), we treat documentation and
testing in DESDEO2 as integral to sustainable research software. The
documentation structure is inspired by the Diátaxis approach [@diataxis],
separating learning-oriented *tutorials*, goal-oriented *how-to guides*,
understanding-oriented *explanations*, and a technical reference material. This
structure supports both new and experienced users, as well as contributors, and
is intended to reduce the overhead of adopting and extending the core-logic in
research and teaching contexts. To support ongoing development and
reproducibility, the core-logic is accompanied by unit tests targeting
individual components, e.g., interactive method building blocks. As DESDEO2's
broader software stack matures, integration testing can be expanded
accordingly, but the core-logic is already designed to support such evolution
without backwards-incompatible changes to its interfaces. As a current
limitation, DESDEO2's web-facing components, which would extend it into a full
decision-support system, are not yet complete.

# Research impact statement

DESDEO has supported a sustained line of research on interactive multiobjective
optimization over several years. Earlier versions enabled comparative studies,
decision-support applications, and practical deployments across multiple
domains, such as engineering design, forest management, and production planning
(e.g., [@afsar2023comparing; @afsar2023designing; @burkotova2023interactive;
@eyvindson2023multioptforest; @Kania2022integration; @kania2023desmils]). This
established both the multiobjective optimization community's need for reusable
interactive method implementations and a foundation of research experience that
directly informed the design of DESDEO2.

DESDEO2's core-logic is actively used in ongoing research at the University of
Jyväskylä, supporting multiple Research Council of Finland funded research
projects and both doctoral and master-level theses. Recent examples include
[@saini2025efficient; @pajasmaa2026nautili; @saini2026harvest;
@tahvanainen2026climate]. The framework has also been presented at the
International Conference on Multiple Criteria Decision Making, the European
Conference on Operational Research, and the International Conference on
Evolutionary Multi-Criterion Optimization.

DESDEO2 has been used in university-level teaching, including multiple courses
and an international summer school at the University of Jyväskylä in 2025 with
over 20 participants. Its predecessor was also used in courses in Spain and
the Netherlands. DESDEO2 has additionally been used in public demonstrations of
interactive multiobjective optimization during European Researchers' Night
events at the University of Jyväskylä.

Since early 2024, DESDEO2's development branches have accumulated over 2000
commits and over 500 issues. Development is led by the Multiobjective
Optimization Group (<https://optgroup.it.jyu.fi/>) at the University of
Jyväskylä, with contributions from students and researchers internationally.
The project remains openly developed, and contributions from the broader
research community are warmly welcomed.

# AI usage disclosure

Generative tools based on large language models have been used to partly
support the development of DESDEO2 for code snippet generation, refactoring,
and as a tool to explore the documentation and code bases of third-party
libraries. All the generated code present in the software repository has always
been audited and validated by a human. Generative tools have also been used to
support the writing of documentation, mostly in automating arduous tasks, such
as parameter descriptions, which are quick to verify but laborious to write.
The correctness of these has always been validated by a human. Lastly,
generative tools have been utilized in support of planning the initial
structure of this paper based on existing ideas and text content produced by
the authors in an earlier draft. All the final contents and ideas in this paper
have been produced and verified by the authors.

# Acknowledgements

We warmly thank everybody who has contributed to the development of DESDEO2 and
its predecessors. Many students, trainees, researchers, and other external
contributors have contributed, and continue to contribute, directly and
indirectly to this collaborative effort.

The development of DESDEO2 was supported by the Research Council of Finland
(grant number 355346). The software is related to the thematic research area
DEMO (Decision Analytics utilizing Causal Models and Multiobjective
Optimization, <https://jyu.fi/demo>) of the University of Jyväskylä.

# References
