This page documents the Pydantic interfaces for configuring Evolutionary Multi-Objective Optimization (EMO)
algorithms in DESDEO. Essentially, create a complete [`EMOOptions`][desdeo.emo.options.templates.EMOOptions] model by specifying options for
the various components of the algorithm. Pass the created model, along with the problem to be solved, to
[`emo_constructor`][desdeo.emo.options.templates.emo_constructor] to create an instance of the desired algorithm.
Popular pre-configured EMO methods include [NSGA-III][desdeo.emo.options.algorithms.nsga3_options],
[RVEA][desdeo.emo.options.algorithms.rvea_options], and [IBEA][desdeo.emo.options.algorithms.ibea_options].
You can find the actual implementation of these components in the
[EMO](./desdeo_emo.md) page.

## Algorithms
::: desdeo.emo.options.algorithms
    options:
        heading_level: 3
        show_root_heading: false

## Templates
::: desdeo.emo.options.templates
    options:
        heading_level: 3
        show_root_heading: false

## Crossover Operators
::: desdeo.emo.options.crossover
    options:
        heading_level: 3
        show_root_heading: false

## Generator Operators
::: desdeo.emo.options.generator
    options:
        heading_level: 3
        show_root_heading: false

## Mutation Operators
::: desdeo.emo.options.mutation
    options:
        heading_level: 3
        show_root_heading: false

## Repair Functions
::: desdeo.emo.options.repair
    options:
        heading_level: 3
        show_root_heading: false

## Scalar Selection Operators
::: desdeo.emo.options.scalar_selection
    options:
        heading_level: 3
        show_root_heading: false

## Selection Operators
::: desdeo.emo.options.selection
    options:
        heading_level: 3
        show_root_heading: false

## Termination Criteria
::: desdeo.emo.options.termination
    options:
        heading_level: 3
        show_root_heading: false
