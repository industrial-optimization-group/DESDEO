from matplotlib.image import resample
from numpy._core.multiarray import scalar
"""Evaluators are defined to evaluate simulator based and surrogate based objectives, constraints and extras."""

import json
import subprocess
import sys
from inspect import getfullargspec
from pathlib import Path

import joblib
import numpy as np
import polars as pl
# import skops.io as sio
import requests

from desdeo.problem import (
    ObjectiveTypeEnum,
    PolarsEvaluator,
    PolarsEvaluatorModesEnum,
    Problem,
    MathParser
)


class EvaluatorError(Exception):
    """Error raised when exceptions are encountered in an Evaluator."""


class Evaluator:
    """A class for creating evaluators for simulator based and surrogate based objectives, constraints and extras."""

    def __init__(
        self, problem: Problem, params: dict[str, dict] | None = None, surrogate_paths: dict[str, Path] | None = None
    ):
        """Creating an evaluator for simulator based and surrogate based objectives, constraints and extras.

        Args:
            problem (Problem): The problem as a pydantic 'Problem' data class.
            params (dict[str, dict], optional): Parameters for the different simulators used in the problem.
                Given as dict with the simulators' symbols as keys and the corresponding simulator parameters
                as a dict as values. Defaults to None.
            surrogate_paths (dict[str, Path], optional): A dictionary where the keys are the names of the objectives,
                constraints and extra functions and the values are the paths to the surrogate models saved on disk.
                The names of the objectives, constraints and extra functions should match the names of the objectives,
                constraints and extra functions in the problem JSON. Defaults to None.
        """
        self.problem = problem
        # store the symbol and min or max multiplier as well (symbol, min/max multiplier [1 | -1])
        self.objective_mix_max_mult = [
            (objective.symbol, -1 if objective.maximize else 1) for objective in problem.objectives
        ]
        # Gather symbols objectives of different types into their own lists
        self.analytical_symbols = [
            obj.symbol
            for obj in list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.analytical, problem.objectives))
        ]
        self.data_based_symbols = [
            obj.symbol for obj in problem.objectives if obj.objective_type == ObjectiveTypeEnum.data_based
        ]
        self.simulator_symbols = [
            obj.symbol
            for obj in list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.simulator, problem.objectives))
        ]
        self.surrogate_symbols = [
            obj.symbol
            for obj in list(filter(lambda x: x.objective_type == ObjectiveTypeEnum.surrogate, problem.objectives))
        ]
        if problem.scalarization_funcs is not None:
            parser = MathParser()
            self.scalarization_funcs = [
                (func.symbol, parser.parse(func.func)) for func in problem.scalarization_funcs if func.symbol is not None
            ]
        else:
            self.scalarization_funcs = []
        # Gather any constraints' symbols
        if problem.constraints is not None:
            self.analytical_symbols = self.analytical_symbols + [
                con.symbol for con in list(filter(lambda x: x.func is not None, problem.constraints))
            ]
            self.simulator_symbols = self.simulator_symbols + [
                con.symbol for con in list(filter(lambda x: x.simulator_path is not None, problem.constraints))
            ]
            self.surrogate_symbols = self.surrogate_symbols + [
                con.symbol for con in list(filter(lambda x: x.surrogates is not None, problem.constraints))
            ]

        # Gather any extra functions' symbols
        if problem.extra_funcs is not None:
            self.analytical_symbols = self.analytical_symbols + [
                extra.symbol for extra in list(filter(lambda x: x.func is not None, problem.extra_funcs))
            ]
            self.simulator_symbols = self.simulator_symbols + [
                extra.symbol for extra in list(filter(lambda x: x.simulator_path is not None, problem.extra_funcs))
            ]
            self.surrogate_symbols = self.surrogate_symbols + [
                extra.symbol for extra in list(filter(lambda x: x.surrogates is not None, problem.extra_funcs))
            ]

        # Gather all the symbols of objectives, constraints and extra functions
        self.problem_symbols = (
            self.analytical_symbols + self.data_based_symbols + self.simulator_symbols + self.surrogate_symbols
        )

        # Gather the possible simulators
        self.simulators = problem.simulators if problem.simulators is not None else []
        # Gather the possibly given parameters
        self.params = {}
        for sim in self.simulators:
            sim_params = params.get(sim.name, {}) if params is not None else {}
            if sim.parameter_options is not None:
                for key in sim.parameter_options:
                    sim_params[key] = sim.parameter_options[key]
            self.params[sim.name] = sim_params

        self.surrogates = {}
        if surrogate_paths is not None:
            self._load_surrogates(surrogate_paths)
        else:
            self._load_surrogates()

        if len(self.surrogate_symbols) > 0:
            missing_surrogates = []
            for symbol in self.surrogate_symbols:
                if symbol not in self.surrogates:
                    missing_surrogates.append(symbol)

            if len(missing_surrogates) > 0:
                raise EvaluatorError(f"Some surrogates missing: {missing_surrogates}.")

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
        res_df = pl.DataFrame()
        for sim in self.simulators:
            # gather the possible parameters for the simulator
            params = self.params.get(sim.name, {})
            if sim.file is not None:
                # call the simulator with the decision variable values and parameters as dicts
                res = subprocess.run(
                    [sys.executable, sim.file, "-d", str(xs), "-p", str(params)], capture_output=True, text=True
                )
                if res.returncode == 0:
                    # gather the simulation results (a dict) into the results dataframe
                    res_df = res_df.hstack(pl.DataFrame(json.loads(res.stdout)))
                else:
                    raise EvaluatorError(res.stderr)
            elif sim.url is not None:
                # call the endpoint
                try:
                    if isinstance(xs, pl.DataFrame):
                        # if xs is a polars dataframe, convert it to a dict
                        xs = xs.to_dict(as_series=False)
                    res = requests.get(sim.url.url, auth=sim.url.auth, json={"d": xs, "p": params})
                    res.raise_for_status()  # raise an error if the request failed
                except requests.RequestException as e:
                    raise EvaluatorError(
                        f"Failed to call the simulator at {sim.url}. Is the simulator server running?"
                        ) from e
                res_df = res_df.hstack(pl.DataFrame(res.json()))


        # Evaluate the minimization form of the objective functions
        min_obj_columns = pl.DataFrame()
        for symbol, min_max_mult in self.objective_mix_max_mult:
            if symbol in res_df.columns:
                min_obj_columns = min_obj_columns.hstack(
                    res_df.select((min_max_mult * pl.col(f"{symbol}")).alias(f"{symbol}_min"))
                )

        res_df = res_df.hstack(min_obj_columns)
        # If there are scalarization functions, evaluate them as well
        scalarization_columns = res_df.select(*[expr.alias(symbol) for symbol, expr in self.scalarization_funcs])
        return res_df.hstack(scalarization_columns)

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
        res = pl.DataFrame()
        var = np.array([value for _, value in xs.items()]).T  # has to be transpose (at least for sklearn models)
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
            # add the objects, constraints and extra functions into the polars dataframe
            # values go into columns with the symbol as the column names
            res = res.with_columns(pl.Series(value).alias(symbol))
            # uncertainties go into columns with {symbol}_uncert as the column names
            res = res.with_columns(pl.Series(uncertainty).alias(f"{symbol}_uncert"))

        # Evaluate the minimization form of the objective functions
        min_obj_columns = pl.DataFrame()
        for symbol, min_max_mult in self.objective_mix_max_mult:
            if symbol in res.columns:
                min_obj_columns = min_obj_columns.hstack(
                    res.select((min_max_mult * pl.col(f"{symbol}")).alias(f"{symbol}_min"))
                )
        res_df = res_df.hstack(min_obj_columns)
        # If there are scalarization functions, evaluate them as well
        scalarization_columns = res_df.select(*[expr.alias(symbol) for symbol, expr in self.scalarization_funcs])
        return res_df.hstack(scalarization_columns)

    def _load_surrogates(self, surrogate_paths: dict[str, Path] | None = None):
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
        if surrogate_paths is not None:
            for symbol in surrogate_paths:
                with Path.open(f"{surrogate_paths[symbol]}", "rb") as file:
                    self.surrogates[symbol] = joblib.load(file)
                    """unknown_types = sio.get_untrusted_types(file=file)
                    if len(unknown_types) == 0:
                        self.surrogates[symbol] = sio.load(file, unknown_types)
                    else: # TODO: if there are unknown types they should be checked
                        self.surrogates[symbol] = sio.load(file, unknown_types)
                        #raise EvaluatorError(f"Untrusted types found in the model of {obj.symbol}: {unknown_types}")"""
        else:
            # check each surrogate based objective, constraint and extra function for surrogate path
            for obj in self.problem.objectives:
                if obj.surrogates is not None:
                    with Path.open(f"{obj.surrogates[0]}", "rb") as file:
                        self.surrogates[obj.symbol] = joblib.load(file)
                        """unknown_types = sio.get_untrusted_types(file=file)
                        if len(unknown_types) == 0:
                            self.surrogates[obj.symbol] = sio.load(file, unknown_types)
                        else: # TODO: if there are unknown types they should be checked
                            self.surrogates[obj.symbol] = sio.load(file, unknown_types)
                            #raise EvaluatorError(f"Untrusted types found in the model of {obj.symbol}: {unknown_types}")"""
            for con in self.problem.constraints or []:  # if there are no constraints, an empty list is used
                if con.surrogates is not None:
                    with Path.open(f"{con.surrogates[0]}", "rb") as file:
                        self.surrogates[con.symbol] = joblib.load(file)
                        """unknown_types = sio.get_untrusted_types(file=file)
                        if len(unknown_types) == 0:
                            self.surrogates[con.symbol] = sio.load(file, unknown_types)
                        else: # TODO: if there are unknown types they should be checked
                            self.surrogates[con.symbol] = sio.load(file, unknown_types)
                            #raise EvaluatorError(f"Untrusted types found in the model of {obj.symbol}: {unknown_types}")"""
            for extra in self.problem.extra_funcs or []:  # if there are no extra functions, an empty list is used
                if extra.surrogates is not None:
                    with Path.open(f"{extra.surrogates[0]}", "rb") as file:
                        self.surrogates[extra.symbol] = joblib.load(file)
                        """unknown_types = sio.get_untrusted_types(file=file)
                        if len(unknown_types) == 0:
                            self.surrogates[extra.symbol] = sio.load(file, unknown_types)
                        else: # TODO: if there are unknown types they should be checked
                            self.surrogates[extra.symbol] = sio.load(file, unknown_types)
                            #raise EvaluatorError(f"Untrusted types found in the model of {obj.symbol}: {unknown_types}")"""

    def evaluate(self, xs: dict[str, list[int | float]], flat: bool = False) -> pl.DataFrame:
        """Evaluate the functions for the given decision variables.

        Evaluates analytical, simulation based and surrogate based functions. For now, the evaluator assumes that there
        are no data based objectives.

        Args:
            xs (dict[str, list[int | float]]): The decision variables for which the functions are to be evaluated.
                Given as a dictionary with the decision variable symbols as keys and a list of decision variable values
                as the values. The length of the lists is the number of samples and each list should have the same
                length (same number of samples).
            flat (bool, optional): whether the valuation is done using flattened variables or not. Defaults to False.

        Returns:
            pl.DataFrame: polars dataframe with the evaluated function values.
        """
        # TODO (@gialmisi): Make work with polars dataframes as well in addition to dict.
        # See, e.g., PolarsEvaluator._polars_evaluate. Then, remove the arg `flat`.
        res = pl.DataFrame()

        # Evaluate the analytical functions
        if len(self.analytical_symbols + self.data_based_symbols) > 0:
            polars_evaluator = PolarsEvaluator(self.problem, evaluator_mode=PolarsEvaluatorModesEnum.mixed)
            analytical_values = (
                polars_evaluator._polars_evaluate(xs) if not flat else polars_evaluator._polars_evaluate_flat(xs)
            )
            res = res.hstack(analytical_values)

        # Evaluate the simulator based functions
        if len(self.simulator_symbols) > 0:
            simulator_values = self._evaluate_simulator(xs)
            res = res.hstack(simulator_values)

        # Evaluate the surrogate based functions
        if len(self.surrogate_symbols) > 0:
            surrogate_values = self._evaluate_surrogates(xs)
            res = res.hstack(surrogate_values)

        # Check that everything is evaluated
        for symbol in self.problem_symbols:
            if symbol not in res.columns:
                raise EvaluatorError(f"{symbol} not evaluated.")
        return res
