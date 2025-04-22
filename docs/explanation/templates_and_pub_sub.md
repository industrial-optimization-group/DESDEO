# Evolutionary Algorithms in DESDEO

In this section, we will discuss how evolutionary algorithms (EAs) are implemented in DESDEO.
As discussed in the [tutorial on EAs](../tutorials/EMO.md), EAs are generally composed of modular components that can be reutilized in other EAs, or can be replaced with equivalent components.
An EA can be seen as a pipeline of components that process the population of solutions in each generation.
We first describe how DESDEO implements the components of an EA.
Then, we describe how DESDEO supports the creation of such pipelines, and point out a few shortcomings with the approach regarding the flow of information between components.
Finally, we discuss how the Publish-Subscribe pattern can be used to improve the flow of information between components.

## EA Components

In DESDEO, the components of an EA are implemented as classes with equivalent components sharing the same interface. As we will see later in Section [Publish-Subscribe Pattern](#Publish-Subscribe-Pattern), all components are implemented as subclasses to the Subscriber class. However, for now, we will describe the structure of a typical EA component in a more general way.

In general, an EA component has two main methods:

1. Component initializer: This method initializes the component with the necessary parameters. For example, the initializer of a crossover operator would take the probability of crossover as a parameter. The initializer should accept user provided hyperparameters and set the default values for the rest. The default `__init__` method of the class is used for this purpose. The function signature of the initializer of each component may be different (even for components of the same type).

2. Component execution: This method is called by the EA to execute the component. For example, the execution method of a crossover operator would take the current population and return a new population after applying the crossover operator. The function signature of each execution method must be the same for all components of the same type. However, the function signature may differ between components of different types. In general, the name of the execution method is also different for each component type, and can take an appropriate name that describes the function of the component.

In addition to these two methods, a component may have other methods that are specific to the component. However, these other methods are not expected to be called by the EA, and are used internally by the component. For clarity, these may be marked as private methods by prefixing the method name with an underscore.

## Templates

In DESDEO, the pipeline of an EA is created using templates. A template is simply a method that takes initialized components as arguments and runs their execution methods in a specific order. The order in which the components are executed is determined by the template itself. As each component of the same type is expected to have the same signature for the execution method, the template can call the execution method of each component without knowing the specifics of the component. For example, the template for a simple EA may look like this:

```python
def template(
    generator: BaseGenerator,
    terminator: BaseTerminator,
    crossover: BaseCrossover,
    mutation: BaseMutation,
    evaluator: EMOEvaluator,
    selection: BaseSelector,
) -> EMOResult:
    solutions, outputs = generator.do()

    while not terminator.check():
        offspring = crossover.do(population=solutions)
        offspring = mutation.do(offspring, solutions)
        offspring_outputs = evaluator.evaluate(offspring)
        solutions, outputs = selection.do(parents=(solutions, outputs), offsprings=(offspring, offspring_outputs))

    return EMOResult(solutions=solutions, outputs=outputs)
```

The template takes care of the general order in which the components are executed. Note that the template itself makes no assumptions about the exact nature of the components, or that of the problem. The same template can be used for continuous, discrete, or mixed-integer optimization problems, as long as the components are implemented correctly and they support the specific problem type.
The initialization of the components is done outside the template, and this step can be used to make sure that the components actually support the problem at hand.

The template also provides a basic pathway for the flow of information between components. In the example above, the outputs of the mutation operator are passed to the evaluator, and the outputs of the evaluator are passed to the selection operator. This is only possible because the components of the same type have the same signature for the execution method. However, this approach has a few shortcomings. In reality, different operators of the same kind may require different information. For example, there may be self-adaptive operators that take previous populations, or the expended budget of optimization as inputs. In general, it is not possible to predict the exact information that each operator may require. Changing the signature of the execution method of each component to accommodate all possible information is not a good idea, as it would make the components less modular, and the templates less reusable. In the next section, we discuss how the Publish-Subscribe pattern can be used to improve the flow of information between components.

## Publish-Subscribe Pattern

The [Publish-Suscribe pattern](https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern) is a messaging pattern where senders of messages (publishers) do not program the messages to be sent directly to specific receivers (subscribers). Instead, the publisher classifies the messages into classes without knowledge of which subscribers, if any, there may be. Similarly, subscribers express interest in one or more classes and only receive messages that are of interest, without knowledge of which publishers, if any, there are.

In the context of DESDEO, this means that each component can send messages to a central message broker, and subscribe to messages of interest. The message broker can then route the messages to the appropriate subscribers. This allows the components to be more modular, as they do not need to know the specifics of other components. The message broker can also be used to route messages to multiple subscribers, or to filter messages based on the content of the message. Essentially, the flow of information is decoupled from the templates, and the components can be more easily reused in different pipelines.

There are a few differences between the Publish-Subscribe pattern and the implementation in DESDEO. In DESDEO, the components are implemented as subclasses of the `Subscriber` class. Hence, even the components that are sending messages out are technically subscribers. There is a `Publisher` class as well. The `Publisher` class is the message broker mentioned in the previous paragraph. Each `Subscriber` can register itself to the `Publisher` and make sure that the `Publisher` knows which messages can be recieved from it. Furthermore, each `Subscriber` can also register topics that it is interested in. Once all components are registered, the `Publisher` can make sure that all topics that have been subscribed to are also being sent by one or more components. This way, the `Publisher` can make sure that all components are connected properly to each other.

To enable this pattern, each component must implement the `Subscriber` class. The `Subscriber` class enforces the impementation of the component to contain these four attributes/methods:

1. Attribute `provided_topics`: Is a dict that maps integers to a list of so called `MessageTopics`. The integer is the verbosity level for the component. A verbosity of zero forces the component to send no messages. A verbosity of one forces the component to send only information that are of type integer, float, bool, or string. A verbosity level of two additionally allows dictionaries, lists and polars dataframes. When an initialized component is registered to a Publisher, the `provided_topics` is used by the publisher to understand which topics the component can send messages about.

2. Attribute `interested_topics`: Is a list of `MessageTopics` that the component is interested in. When a component is registered to a Publisher, the `interested_topics` is used by the publisher to understand which topics the component is interested in.

3. Method `state`: This method is used to formulate the message that is sent by the component to the Publisher. The method should return a list of `Message` objects. The `Message` object is a simple Pydantic model that contains the message `topic`, the message `value`, as well as the message `source`, which is just the class name of the component (note, not the instance name). The `Subscriber` class provides a method named `notify`, which, when called, calls the `state` method and sends the messages to the Publisher. An appropriate time to call the `notify` method is at the end of the execution method of the component.

4. Method `update`: This method is used to receive messages from the Publisher. The method should accept a list of `Message` objects. Based on the content of the messages, the component can update its internal state.

Note that the template itself does not need to be modified to accommodate the Publish-Subscribe pattern. In fact, the template does not invoke the publisher at all. Sending messages to the publisher (and therefore, the publisher sending the messages to other components) is done by interrupting the control flow of the template. However, the users of DESDEO, or even the developers of DESDEO do not need to worry about this as most of the heavy lifting is done by the Publisher and the Subscriber base classes. As long as the components are implemented correctly, with the information provided as stated above, the Publish-Subscribe pattern should work seamlessly.

Note that another benefit of using the Publish-Subscribe pattern for the flow of information is that we are not limited to only using the components needed by the template. Additional components, such as archiving or visualization components can be registered to the publisher, and can receive messages from the other components. These components will work as expected even though the template itself does not invoke them. This allows for a more flexible and modular approach to implementing EAs in DESDEO.

Below we provide an example of how the Publish-Subscribe pattern can be used to implement a simple EA. The example is a simplified implementation of the RVEA algorithm, which is a decomposition-based EA. The example is not complete, and is only meant to illustrate how the Publish-Subscribe pattern can be used to implement EAs in DESDEO. The complete implementation of RVEA can be found in the `rvea` method. The RVEA algorithm's selection operator needs to know how many generations have passed or how many evaluations have been made. This information is not available to the selection operator in the template. However, the selection operator can subscribe to messages about the number of generations or evaluations, and update its internal state accordingly.

```python

# Create a Publisher object
publisher = Publisher()  

#  Initialize the components, make sure that the components are passed the publisher object
evaluator = EMOEvaluator(
    problem=problem,
    publisher=publisher,
    verbosity=2,
)

selector = RVEASelector(
    problem=problem,
    publisher=publisher,
    reference_vector_options=reference_vector_options,
    verbosity=2,
)

generator = LHSGenerator(
    problem=problem,
    evaluator=evaluator,
    publisher=publisher,
    verbosity=1,
)
crossover = SimulatedBinaryCrossover(
    problem=problem,
    publisher=publisher,
    verbosity=1,
)
mutation = BoundedPolynomialMutation(
    problem=problem,
    publisher=publisher,
    verbosity=1,
)

terminator = MaxGenerationsTerminator(n_generations, publisher=publisher)

components = [evaluator, generator, crossover, mutation, selector, terminator]

# Register the components to the publisher
[publisher.register_topics(x.provided_topics[x.verbosity], x.__class__.__name__) for x in components]

# Subscribe to the topics that the components are interested in
[publisher.auto_subscribe(x) for x in components]

# Check whether all messages that have been subscribed to are also being sent by one or more components. Must be true.
publisher.check_consistency()

template1(
    evaluator=evaluator,
    crossover=crossover,
    mutation=mutation,
    generator=generator,
    selection=selector,
    terminator=terminator,
)
```

The `Publisher` class provides methods to register components and subscribe to topics. The `Publisher` class also provides a method to check the consistency of the messages being sent and received. Finally, the `Publisher` class provides a method named `relationship_map` that can be used to visualize the relationships between components. The `relationship_map` method generates a graph of the relationships between components, and can be used to debug the flow of information between components. Note that in the example above, only components that are needed by the template are registered to the publisher. Additional components can be registered to the publisher at any time, and can receive messages from the other components.