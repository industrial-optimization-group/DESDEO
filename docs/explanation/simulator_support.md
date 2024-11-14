# Simulator and surrogate support in DESDEO

## Simulator file

A `simulator file` connects an external simulator to DESDEO.
It is a pyhton script that is called from the [Evaluator][desdeo.problem.simulator_evaluator]
with python's `subprocess.run` method. The evaluator passes to the simulator file decision
variable values and whatever parameters the simulator may take. These parameters could
be, for example, some variables the simulator needs that are not decision variables of the problem.

The simulator file takes two arguments:

- `-d`: a python dict of the decision variables as a list with each element representing a single sample, e.g.,

    ```python
    # decision variable values for three samples
    {
        "x_1": [1.5, 1.3, 1.4],
        "x_2": [-2.2, -2.0, -3.7],
        "x_3": [5.1, 10.7, 20.2]
    }
    ```

- `-p`: a python dict of the parameters, e.g.,

    ```python
    {
        "alpha": 10,
        "beta": -2
    }
    ```

The simulator file returns the objective, constraint and extra function values as a python dict
with the corresponding symbols as the keys of the dict and the corresponding values from the simulator
as a list, with each element representing a single sample, as the dict's values. For example,

```python
{
    "f_1": [1.5, 5.4, 10.2], # an objective
    "f_2": [-2.2, 0.1, -5.3], # an objective
    "g_2": [-0.1, -0.2, 0.0], # a constraint
    "e_4": [10, 5.1, 2.1] # an extra function
}
```

The evaluator is then responsible for gathering those values and at the end, making sure that every
objective, constraint and extra function is evaluated, whether they are analytical, simulator or
surrogate based.

### An example of a simulator file

In what follows, an example of a simulator file is shown. The "simulator" used in the example
is just a python function that takes the decision variables and parameters as arguments and
returns something based on them. If needed the input arguments can be manipulated into
a form the actual simulator can handle.

First we need to import the necessary modules:

```python
import argparse
import ast
import json
import sys
```

The modules `argparse` and sys are used to identify and read the argumenets passed to the simulator file.
The modules `ast` and `json` are used for parsing the arguments.

For this example, we define a simple python function that is acting as the simulator:

```python
import numpy as np

def simulator(xs: dict, params: dict):
    """The 'simulator' that is used to test connecting to an actual simulator with the arguments."""
    alpha: float = params.get("alpha", 1)
    beta: float = params.get("beta", 1)
    delta: float = params.get("delta", 1)
    fun1 = np.array(xs["x_1"]) * 2 + np.array(xs["x_2"]) * alpha
    fun2 = np.array(xs["x_2"]) * 2 + np.array(xs["x_1"]) * beta
    fun3 = np.array(xs["x_2"]) * delta
    return {"f_1": fun1.tolist(), "f_4": fun2.tolist(), "e_1": fun3.tolist()}
```

The "simulator" takes the decision variables (`xs`) and parameters (`params`) as
python dicts as arguments. It then does some computations with them and returns
the values for two objectives `f_1` and `f_4`, and one extra function value `e_1`.
The decision variable values are given as lists with each element representing
a single sample. This makes the returned values lists as well.

Now we need a script that parses the arguments passed from the evaluator into the correct form
and calls the evaluator. Finally, the script passes the output dict from the simulator back
to the evaluator via the `stdout` module. The evaluator then reads the stdout and the possible
errors from the simulator file. The script looks something like

```python
if __name__ == "__main__":
    # initialize the argument parser
    parser = argparse.ArgumentParser()

    # define help messages for when the arguments are missing
    vars_msg = "Variables for the simulator as a python dict. For example: {'x_1': [0, 1, 2, 3, 4], 'x_2': [4, 3, 2, 1, 0]}."
    params_msg = "Parameters for the simulator as a python dict. For example: {'alpha': 0.1, 'beta': 0.2}."

    # add the expected arguments
    parser.add_argument("-d", dest="vars", help=vars_msg)
    parser.add_argument("-p", dest="params", help=params_msg)

    # check that arguments are given, and if not, print out a message with information on the simulator file
    args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])

    # check that the expected arguments are given values, if not, print out a message with information on the missing argument
    if args.vars:
        # parse the argument from string form into a python dict using ast module's literal_eval method
        variables = ast.literal_eval(args.vars)
    else:
        parser.parse_args(["-h"])
    if args.params:
        # parse the argument from string form into a python dict using ast module's literal_eval method
        parameters = ast.literal_eval(args.params)
    else:
        parser.parse_args(["-h"])

    # call the simulator with the given variables and parameters
    simulator_output = simulator(variables, parameters)

    # send out the simulator outputs utilizing json.dumps method to keep the output as a dict to be parsed
    sys.stdout.write(json.dumps(simulator_output))
```

In the script, we first initialize the argument parser and the expected arguments.
Then we check that the arguments are given values and parse the values.
Then the simulator itself is called with the arguments and the output of the
simulator is gathered. Here the output of the simulator is in the correct form,
a python dict, but if it was not, we would need to make the dict before sending
it out. The output dict is then sent out via `sys.stdout.write` method and kept
in the correct form by using `json.dumps` here and then `json.loads` in the
evaluator end.
