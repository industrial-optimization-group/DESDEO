import json
import sys

import numpy as np


def simulator(xs: dict, params: dict):
    alpha = params.get("alpha", 1)
    beta = params.get("beta", 1)
    fun1 = np.array(xs["x_1"]) * 2 + np.array(xs["x_2"]) * alpha
    fun2 = np.array(xs["x_2"]) * 2 + np.array(xs["x_1"]) * beta
    fun3 = np.array(xs["x_2"])
    return np.array([fun1.tolist(), fun2.tolist(), fun3.tolist()])

if __name__ == "__main__":
    missing_arg = False
    args = sys.argv
    if '-d' in args:
        d_index = args.index('-d')
    else:
        missing_arg = True

    if '-p' in args:
        p_index = args.index('-p')
    else:
        missing_arg = True

    if missing_arg is True:
        print("Information")
    else:
        xs = args[d_index + 1: p_index]

        # parse the decision variable values
        xs = json.loads(''.join(xs).replace("\'", "\""))

        parameters = args[p_index + 1:]
        parameters = json.loads(''.join(parameters).replace("\'", "\""))
        #alpha = parameters["alpha"]
        #print(xs)
        simulator_output = simulator(xs, parameters).tolist()
        #print(xs, parameters)
        #sys.stdout.write(xs)
        #print(json.dumps(simulator_output))
        sys.stdout.write(json.dumps(simulator_output))
