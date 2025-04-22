"""A test simulator file for testing the simulator evaluator.

The simulator file is given two dicts as arguments:
    -d: a dict of the decision variables for the simulator
    -p: a dict of paramaters for the simulator.
The simulator file passes these arguments to the simulator and gets a dict as return.
"""

import argparse
import ast
import json
import sys

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    vars_msg = "Variables for the simulator as a python dict. For example: {'x_1': [0, 1, 2, 3, 4], 'x_2': [4, 3, 2, 1, 0]}."
    params_msg = "Parameters for the simulator as a python dict. For example: {'alpha': 0.1, 'beta': 0.2}."
    parser.add_argument("-d", dest="vars", help=vars_msg)
    parser.add_argument("-p", dest="params", help=params_msg)
    # check that the arguments are given values
    # TODO: maybe also check the types of the arguments at some point?
    args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])
    if args.vars:
        variables = ast.literal_eval(args.vars)
    else:
        parser.parse_args(["-h"])
    if args.params:
        parameters = ast.literal_eval(args.params)
    else:
        parser.parse_args(["-h"])

    simulator_output = simulator(variables, parameters)
    sys.stdout.write(json.dumps(simulator_output))
