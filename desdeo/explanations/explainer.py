"""Explainers are defined here."""

from typing import Callable

import polars as pl
import shap


class BlackBoxError(Exception):
    """Raised when issued with the 'BlackBox' class are encountered."""


class BlackBox:
    """The 'BlackBox' class defines a model that should be explained."""

    def __init__(
        self, evaluator: Callable[[pl.DataFrame | dict, ...], pl.DataFrame], evaluator_kwargs: dict | None = None
    ):
        self.evaluator = evaluator
        self.evaluator_kwargs = evaluator_kwargs

    def evaluate(self, xs: dict) -> pl.DataFrame:
        """Evaluate the black box.

        Args:
            xs (dict):


        Returns:
            pl.DataFrame: returns a Polars dataframe with the values returned by evaluating
                the black box
        """
        # needs to account for calling argument like
        # [0.60260447 0.4600719  0.906743  ]b
        # [0.54925335 0.92982054 0.32396162]
        # ...
        # [0.57616443 1.23657878 0.23357839]
        return self.evaluator(xs, **self.evaluator_kwargs) if self.evaluator_kwargs is not None else self.evaluator(xs)


class ShapExplainer:
    def __init__(self, bb: BlackBox, missing_data: pl.DataFrame):
        self.bb = bb
        self.missing_data = missing_data
        self.explainer = shap.explainers.Permutation(self.bb.evaluate, self.missing_data.to_numpy())

    def shap_values(self, x: dict):
        return self.explainer(x)
