# How to Implement Evolutionary Algorithm components in DESDEO

Implementing evolutionary algorithm (EA) components though not difficult, is not a trivial task.
Once you understand how to implement EA components in DESDEO, you will be able to create entirely new EAs or modify
existing ones to better suit your optimization needs.
Note that quite a few EA components are already implemented in DESDEO, so before implementing your own, check if an
existing one fits your needs.
This guide provides a step-by-step approach to implementing EA components in DESDEO. As a prerequisite, you should
familiarize yourself with:

- How multiobjective optimization problems are structured in DESDEO (see [here](../../explanation/problem_format)),
- How evolutionary algorithms are structured in DESDEO (see [explanation](../../explanation/templates_and_pub_sub) and [usage](../ea)),
- How the Pydantic interface for EAs work (see [explanation](../../explanation/pydantic_interface) and [usage](../ea_options)).

Once you are familiar with these concepts, you can follow the steps below to implement your own EA components in DESDEO:

1. Implement the EA component as a Python method.
2. Classify the inputs of the method into three categories: initialization parameters, parameters that it can get from
   the template, and parameters that it will have to receive via the publisher-subscriber mechanism.
3. Implement a Python class that inherits from [Subscriber](../../api/desdeo_tools/#desdeo.tools.patterns.Subscriber) as a wrapper for your method.
4. Implement a Pydantic model for your EA component to make sure it can be used through the Pydantic interface.
5. Test your implementation to ensure it works as expected.

Let's implement a simple EA component as an example: an adaptive mutation operator that adjusts the mutation rate based
on how long the optimization has been running.

## Step 1: Implement the EA component as a Python method

The operator takes a population of offspring solutions as a NumPy array and applies mutation to each solution based on
how many generations have passed relative to the maximum number of generations. The mutation rate decreases as the
number of generations increases. The mutation is bound by specified minimum and maximum mutation values.

```python
def adaptive_mutation(
    offspring: np.ndarray,
    generation: int, 
    max_generations: int, 
    base_mutation_rate: float, 
    mut_min: float, 
    mut_max: float
    ) -> np.ndarray:
    mutation_rate = base_mutation_rate * (1 - generation / max_generations)
    for i in range(offspring.shape[0]):
        if np.random.rand() < mutation_rate:
            mutation_value = np.random.normal(mut_min, mut_max, size=offspring.shape[1])
            offspring[i] += mutation_value
    return offspring
```

!!! note
    The above implementation is just a simple example and not a suggestion for a practical mutation operator. Moreover,
    the implementation is not optimized for performance. Check NumPy's vectorized operations or Numba's JIT compilation
    for better performance in real-world applications.

## Step 2: Classify the inputs of the method

The inputs of the `adaptive_mutation` method can be classified as follows:

- Initialization parameters: `base_mutation_rate`, `mut_min`, `mut_max`. These are parameters that define the behavior
    of the mutation operator and are set when the operator is created.
- Template parameters: To check whether an input parameter can be obtained from the template, check the implementation
    of the templates, or the implementation of existing EA components (in this case, other mutation operators). The
    source code for [`template1`](../../api/desdeo_emo/#desdeo.emo.methods.templates.template1) shows that mutation operators can only get
    the parent and offspring populations from the template. Therefore, in this case, `offspring` is a template parameter.
    However, the data is provided as a Polars DataFrame, so we will need to convert it to a NumPy array in the wrapper class.
- Publisher-subscriber parameters: Any remaining parameters that are not initialization parameters or template parameters
    must be provided via the publisher-subscriber mechanism. In this case, `generation` and `max_generations` fall
    into this category. Note that as `max_generations` is a constant value throughout the optimization, it could also be
    considered as an initialization parameter. However, the Publisher-Subscriber mechanism provides this information,
    so we will use it from there. This reduces the number of parameters we need to set when creating the mutation operator.
    It also makes sure that we do not accidentally set a wrong value for `max_generations`.

## Step 3: Implement a Subscriber wrapper class

Now that we have classified the inputs, we can implement a Subscriber wrapper class for the `adaptive_mutation` method.
The class will inherit from [Subscriber](../../api/desdeo_tools/#desdeo.tools.patterns.Subscriber). As stated [here](../../explanation/templates_and_pub_sub/#publish-subscribe-pattern),
we need to implement four attributes/methods: 

1. Attribute `provided_topics`: Topics for the publisher subscriber mechanism that the component will provide data for.
2. Attribute `interested_topics`: Topics for the publisher subscriber mechanism that the component needs data from.
3. Method `state`: A method that creates the messages to be sent to the `Publisher`.
4. Method `update`: A method that receives messages from the `Publisher` and performs updates the component.

While implementing the class, make sure to follow the structure of other similar components in DESDEO. To check the 
available message topics and structures, check the [docs](../../api/desdeo_tools/#message-topics).

```python
class AdaptiveMutation(Subscriber):
    @property
    def provided_topics(self) -> dict[int, Sequence[MutationMessageTopics]]:
        """The message topics provided by the mutation operator, grouped by verbosity level."""
        return {
            0: [],
            1: [MutationMessageTopics.MUTATION_PROBABILITY],
        }

    @property
    def interested_topics(self):
        """The message topics that the mutation operator is interested in."""
        return [TerminatorMessageTopics.GENERATION, TerminatorMessageTopics.MAX_GENERATIONS]

    def __init__(
        self,
        problem: Problem,
        base_mutation_rate: float,
        mut_min: float,
        mut_max: float,
        publisher: Publisher,
        verbosity: int,
    ):
        super().__init__(problem=problem, publisher=publisher, verbosity=verbosity)
        self.base_mutation_rate = base_mutation_rate
        # You can add checks to make sure that the initialization parameters are valid
        self.mut_min = mut_min
        self.mut_max = mut_max
        self.generation = None
        self.mutation_probability = None
        self.max_generations = None
        self.offsprings_original = None
        self.offsprings_mutated = None
    
    def do(self, offsprings: pl.DataFrame, parents: pl.DataFrame) -> pl.DataFrame:
        """Apply adaptive mutation to the offspring population."""
        if self.generation is None or self.max_generations is None:
            raise ValueError("Generation and max_generations must be set before calling do method.")
        # Convert Polars DataFrame to NumPy array
        self.offsprings_original = copy(offsprings)
        offspring_array = offsprings.to_numpy()
        columns = offsprings.columns
        mutated_offspring_array = adaptive_mutation(
            offspring=offspring_array,
            generation=self.generation,
            max_generations=self.max_generations,
            base_mutation_rate=self.base_mutation_rate,
            mut_min=self.mut_min,
            mut_max=self.mut_max
        )
        # Convert back to Polars DataFrame
        self.offsprings_mutated = pl.DataFrame(mutated_offspring_array, schema=columns)
        return self.offsprings_mutated

    def state(self) -> Sequence[Message]:
        """Return state messages."""
        if self.verbosity == 0:
            return []
        mutation_probability = self.base_mutation_rate * (1 - self.generation / self.max_generations)
        return [
            FloatMessage(
                topic=MutationMessageTopics.MUTATION_PROBABILITY,
                source=self.__class__.__name__,
                value=mutation_probability,
            ),
        ]
    def update(self, message: Message) -> None:
    """Update the parameters for adaptive mutation.

    Args:
        message (Message): The message to update the parameters. The message should be coming from the
            Terminator operator (via the Publisher).
    """
    if message.topic == TerminatorMessageTopics.GENERATION:
        self.generation = message.value
    if message.topic == TerminatorMessageTopics.MAX_GENERATIONS:
        self.max_generations = message.value
    return
```

## Step 4: Implement a Pydantic model

This is an optional step. You should be able to use the `AdaptiveMutation` operator without a Pydantic model by directly
instantiating it and passing it to the EA template. However, if you want the operator to be usable through the Pydantic
and want to make it available for others to use easily (including via the Web API), you need to implement a Pydantic
model for it.

This model needs to be implemented in `desdeo/emo/options/mutation.py`. It is a simple pydantic
model that contains the initialization parameters for the mutation operator, along with a `name` attribute to identify
the operator. It should also contain some sensible default values for the parameters.

```python
class AdaptiveMutationOptions(Pydantic.BaseModel):
    """Pydantic model for AdaptiveMutation operator."""

    name: Literal["AdaptiveMutation"] = "AdaptiveMutation"
    base_mutation_rate: float = Field(
        0.1,
        description="Base mutation rate for the adaptive mutation operator.",
        gt=0,
        lt=1,
    )
    mut_min: float = Field(
        0.1,
        description="Minimum mutation value.",
        ge=0,
        lt=1,
    )
    mut_max: float = Field(
        0.5,
        description="Maximum mutation value.",
        ge=0,
        lt=1,
    )
```
Finally, edit the `MutationOptions` union type to include the new model, and edit the `mutation_types` dictionary
in the `mutation_constructor` method to include the new operator class. This can all be done in the same file
(`desdeo/emo/options/mutation.py`).

## Step 5: Test your implementation
After implementing the EA component, it is crucial to test it to ensure it works as expected. You can create unit tests that check the functionality of the `adaptive_mutation` method, the `AdaptiveMutation` class, and the Pydantic model.
Test whether the new component works as intended by itself and when integrated into an EA template.