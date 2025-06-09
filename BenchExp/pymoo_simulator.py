import argparse
import ast
import json
import os
import sys

import numpy as np
from pymoo.problems import get_problem


def simulator_pymoo(variables: dict, parameters: dict) -> dict:
    # get the problem object from pymoo with its name
    pymoo_problem = get_problem(parameters["name"], n_var=parameters["n_vars"], n_obj=parameters["n_objs"])

    # get the variable lists
    vart = [variables[f"x_{i+1}"] for i in range(pymoo_problem.n_var)]

    # stack the variables correctly for pymoo
    vars = np.stack(vart, axis=1)

    # evaluate the population via pymoo
    F = pymoo_problem.evaluate(vars)

    # convert the array to dictionary
    obj = dict([(f"f_{i+1}", F[:, i].tolist()) for i in range(pymoo_problem.n_obj)])

    return obj


if __name__ == "__main__":
    # initialize the argument parser
    parser = argparse.ArgumentParser()

    # define help messages for when the arguments are missing
    vars_msg = (
        "Variables for the simulator as a python dict. For example: {'x_1': [0, 1, 2, 3, 4], 'x_2': [4, 3, 2, 1, 0]}."
    )
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

    stdout = sys.stdout
    sys.stdout = open(os.devnull, "w")

    # call the simulator with the given variables and parameters
    simulator_output = simulator_pymoo(variables, parameters)

    # send out the simulator outputs utilizing json.dumps method to keep the output as a dict to be parsed
    sys.stdout = stdout
    sys.stdout.write(json.dumps(simulator_output))
