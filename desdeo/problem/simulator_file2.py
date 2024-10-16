import json
import sys

import numpy as np


def simulator(xs: dict, params: dict):
    epsilon: float = params.get("epsilon", 1)
    gamma: float = params.get("gamma", 1)
    fun1 = np.array(xs["x_1"]) * 2 - np.array(xs["x_2"]) - epsilon / 20
    fun2 = np.array(xs["x_2"]) * 2 - np.array(xs["x_1"]) + gamma / 100
    return {"f_3": fun1.tolist(), "g_1": fun2.tolist()}

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
        simulator_output = simulator(xs, parameters)
        #print(xs, parameters)
        #sys.stdout.write(xs)
        #print(json.dumps(simulator_output))
        sys.stdout.write(json.dumps(simulator_output))
