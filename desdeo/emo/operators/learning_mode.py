"""Learning-mode operator for the XLEMOO method.

The operator subscribes to the same ``VERBOSE_OUTPUTS`` stream the archive
listens to, and maintains its own bounded H-group (best-by-target) and
L-group (worst-by-target) of unique decision vectors seen so far. When
`do()` is called, it trains a `SkopeRulesClassifier`
on those groups and returns a fresh batch of decision vectors
instantiated from the extracted rules.

Keeping only the H/L groups (rather than the unbounded archive) makes the
per-generation ``unique()`` cost proportional to the population size,
independent of run length.
"""

from collections.abc import Sequence

import numpy as np
import polars as pl
from imodels import SkopeRulesClassifier

from desdeo.emo.operators.scalar_selection import ElitistSelection
from desdeo.explanations.rules import (
    extract_skoped_rules,
    instantiate_from_ruleset,
)
from desdeo.problem import Problem
from desdeo.tools.message import EvaluatorMessageTopics, GeneratorMessageTopics, Message, MessageTopics
from desdeo.tools.patterns import Publisher, Subscriber


class LearningModeOperator(Subscriber):
    """Performs the learning mode step of the XLEMOO method.

    The operator subscribes to ``VERBOSE_OUTPUTS`` from the evaluator and
    generator and maintains its own bounded H-group / L-group of the
    best- and worst-by-target unique decision vectors seen so far.
    `do()` trains a SkopeRulesClassifier on those groups and returns
    a fresh batch of decision vectors instantiated from the extracted
    rules. The caller (typically
    [template_xlemoo][desdeo.emo.methods.templates.template_xlemoo]) evaluates the
    returned candidates and integrates them with the current population
    through its own selection step.
    """

    @property
    def interested_topics(self) -> Sequence[MessageTopics]:
        """Subscribe to verbose outputs from the evaluator and generator."""
        return [
            EvaluatorMessageTopics.VERBOSE_OUTPUTS,
            GeneratorMessageTopics.VERBOSE_OUTPUTS,
        ]

    @property
    def provided_topics(self) -> dict[int, Sequence[MessageTopics]]:
        """No outgoing messages yet; the operator's results flow through its return value."""
        return {0: [], 1: [], 2: []}

    def __init__(
        self,
        problem: Problem,
        selector: ElitistSelection,
        publisher: Publisher,
        verbosity: int = 2,
        h_split: float = 0.2,
        l_split: float = 0.2,
        instantiation_factor: float = 10.0,
        ml_model: SkopeRulesClassifier | None = None,
        seed: int = 0,
    ):
        """Initialize the learning-mode operator.

        Args:
            problem (Problem): The optimization problem.
            selector (ElitistSelection): The selector used by the surrounding
                algorithm. Its ``target_column`` decides which scalar fitness
                column ranks H vs L, and its ``winner_size`` sets both the
                H/L group budget and the size of the instantiated batch.
            publisher (Publisher): The pub/sub publisher for the current run.
            verbosity (int, optional): Verbosity level, passed to the Subscriber
                base class. Defaults to ``2``.
            h_split (float, optional): Fraction of ``selector.winner_size``
                kept as the H-group budget (top-by-target). Must be in
                ``(0, 1]``. Defaults to ``0.2``.
            l_split (float, optional): Fraction of ``selector.winner_size``
                kept as the L-group budget (bottom-by-target). Must be in
                ``(0, 1]``. Defaults to ``0.2``.
            instantiation_factor (float, optional): Multiplier on ``selector.winner_size``
                deciding how many candidates to instantiate from the rules. Defaults to ``10.0``.
            ml_model (SkopeRulesClassifier | None, optional): A pre-built classifier. If
                ``None``, a ``SkopeRulesClassifier`` with the article's defaults is built.
            seed (int, optional): Random seed forwarded both to the rule-instantiation
                generator and to the default classifier. Defaults to ``0``.
        """
        super().__init__(publisher=publisher, verbosity=verbosity)
        if not 0.0 < h_split <= 1.0:
            raise ValueError(f"h_split must be in (0, 1]; got {h_split}.")
        if not 0.0 < l_split <= 1.0:
            raise ValueError(f"l_split must be in (0, 1]; got {l_split}.")

        self.problem = problem
        self.selector = selector
        self.h_split = h_split
        self.l_split = l_split
        self.instantiation_factor = instantiation_factor
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.variable_symbols: list[str] = [v.symbol for v in problem.get_flattened_variables()]
        self.variable_bounds: list[tuple[float, float]] = [
            (float(v.lowerbound), float(v.upperbound)) for v in problem.get_flattened_variables()
        ]

        self.h_size: int = max(1, round(h_split * selector.winner_size))
        self.l_size: int = max(1, round(l_split * selector.winner_size))
        self.h_group: pl.DataFrame | None = None
        self.l_group: pl.DataFrame | None = None

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

    def _ingest(self, data: pl.DataFrame) -> None:
        """Fold a new evaluation batch into the H- and L-groups.

        Concatenates ``data`` with the current ``h_group`` and ``l_group``, deduplicates
        on the decision-variable columns, sorts by ``selector.target_column``, and keeps
        the top ``h_size`` and bottom ``l_size`` rows.
        """
        target_column = self.selector.target_column
        if target_column not in data.columns:
            return

        columns = [*self.variable_symbols, target_column]
        frames = [data.select(columns)]
        if self.h_group is not None:
            frames.append(self.h_group)
        if self.l_group is not None:
            frames.append(self.l_group)

        combined = pl.concat(frames, how="vertical_relaxed")
        combined = combined.unique(subset=self.variable_symbols, maintain_order=True)
        combined = combined.sort(target_column)

        self.h_group = combined.head(self.h_size)
        self.l_group = combined.tail(self.l_size)

    def update(self, message: Message) -> None:
        """Fold each ``VERBOSE_OUTPUTS`` message into the H- and L-groups."""
        if message.topic not in (
            EvaluatorMessageTopics.VERBOSE_OUTPUTS,
            GeneratorMessageTopics.VERBOSE_OUTPUTS,
        ):
            return
        data = message.value
        if not isinstance(data, pl.DataFrame) or data.height == 0:
            return
        self._ingest(data)

    def do(self) -> pl.DataFrame | None:
        """Run one learning mode iteration.

        Trains a SkopeRulesClassifier on the maintained H- and L-groups and returns
        a fresh batch of decision vectors instantiated from the extracted rules.

        Returns:
            pl.DataFrame | None: The instantiated decision-variable DataFrame
                (one row per candidate), or ``None`` when no usable rules can
                be extracted (the operator has not yet observed any evaluation,
                one of the groups is still empty, or SkopeRules returned an
                empty ruleset). The caller should fall back to the existing
                population in that case.
        """
        if self.h_group is None or self.l_group is None:
            return None
        if self.h_group.height == 0 or self.l_group.height == 0:
            return None

        h_vars = self.h_group[self.variable_symbols].to_numpy()
        l_vars = self.l_group[self.variable_symbols].to_numpy()

        x_train = np.vstack((h_vars, l_vars))
        y_train = np.hstack((np.ones(len(h_vars), dtype=int), np.zeros(len(l_vars), dtype=int)))

        self.current_ml_model = self.ml_model.fit(x_train, y_train, feature_names=self.variable_symbols)

        rules, weights = extract_skoped_rules(self.current_ml_model)
        if not rules:
            return None

        n_to_instantiate = int(self.instantiation_factor * self.selector.winner_size)
        instantiated = instantiate_from_ruleset(
            rules_list=rules,
            weights=weights,
            variable_symbols=self.variable_symbols,
            variable_bounds=self.variable_bounds,
            n_samples=n_to_instantiate,
            rng=self.rng,
        )

        return pl.DataFrame(instantiated, schema=self.variable_symbols)

    def state(self) -> Sequence[Message]:
        """No outgoing messages; learning results are exposed via the return value of `do()`."""
        return []
