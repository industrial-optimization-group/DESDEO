"""This module contains tools to generate and analyze explanations."""

__all__ = ["ShapExplainer", "generate_biased_mean_data"]

from .explainer import ShapExplainer
from .utils import generate_biased_mean_data
