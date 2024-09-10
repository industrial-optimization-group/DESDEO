import numpy as np

import sys

def simulator(xs: np.ndarray, params: dict):
    return [xs[0] * 2 + xs[1], xs[1] * 2 + xs[0]]

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
        xs = args[args.index('-d') + 1: p_index]

        # parse the decision variable values
        for i in range(len(xs)):
            xs[i] = float(xs[i].replace('[', '').replace(']', ''))

        objective_values = []
        parameters = args[args.index('-p') + 1]
        #print(xs)
        simulator_output = simulator(xs, parameters)
        #print(simulator_output)
        #print(xs, parameters)
        #sys.stdout.write(xs)
        sys.stdout.write(str(simulator_output))
