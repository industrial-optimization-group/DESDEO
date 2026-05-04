"""Learning-mode operator for the XLEMOO method.

The operator inspects an :class:`~desdeo.emo.hooks.archivers.Archive`,
trains a SkopeRulesClassifier on the best/worst split of past evaluations,
and uses the learned rules to instantiate a fresh population. It is plain
(non-Subscriber) and is meant to be invoked directly by a method template.
"""

import numpy as np
import polars as pl
from imodels import SkopeRulesClassifier

from desdeo.emo.hooks.archivers import Archive
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.selection import ASFSelector
from desdeo.explanations.rules import (
    extract_skoped_rules,
    instantiate_from_ruleset,
)
from desdeo.problem import Problem


def _split_indices(n_total: int, fraction: float) -> int:
    """Resolve an H/L split argument into a number of samples."""
    if fraction < 1.0:
        return int(fraction * n_total)
    half = n_total // 2
    if fraction > half:
        return int(half)
    return int(fraction)


class LearningModeOperator:
    """Performs the learning mode step of the XLEMOO method."""

    def __init__(
        self,
        problem: Problem,
        archive: Archive,
        evaluator: EMOEvaluator,
        selector: ASFSelector,
        h_split: float = 0.2,
        l_split: float = 0.2,
        instantiation_factor: float = 10.0,
        ml_model: SkopeRulesClassifier | None = None,
        seed: int | None = None,
    ):
        """Initialize the learning-mode operator.

        Args:
            problem (Problem): The optimization problem.
            archive (Archive): Archive holding all evaluated solutions so far.
            evaluator (EMOEvaluator): Evaluator used to score newly instantiated individuals.
            selector (ASFSelector): ASF selector that defines the target column and the
                desired population size.
            h_split (float, optional): Fraction (or absolute count if ``>= 1``) of unique
                individuals placed in the H-group. Defaults to ``0.2``.
            l_split (float, optional): Fraction (or absolute count if ``>= 1``) of unique
                individuals placed in the L-group. Defaults to ``0.2``.
            instantiation_factor (float, optional): Multiplier applied to ``population_size``
                to decide how many new individuals to instantiate from the rules.
                Defaults to ``10.0``.
            ml_model (SkopeRulesClassifier | None, optional): A pre-built classifier. If
                ``None``, a ``SkopeRulesClassifier`` with the article's defaults is built.
            seed (int | None, optional): Random seed forwarded to the default classifier.
        """
        self.problem = problem
        self.archive = archive
        self.evaluator = evaluator
        self.selector = selector
        self.h_split = h_split
        self.l_split = l_split
        self.instantiation_factor = instantiation_factor
        self.seed = seed

        self.variable_symbols: list[str] = [v.symbol for v in problem.get_flattened_variables()]
        self.variable_bounds: list[tuple[float, float]] = [
            (float(v.lowerbound), float(v.upperbound)) for v in problem.get_flattened_variables()
        ]

        if ml_model is None:
            ml_model = SkopeRulesClassifier(
                precision_min=0.1,
                n_estimators=30,
                bootstrap=True,
                bootstrap_features=True,
                random_state=seed,
            )
        self.ml_model = ml_model
        self.current_ml_model: SkopeRulesClassifier | None = None

    def _latest_generation_population(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Return the latest archived generation as ``(decision_variables, outputs)``."""
        solutions = self.archive.solutions
        latest_gen = int(solutions["generation"].max())
        latest = solutions.filter(pl.col("generation") == latest_gen).drop("generation")
        non_decs = [c for c in latest.columns if c not in self.variable_symbols]
        return latest[self.variable_symbols], latest[non_decs]

    def do(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Run one learning mode iteration.

        Returns:
            tuple[pl.DataFrame, pl.DataFrame]: Selected decision variables and their outputs.
        """
        target_column = self.selector.target_column
        population_size = self.selector.population_size

        all_solutions = self.archive.solutions
        non_dec_cols = [c for c in all_solutions.columns if c not in (*self.variable_symbols, "generation")]

        unique = all_solutions.unique(subset=self.variable_symbols, maintain_order=True)
        sorted_unique = unique.sort(target_column)

        n_total = sorted_unique.height
        h_size = _split_indices(n_total, self.h_split)
        l_size = _split_indices(n_total, self.l_split)

        if h_size == 0 or l_size == 0:
            return self._latest_generation_population()

        h_group = sorted_unique.head(h_size)
        l_group = sorted_unique.tail(l_size)

        h_vars = h_group[self.variable_symbols].to_numpy()
        l_vars = l_group[self.variable_symbols].to_numpy()

        x_train = np.vstack((h_vars, l_vars))
        y_train = np.hstack((np.ones(len(h_vars), dtype=int), np.zeros(len(l_vars), dtype=int)))

        self.current_ml_model = self.ml_model.fit(x_train, y_train, feature_names=self.variable_symbols)

        rules, weights = extract_skoped_rules(self.current_ml_model)
        if not rules:
            return self._latest_generation_population()

        n_to_instantiate = int(self.instantiation_factor * population_size)
        instantiated = instantiate_from_ruleset(
            rules_list=rules,
            weights=weights,
            variable_symbols=self.variable_symbols,
            variable_bounds=self.variable_bounds,
            n_samples=n_to_instantiate,
        )

        instantiated_df = pl.DataFrame(instantiated, schema=self.variable_symbols)
        instantiated_outputs = self.evaluator.evaluate(instantiated_df)

        h_outputs = h_group[non_dec_cols]

        return self.selector.do(
            parents=(h_group[self.variable_symbols], h_outputs),
            offsprings=(instantiated_df, instantiated_outputs),
        )
