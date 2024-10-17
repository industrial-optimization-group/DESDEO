"""Evaluators are defined to evaluate simulator based and surrogate based objectives, constraints and extras."""

import json
import subprocess
import sys
from inspect import getfullargspec
from pathlib import Path

import numpy as np
import polars as pl
import skops.io as sio

from desdeo.problem import (
    ObjectiveTypeEnum,
    PolarsEvaluator,
    PolarsEvaluatorModesEnum,
    Problem,
)


class EvaluatorError(Exception):
    """Error raised when exceptions are encountered in an Evaluator."""

class Evaluator:
    """A class for creating evaluators for simulator based and surrogate based objectives, constraints and extras."""
    def __init__(
        self,
        problem: Problem,
        params: dict[str, dict] | None = None,
        surrogate_paths: dict[str, Path] | None = None
    ):
        """Creating an evaluator for simulator based and surrogate based objectives, constraints and extras.

        Args:
            problem (Problem): The problem as a pydantic 'Problem' data class.
            params (dict[str, dict], optional): Parameters for the different simulators used in the problem.
                Given as dict with the simulators' symbols as keys and the corresponding simulator parameters
                as a dict as values. Defaults to None.
            surrogate_paths (dict[str, Path]): A dictionary where the keys are the names of the objectives, constraints
                and extra functions and the values are the paths to the surrogate models saved on disk. The names of
                the objectives, constraints and extra functions should match the names of the objectives, constraints and
                extra functions in the problem JSON. Defaults to None.
        """
        self.problem = problem
        # Gather the problem's objectives
        self.problem_objectives = problem.objectives
        # store the symbol and min or max multiplier as well (symbol, min/max multiplier [1 | -1])
        self.objective_mix_max_mult = [
            (objective.symbol, -1 if objective.maximize else 1)
            for objective in self.problem_objectives
        ]
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

    def _evaluate_simulator(self, xs: dict[str, list[int | float]]) -> pl.DataFrame:
        """Evaluate the problem for the given decision variables using the problem's simulators.

        Args:
            xs (dict[str, list[int | float]]): The decision variables for which the functions are to be evaluated.
                Given as a dictionary with the decision variable symbols as keys and a list of decision variable values
                as the values. The length of the lists is the number of samples and each list should have the same
                length (same number of samples).

        Returns:
            pl.DataFrame: The objective, constraint and extra function values for the given decision variables as
                a polars dataframe. The symbols of the objectives, constraints and extra functions are the column names
                and the length of the columns is the number of samples. Will return those objective, constraint and
                extra function values that are gained from simulators listed in the problem object.
        """
        results = {}
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
                f"{sys.executable} {sim.file} -d {xs} -p {params}", check=True, capture_output=True
            ).stdout.decode()
            res = dict(json.loads(''.join(res)))
            for key, value in res.items():
                results[key] = value
        res = pl.DataFrame(results)

        # Evaluate the minimization form of the objective functions
        min_obj_columns = pl.DataFrame()
        for symbol, min_max_mult in self.objective_mix_max_mult:
            if symbol in res.columns:
                min_obj_columns = min_obj_columns.hstack(
                    res.select((min_max_mult * pl.col(f"{symbol}")).alias(f"{symbol}_min"))
                )
        return res.hstack(min_obj_columns)

    def _evaluate_surrogates(self, xs: dict[str, list[int | float]]) -> pl.DataFrame:
        """Evaluate the problem for the given decision variables using the surrogate models.

        Args:
            xs (dict[str, list[int | float]]): The decision variables for which the functions are to be evaluated.
                Given as a dictionary with the decision variable symbols as keys and a list of decision variable values
                as the values. The length of the lists is the number of samples and each list should have the same
                length (same number of samples).

        Returns:
            pl.DataFrame: The values of the evaluated objectives, constraints and extra functions as a polars
                dataframe. The uncertainty prediction values are also returned. If a model does not provide
                uncertainty predictions, then they are set as NaN.
        """
        results_dict = {}
        var = np.array([value for _, value in xs.items()]).T # has to be transpose (m, n) at least for sklearn models
        for symbol in self.surrogates:
            # get a list of args accepted by the model's predict function
            accepted_args = getfullargspec(self.surrogates[symbol].predict).args
            # if "return_std" accepted, gather the uncertainty predictions as well
            if "return_std" in accepted_args:
                value, uncertainty = self.surrogates[symbol].predict(var, return_std=True)
            # otherwise, set the uncertainties as NaN
            else:
                value = self.surrogates[symbol].predict(var)
                uncertainty = np.full(np.shape(value), np.nan)
            # add the objects, constraints and extra functions into a dict that is then turned into a polars dataframe
            # values go into columns with the symbol as the column names
            results_dict[symbol] = value
            # uncertainties go into columns with {symbol}_uncert as the column names
            results_dict[f"{symbol}_uncert"] = uncertainty

        res = pl.DataFrame(results_dict)
        # Evaluate the minimization form of the objective functions
        min_obj_columns = pl.DataFrame()
        for symbol, min_max_mult in self.objective_mix_max_mult:
            if symbol in res.columns:
                min_obj_columns = min_obj_columns.hstack(
                    res.select((min_max_mult * pl.col(f"{symbol}")).alias(f"{symbol}_min"))
                )
        return res.hstack(min_obj_columns)

    def _load_surrogates(self, surrogate_paths: dict[str, Path]):
        """Load the surrogate models from disk and store them within the evaluator.

        This is used during initialization of the evaluator or when the analyst wants to replace the current surrogate
        models with other models. However if a new model is trained after initialization of the evaluator, the problem
        JSON should be updated with the new model paths and the evaluator should be re-initialized. This can happen
        with any solver that does model management.

        Args:
            surrogate_paths (dict[str, Path]): A dictionary where the keys are the names of the objectives, constraints
                and extra functions and the values are the paths to the surrogate models saved on disk. The names of
                the objectives should match the names of the objectives in the problem JSON. At the moment the supported
                file format is .skops (through skops.io). TODO: if skops.io used, should be added to pyproject.toml.
        """
        for symbol in surrogate_paths:
            with Path.open(f"{surrogate_paths[symbol]}", 'rb') as file:
                unknown_types = sio.get_untrusted_types(file=file)
                if len(unknown_types) == 0:
                    self.surrogates[symbol] = sio.load(file, unknown_types)
                else: # TODO: if there are unknown types they should be checked
                    self.surrogates[symbol] = sio.load(file, unknown_types)
                    #raise EvaluatorError(f"Untrusted types found in the model of {obj.symbol}: {unknown_types}")

    def evaluate(self, xs: dict[str, list[int | float]]) -> pl.DataFrame:
        """Evaluate the functions for the given decision variables.

        Evaluates analytical, simulation based and surrogate based functions. For now, the evaluator assumes that there
        are no data based objectives.

        Args:
            xs (dict[str, list[int | float]]): The decision variables for which the functions are to be evaluated.
                Given as a dictionary with the decision variable symbols as keys and a list of decision variable values
                as the values. The length of the lists is the number of samples and each list should have the same
                length (same number of samples).

        Returns:
            pl.DataFrame: polars dataframe with the evaluated function values.
        """
        res = pl.DataFrame()

        # Evaluate the analytical functions
        if len(self.analytical_objectives + self.analytical_constraints + self.analytical_extras) > 0:
            polars_evaluator = PolarsEvaluator(self.problem, evaluator_mode=PolarsEvaluatorModesEnum.mixed)
            analytical_values = polars_evaluator._polars_evaluate(xs)
            res = res.hstack(analytical_values)

        """data_evaluator = GenericEvaluator(self.problem, evaluator_mode=EvaluatorModesEnum.mixed)
        data_values = data_evaluator._from_discrete_data()
        obj_values.append(data_values)"""
        #data_objs = self._from_discrete_data()

        # Evaluate the simulator based functions
        if len(self.simulator_objectives + self.simulator_constraints + self.simulator_extras) > 0:
            simulator_values = self._evaluate_simulator(xs)
            res = res.hstack(simulator_values)

        # Evaluate the surrogate based functions
        if len(self.surrogate_objectives + self.surrogate_constraints + self.simulator_extras) > 0:
            surrogate_values = self._evaluate_surrogates(xs)
            res = res.hstack(surrogate_values)

        # Check that everything is evaluated
        for symbol in self.problem_symbols:
            if symbol not in res.columns:
                raise EvaluatorError(f"{symbol} not evaluated.")
        return res

if __name__ == "__main__":
    from desdeo.problem import simulator_problem, surrogate_problem

    evaluator = Evaluator(
        simulator_problem(),
        params={"s_1": {"alpha": 0.1, "beta": 0.2}, "s_2": {"epsilon": 10, "gamma": 20}},
        surrogate_paths={"f_5": Path("model.skops"),
                         "f_6": Path("model2.skops"),
                         "g_3": Path("model.skops"),
                         "e_3": Path("model2.skops")})
    """res = evaluator.evaluate({
        "analytical": {"x_1": [0, 1, 2, 3, 4], "x_2": [4, 3, 2, 1, 0], "x_3": [0, 4, 1, 3, 2]},
        "simulator": np.array([[0, 1, 2, 3, 4], [4, 3, 2, 1, 0], [0, 4, 1, 3, 2], [3, 1, 3, 2, 3]]),
        "surrogate": np.array([[0, 1, 2, 3, 4], [4, 3, 2, 1, 0], [0, 4, 1, 3, 2], [3, 1, 3, 2, 3]])})"""
    res = evaluator.evaluate({
        "x_1": [0, 1, 2, 3, 4],
        "x_2": [4, 3, 2, 1, 0],
        "x_3": [0, 4, 1, 3, 2],
        "x_4": [3, 1, 3, 2, 3]})
    #res = evaluator._evaluate_simulator(np.array([[0, 1, 2, 3], [4, 3, 2, 1], [0, 4, 1, 3]]))
    #print(np.shape(res), res)
    with pl.Config(tbl_cols=-1):
        print(res)
