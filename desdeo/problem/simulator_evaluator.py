
import json
import subprocess
import sys

import numpy as np

from desdeo.problem import (
    EvaluatorError,
    EvaluatorModesEnum,
    GenericEvaluator,
    ObjectiveTypeEnum,
    Problem,
)


class Evaluator:
    def __init__(
        self,
        problem: Problem,
        params: dict[str, dict] | None = None, # this could possibly be better for the evaluate functions?
        #evaluator_mode: EvaluatorModesEnum | None = None # TODO: not needed when generic evaluate function works (maybe for init reasons?)
    ):
        self.problem = problem
        """if evaluator_mode not in EvaluatorModesEnum:
            msg = (
                f"The provided 'evaluator_mode' '{evaluator_mode}' is not supported."
                f" Must be one of {EvaluatorModesEnum}."
            )
            raise EvaluatorError(msg)

        self.evaluator_mode = evaluator_mode"""
        self.problem_objectives = problem.objectives
        self.analytical_objectives = list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.analytical, problem.objectives))
        self.data_based_objectives = list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.data_based, problem.objectives))
        self.simulator_objectives = list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.simulator, problem.objectives))
        self.surrogate_objectives = list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.surrogate, problem.objectives))
        # Gather any constraints
        self.problem_constraints = problem.constraints
        # Gather any extra functions
        self.problem_extra = problem.extra_funcs

        # Gather the possible simulators
        self.simulators = problem.simulators
        self.params = params
        if self.params is not None:
            sim_symbol_list = [s.symbol for s in self.simulators]
            for symbol in self.params:
                if symbol not in sim_symbol_list:
                    raise EvaluatorError(f"{symbol} not listed in the problem's simulators.")
        else:
            self.params = {}

        """if self.evaluator_mode == EvaluatorModesEnum.simulator:
            # Gather the possible simulators
            self.simulators = problem.simulators
            if self.simulators is None:
                raise EvaluatorError("No simulators defined for the problem.")
            self.params = params
            if self.params is not None:
                for name in self.params:
                    if name not in self.simulators:
                        raise EvaluatorError(f"{name} not listed in the problem's simulators.")
            else:
                self.params = {}
            self.evaluate = self._evaluate_simulator"""

    def _evaluate_simulator(self, xs: np.ndarray) -> np.ndarray:
        """Evaluate the objectives for the given decision variables using the simulator.

        If there is a mix of (mutually exclusive and exhaustive) analytical and simulator objectives, this method will
        use polars to evaluate the analytical objectives and the simulator file to evaluate the simulator objectives,
        and return the combined results.

        Args:
            xs (np.ndarray): The decision variables for which the objectives need to be evaluated.
                The shape of the array is (n, m), where n is the number of decision variables and m is the
                number of samples. Note that there is no need to support TensorVariables in this evaluator.

        Returns:
            np.ndarray: The objective values for the given decision variables.
                The shape of the array is (k, m), where k is the number of objectives and m is the number of samples.
        """
        xs_json = json.dumps(xs.tolist())
        # TODO: add validation?
        results_dict = {}

        for sim in self.simulators:
            sim_symbols = []
            results = []
            for obj in self.simulator_objectives:
                if obj.simulator_path == sim.file:
                    sim_symbols.append(obj.symbol)

            if self.problem_constraints is not None:
                for con in self.problem_constraints:
                    if con.simulator_path == sim.file:
                        sim_symbols.append(con.symbol)

            if self.problem_extra is not None:
                for extra in self.problem_extra:
                    if extra.simulator_path == sim.file:
                        sim_symbols.append(extra.symbol)

            params = self.params.get(sim.name, None)
            res = subprocess.run(
                f"{sys.executable} {sim.file} -d {xs_json} -p {params}", check=True, capture_output=True
            ).stdout.decode()
            results.append(np.array(json.loads(''.join(res))))

            # here we are assuming that the simulator file gives outputs (objectives, constraints and extra_functions)
            # in the "correct" order
            for i in range(len(sim_symbols)):
                results_dict[sim_symbols[i]] = np.vstack(results)[i]
        return results_dict

    def evaluate(self, xs: dict, return_type: str = "dict") -> dict[str, int | float | np.ndarray] | np.ndarray:
        # possible return types are "dict" and "ndarray"
        if return_type not in ["dict", "ndarray"]:
            raise EvaluatorError(f"{return_type} is not a valid return type.")
        if return_type == "dict":
            res = {}
            """polars_evaluator = GenericEvaluator(self.problem)
            analytical_values = polars_evaluator._polars_evaluate(xs)
            obj_values.append(analytical_values)"""
            #analytical_objs = self._polars_evaluate(xs['analytical'])
            """data_evaluator = GenericEvaluator(self.problem, evaluator_mode=EvaluatorModesEnum.discrete)
            data_values = data_evaluator._from_discrete_data()
            obj_values.append(data_values)"""
            #data_objs = self._from_discrete_data()

            simulator_values = self._evaluate_simulator(xs["simulator"])
            for obj in self.simulator_objectives:
                res[obj.symbol] = simulator_values[obj.symbol].tolist()

            if self.problem_constraints is not None:
                for con in self.problem_constraints:
                    if con.symbol in simulator_values:
                        res[con.symbol] = simulator_values[con.symbol]

            if self.problem_extra is not None:
                for extra in self.problem_extra:
                    if extra.symbol in simulator_values:
                        res[extra.symbol] = simulator_values[extra.symbol]
            #surrogate_objs = self._evaluate_surrogate(xs['surrogate'])
            return res

        obj_values = []
        """polars_evaluator = GenericEvaluator(self.problem)
        analytical_values = polars_evaluator._polars_evaluate(xs)
        obj_values.append(analytical_values)"""
        #analytical_objs = self._polars_evaluate(xs['analytical'])
        """data_evaluator = GenericEvaluator(self.problem, evaluator_mode=EvaluatorModesEnum.discrete)
        data_values = data_evaluator._from_discrete_data()
        obj_values.append(data_values)"""
        #data_objs = self._from_discrete_data()
        simulator_objs = self._evaluate_simulator(xs["simulator"])
        if len(simulator_objs) != len(self.simulator_objectives):
            raise EvaluatorError("Some simulator(s) not found.")
        for obj in simulator_objs:
            obj_values.append(obj)
        #surrogate_objs = self._evaluate_surrogate(xs['surrogate'])
        return obj_values

if __name__ == "__main__":
    from desdeo.problem import simulator_problem

    evaluator = Evaluator(
        simulator_problem(),
        params={"s_1": {"alpha": 0.1, "beta": 0.2}, "s_2": {"epsilon": 10, "gamma": 20}})
    res = evaluator.evaluate({"simulator": np.array([[0, 1, 2, 3], [4, 3, 2, 1], [0, 4, 1, 3]])}, return_type="dict")
    #res = evaluator._evaluate_simulator(np.array([[0, 1, 2, 3], [4, 3, 2, 1], [0, 4, 1, 3]]))
    #print(np.shape(res), res)
    print(res)
