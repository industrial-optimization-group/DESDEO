"""Explainers are defined here."""

from collections.abc import Callable

import numpy as np
import polars as pl
import shap

from desdeo.problem import Problem


class BlackBoxError(Exception):
    """Raised when issued with the 'BlackBox' class are encountered."""


class BlackBox:
    """The 'BlackBox' class defines a model that should be explained.

    The black box is used as a wrapper to abstract the input to an interactive method,
    e.g., a reference point, and the method's output.
    """

    def __init__(
        self,
        problem: Problem,
        evaluator: Callable[[np.ndarray, ...], np.ndarray],
        evaluator_kwargs: dict | None = None,
    ):
        self.evaluator = evaluator
        self.evaluator_kwargs = evaluator_kwargs

    def evaluate(self, xs: np.ndarray) -> np.ndarray:
        """Evaluate the black box.

        Args:
            xs (np.ndarray):


        Returns:
            np.ndarray: returns a numpy array with the values returned by evaluating
                the black box
        """
        # needs to account for calling argument like
        # [0.60260447 0.4600719  0.906743  ]b
        # [0.54925335 0.92982054 0.32396162]
        # ...
        # [0.57616443 1.23657878 0.23357839]

        return np.apply_along_axis(
            lambda x: self.evaluator(x, **self.evaluator_kwargs)
            if self.evaluator_kwargs is not None
            else self.evaluator(x),
            axis=1,
            arr=np.atleast_2d(xs),
        )


class ShapExplainer:
    def __init__(self, bb: BlackBox, missing_data: np.ndarray):
        self.bb = bb
        self.missing_data = np.atleast_2d(missing_data)
        self.explainer = shap.explainers.KernelExplainer(self.bb.evaluate, self.missing_data)

    def shap_values(self, x: np.ndarray):
        return self.explainer(np.atleast_2d(x))
