# Pydantic Interface for Evolutionary Algorithms

DESDEO implements many different evolutionary algorithm (EA) components (generators, genetic operators, etc.) and templates in which to use them, as explained in [Evolutionary Algorithms in DESDEO](../templates_and_pub_sub). These components and templates can be used directly from Python code, as shown in the [Using Evolutionary Algorithms in DESDEO (Functional)](../../howtoguides/ea) guide.
 
However, that approach may be cumbersome for certain use-cases, such as when using DESDEO from a web application or when configuring an optimization run from a configuration file or running DESDEO from other programming languages. To facilitate these use-cases, DESDEO provides a Pydantic-based (or JSON-schema-based) interface for configuring and running evolutionary algorithms. This interface allows users to define their [optimization problems](../problem_format), algorithms, and parameters in a structured way, which can then be easily serialized to and from JSON or other formats.

Essentially, the entire configuration of an evolutionary algorithm run can be represented as a Pydantic/JSON model, which can be validated and parsed by DESDEO. This makes it easier to set up and run optimization tasks without needing to write extensive Python code. For example, NSGA-III is represented as:

```json
{
    "preference": null,
    "template": {
        "crossover": {
            "name": "SimulatedBinaryCrossover",
            "xover_probability": 0.5,
            "xover_distribution": 30.0
        },
        "mutation": {
            "name": "BoundedPolynomialMutation",
            "mutation_probability": null,
            "distribution_index": 20.0
        },
        "selection": {
            "name": "NSGA3Selector",
            "reference_vector_options": {
                ... // Options hidden for brevity
            },
            "invert_reference_vectors": false
        },
        "termination": {
            "name": "MaxGenerationsTerminator",
            "max_generations": 100
        },
        "generator": {
            "n_points": 100,
            "name": "LHSGenerator"
        },
        "repair": {
            "name": "NoRepair"
        },
        "use_archive": true,
        "seed": 42,
        "verbosity": 2,
        "algorithm_name": "NSGA3",
        "name": "Template1"
    }
}
```

The above JSON snippet represents the configuration for an NSGA-III algorithm, including its genetic operators, selection method, termination criteria, and other parameters. Users can modify these parameters as needed and run the optimization from this configuration. The schema for these configurations is defined by the Pydantic model [`EMOOptions`][desdeo.emo.options.templates.EMOOptions] and can be exported to JSON Schema by calling the `EMOOptions.model_json_schema()` method.
Examples of using this Pydantic interface can be found in the [Using Evolutionary Algorithms in DESDEO (Pydantic Interface)](../../howtoguides/ea_options) guide. 