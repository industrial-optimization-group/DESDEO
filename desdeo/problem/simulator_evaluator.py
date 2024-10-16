"""Evaluators are defined to evaluate simulator based and surrogate based objectives, constraints and extras."""

import json
import pickle
import subprocess
import sys
from inspect import getfullargspec
from pathlib import Path

import joblib
import numpy as np
import skops.io as sio

from desdeo.problem import (
    EvaluatorError,
    EvaluatorModesEnum,
    GenericEvaluator,
    ObjectiveTypeEnum,
    Problem,
)


class Evaluator:
    """A class for creating evaluators for simulator based and surrogate based objectives, constraints and extras."""
    def __init__(
        self,
        problem: Problem,
        params: dict[str, dict] | None = None,
        surrogate_paths: dict[str, Path] | None = None,
        #evaluator_mode: EvaluatorModesEnum | None = None # TODO: not needed when generic evaluate function works (maybe for init reasons?)
    ):
        """Creating an evaluator for simulator based and surrogate based objectives, constraints and extras.

        Args:
            problem (Problem): The problem as a pydantic 'Problem' data class.
            params (dict[str, dict], optional): Parameters for the different simulators used in the problem.
                Given as dict with the simulators' symbols and the corresponding simulator parameters as a dict.
                Defaults to None.
            surrogate_paths (dict[str, Path]): A dictionary where the keys are the names of the objectives, constraints
                and extra functions and the values are the paths to the surrogate models saved on disk. The names of
                the objectives, constraints and extra functions should match the names of the objectives,constraints and
                extra functions in the problem JSON.
        """
        self.problem = problem
        # Gather the problem's objectives
        self.problem_objectives = problem.objectives
        self.objective_symbols = [obj.symbol for obj in problem.objectives]
        # Gather objectives of different types into their own lists
        self.analytical_objectives = list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.analytical, problem.objectives))
        #self.data_based_objectives = list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.data_based, problem.objectives))
        self.simulator_objectives = list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.simulator, problem.objectives))
        self.surrogate_objectives = list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.surrogate, problem.objectives))
        # Gather any constraints
        self.analytical_constraints = []
        self.simulator_constraints = []
        self.surrogate_constraints = []
        self.constraint_symbols = []
        self.problem_constraints = problem.constraints
        if problem.constraints is not None:
            self.analytical_constraints = list(filter(lambda x: x.func is not None, problem.constraints))
            self.simulator_constraints = list(filter(lambda x: x.simulator_path is not None, problem.constraints))
            self.surrogate_constraints = list(filter(lambda x: x.surrogate is not None, problem.constraints))
            self.constraint_symbols = [con.symbol for con in problem.constraints]

        # Gather any extra functions
        self.analytical_extras = []
        self.simulator_extras = []
        self.surrogate_extras = []
        self.extra_symbols = []
        self.problem_extras = problem.extra_funcs
        if problem.extra_funcs is not None:
            self.analytical_extras = list(filter(lambda x: x.func is not None, problem.extra_funcs))
            self.simulator_extras = list(filter(lambda x: x.simulator_path is not None, problem.extra_funcs))
            self.surrogate_extras = list(filter(lambda x: x.surrogate is not None, problem.extra_funcs))
            self.extra_symbols = [extra.symbol for extra in problem.extra_funcs]

        # Gather all the symbols of objectives, constraints and extra functions
        self.problem_symbols = self.objective_symbols + self.constraint_symbols + self.extra_symbols

        # Gather the possible simulators
        self.simulators = problem.simulators
        # Gather the possibly given parameters
        if params is not None:
            self.params = params
        else:
            self.params = {}

        self.surrogates = {}
        if surrogate_paths is not None:
            self._load_surrogates(surrogate_paths)

    def _evaluate_simulator(self, xs: np.ndarray, return_as_dict: bool = True) -> np.ndarray:
        """Evaluate the problem for the given decision variables using the simulator.

        If there is a mix of (mutually exclusive and exhaustive) analytical and simulator objectives,
        constraints and extra functions, this method will use polars to evaluate the analytical objectives,
        constraints and extra functions and the simulator file to evaluate the simulator objectives,
        constraints and extra functions, and return the combined results.

        Args:
            xs (np.ndarray): The decision variables for which the objectives need to be evaluated.
                The shape of the array is (n, m), where n is the number of decision variables and m is the
                number of samples. Note that there is no need to support TensorVariables in this evaluator.
            return_as_dict (bool, optional): Determines in what form the objective, constraint and extra function
                values are returned. The options at the moment are 'dict' (a python dict) and 'ndarray' (numpy array).
                If returned as a dict, the dict will contain the objective, constraint and extra function symbols
                and their corresponding values. Defaults to 'True'.

        Returns:
            dict[str, np.ndarray]: The objective, constraint and extra function values for the given
                decision variables. Will return those objective, constraint and extra function values
                that are gained from simulators listed in the problem object.
                Returned as a dict with the objective, constraint and extra function symbols
                and the corresponding values as numpy arrays. The length of the arrays is the number of samples.
        """
        xs_json = json.dumps(xs.tolist())
        # TODO: add validation?
        results_dict = {}
        results = []
        sim_symbols = []
        for sim in self.simulators:
            for obj in self.simulator_objectives:
                if obj.simulator_path == sim.file:
                    sim_symbols.append(obj.symbol)

            if self.problem_constraints is not None:
                for con in self.problem_constraints:
                    if con.simulator_path == sim.file:
                        sim_symbols.append(con.symbol)

            if self.problem_extras is not None:
                for extra in self.problem_extras:
                    if extra.simulator_path == sim.file:
                        sim_symbols.append(extra.symbol)

            params = self.params.get(sim.name, {})
            res = subprocess.run(
                f"{sys.executable} {sim.file} -d {xs_json} -p {params}", check=True, capture_output=True
            ).stdout.decode()
            results.append(np.array(json.loads(''.join(res))))

        # here we are assuming that the simulator file gives outputs (objectives, constraints and extra_functions)
        # in the "correct" order
        results_stack = np.vstack(results)
        if not return_as_dict:
            return results_stack
        for i in range(len(sim_symbols)):
            results_dict[sim_symbols[i]] = results_stack[i]
        return results_dict

    def _evaluate_surrogates(
        self,
        xs: np.ndarray,
        return_as_dict: bool = True
    ) -> dict[str, tuple[np.ndarray, np.ndarray]] | tuple[np.ndarray, np.ndarray]:
        """Evaluate the problem for the given decision variables using the surrogate models.

        If there is a mix of (mutually exclusive and exhaustive) analytical and surrogate objectives, this method will
        use polars to evaluate the analytical objectives and the surrogate models to evaluate the surrogate objectives,
        and return the combined results.

        Args:
            xs (np.ndarray): The decision variables for which the objectives need to be evaluated.
                The shape of the array is (n, m), where n is the number of decision variables and m is the number
                of samples. Note that there is no need to support TensorVariables in this evaluator.
            return_as_dict (bool, optional): Determines in what form the objective, constraint and extra function
                values are returned. The options at the moment are 'dict' (a python dict) and 'ndarray' (numpy array).
                If returned as a dict, the dict will contain the objective, constraint and extra function symbols
                and their corresponding values. Defaults to 'True'.

        Returns:
            tuple[np.ndarray, np.ndarray]: The objective values for the given decision variables. The shape of
                the first array is (k, m), where k is the number of objectives and m is the number of samples.
                The second array is the uncertainity predictions for the objectives. The shape of the array is (k, m),
                where k is the number of objectives and m is the number of samples. For objectives that are not
                surrogates, the uncertainity predictions should be set to 0. For objectives that are surrogates,
                the uncertainity predictions should be the uncertainity predictions of the surrogate model
                (see, e.g., sklearn's predict method for gaussian process regressors with return_std=True).
                For objectives that are surrogates but do not have uncertainity predictions, the uncertainity
                predictions should be set to np.nan. Maybe a warning should be raised in such cases?
        """
        objective_values = []
        uncertainties = []
        symbols = []
        results_dict = {}
        for obj in self.surrogates:
            accepted_args = getfullargspec(self.surrogates[obj].predict).args
            if "return_std" in accepted_args:
                objective_value, uncertainty = self.surrogates[obj].predict(xs.T, return_std=True)
            else:
                objective_value = self.surrogates[obj].predict(xs.T)
                uncertainty = np.full(np.shape(objective_value), np.nan)
            objective_values.append(objective_value)
            uncertainties.append(uncertainty)
            symbols.append(obj)
        res_arrays = np.array(objective_values), np.array(uncertainties)
        objective_values_stack = np.vstack(res_arrays[0])
        uncertainties_stack = np.vstack(res_arrays[1])
        if not return_as_dict:
            return objective_values_stack, uncertainties_stack
        for i in range(len(symbols)):
            results_dict[symbols[i]] = objective_values_stack[i], uncertainties_stack[i]
        return results_dict

    def _load_surrogates(self, surrogate_paths: dict[str, Path]):
        """Load the surrogate models from disk and store them within the evaluator.

        This is used during initialization of the evaluator or when the analyst wants to replace the current surrogate
        models with other models. However if a new model is trained after initialization of the evaluator, the problem
        JSON should be updated with the new model paths and the evaluator should be re-initialized. This can happen
        with any solver that does model management.

        Args:
            surrogate_paths (dict[str, Path]): A dictionary where the keys are the names of the objectives and the
                values are the paths to the surrogate models saved on disk. The names of the objectives should match
                the names of the objectives in the problem JSON. This Evaluator class must support loading popular
                file formats. Check documentation of popular libraries like sklearn, pytorch, etc. for more information.
        """
        for symbol in surrogate_paths:
            with Path.open(f"{surrogate_paths[symbol]}", 'rb') as file:
                #self.surrogates[obj.symbol] = joblib.load(file)
                unknown_types = sio.get_untrusted_types(file=file)
                if len(unknown_types) == 0:
                    self.surrogates[symbol] = sio.load(file, unknown_types)
                else: # TODO: if there are unknown types they should be checked
                    self.surrogates[symbol] = sio.load(file, unknown_types)
                    #raise EvaluatorError(f"Untrusted types found in the model of {obj.symbol}: {unknown_types}")

    def evaluate(self, xs: dict, return_type: str = "dict") -> dict[str, int | float | np.ndarray] | np.ndarray:
        # possible return types are "dict" and "ndarray"
        if return_type not in ["dict", "ndarray"]:
            raise EvaluatorError(f"{return_type} is not a valid return type.")
        if return_type == "dict":
            res = {}
            if len(self.analytical_objectives + self.analytical_constraints + self.analytical_extras) > 0:
                polars_evaluator = GenericEvaluator(self.problem, evaluator_mode=EvaluatorModesEnum.mixed)
                analytical_values = polars_evaluator._polars_evaluate(xs["analytical"])
                for obj in self.analytical_objectives:
                    res[obj.symbol] = analytical_values[obj.symbol][0]
                for con in self.analytical_constraints:
                    res[con.symbol] = analytical_values[con.symbol][0]
                for extra in self.analytical_extras:
                    res[extra.symbol] = analytical_values[extra.symbol][0]

            """data_evaluator = GenericEvaluator(self.problem, evaluator_mode=EvaluatorModesEnum.mixed)
            data_values = data_evaluator._from_discrete_data()
            obj_values.append(data_values)"""
            #data_objs = self._from_discrete_data()

            if len(self.simulator_objectives + self.simulator_constraints + self.simulator_extras) > 0:
                simulator_values = self._evaluate_simulator(xs=xs["simulator"], return_as_dict=True)
                for obj in self.simulator_objectives:
                    res[obj.symbol] = simulator_values[obj.symbol].tolist()

                if len(self.simulator_constraints) > 0:
                    for con in self.simulator_constraints:
                        res[con.symbol] = simulator_values[con.symbol].tolist()

                if len(self.simulator_extras) > 0:
                    for extra in self.simulator_extras:
                        res[extra.symbol] = simulator_values[extra.symbol].tolist()

            if len(self.surrogate_objectives + self.surrogate_constraints + self.simulator_extras) > 0:
                surrogate_values = self._evaluate_surrogates(xs=xs["surrogate"])
                for obj in self.surrogate_objectives:
                    res[obj.symbol] = surrogate_values[obj.symbol][0].tolist(), surrogate_values[obj.symbol][1].tolist()
                if len(self.surrogate_constraints) > 0:
                    for con in self.surrogate_constraints:
                        res[con.symbol] = surrogate_values[con.symbol][0].tolist(), surrogate_values[con.symbol][1].tolist()

                if len(self.surrogate_extras) > 0:
                    for extra in self.surrogate_extras:
                        res[extra.symbol] = surrogate_values[extra.symbol][0].tolist(), surrogate_values[extra.symbol][1].tolist()

            #surrogate_objs = self._evaluate_surrogate(xs['surrogate'])
            for symbol in self.problem_symbols:
                if symbol not in res:
                    raise EvaluatorError(f"{symbol} not evaluated.")
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
    from desdeo.problem import simulator_problem, surrogate_problem

    evaluator = Evaluator(
        simulator_problem(),
        params={"s_1": {"alpha": 0.1, "beta": 0.2}, "s_2": {"epsilon": 10, "gamma": 20}},
        surrogate_paths={"f_5": Path("model.skops"),
                         "f_6": Path("model2.skops"),
                         "g_3": Path("model.skops"),
                         "e_3": Path("model2.skops")})
    res = evaluator.evaluate({
        "analytical": {"x_1": 1, "x_2": 2, "x_3": 3},
        "simulator": np.array([[0, 1, 2, 3, 4], [4, 3, 2, 1, 0], [0, 4, 1, 3, 2], [3, 1, 3, 2, 3]]),
        "surrogate": np.array([[0, 1, 2, 3, 4], [4, 3, 2, 1, 0], [0, 4, 1, 3, 2], [3, 1, 3, 2, 3]])})
    #res = evaluator._evaluate_simulator(np.array([[0, 1, 2, 3], [4, 3, 2, 1], [0, 4, 1, 3]]))
    #print(np.shape(res), res)
    print(res)
    """evaluator = Evaluator(surrogate_problem())
    evaluator._load_surrogates()
    obj_values, uncertainties = evaluator._evaluate_surrogates(np.array([[0, 1, 2, 3, 4], [4, 3, 2, 1, 0], [0, 4, 1, 3, 2], [3, 1, 3, 2, 3]]))
    print(np.shape(obj_values), np.shape(uncertainties)) # 4 dec vars and 3 samples
    print(obj_values)
    print(uncertainties)"""
