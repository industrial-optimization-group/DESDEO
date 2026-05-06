"""Learning-mode operator for the XLEMOO method.

The operator inspects an :class:`~desdeo.emo.hooks.archivers.Archive`,
trains a SkopeRulesClassifier on the best/worst split of past evaluations,
and uses the learned rules to instantiate a fresh batch of decision vectors.

It is a :class:`~desdeo.tools.patterns.Subscriber` so it participates in the
pub/sub consistency check, but it currently neither subscribes to nor
publishes any messages: the algorithm template invokes :meth:`do` directly
and decides what to do with the returned candidates.
"""

from collections.abc import Sequence

import numpy as np
import polars as pl
from imodels import SkopeRulesClassifier

from desdeo.emo.hooks.archivers import Archive
from desdeo.emo.operators.scalar_selection import ElitistSelection
from desdeo.explanations.rules import (
    extract_skoped_rules,
    instantiate_from_ruleset,
)
from desdeo.problem import Problem
from desdeo.tools.message import Message, MessageTopics
from desdeo.tools.patterns import Publisher, Subscriber


class LearningModeOperator(Subscriber):
    """Performs the learning mode step of the XLEMOO method.

    Trains a SkopeRulesClassifier on the H/L split of unique past
    evaluations stored in the archive and returns a fresh batch of
    decision vectors instantiated from the extracted rules. The caller
    (typically :func:`~desdeo.emo.methods.templates.template_xlemoo`) is
    responsible for evaluating the returned candidates and integrating
    them with the current population through its own selection step.
    """

    @property
    def interested_topics(self) -> Sequence[MessageTopics]:
        """No subscriptions: the operator reads from the archive directly."""
        return []

    @property
    def provided_topics(self) -> dict[int, Sequence[MessageTopics]]:
        """No outgoing messages yet; the operator's results flow through its return value."""
        return {0: [], 1: [], 2: []}

    def __init__(
        self,
        problem: Problem,
        archive: Archive,
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
            archive (Archive): Archive of all evaluated solutions so far.
            selector (ElitistSelection): The selector used by the surrounding
                algorithm. Only its ``winner_size`` is read here, to size the
                instantiated batch.
            publisher (Publisher): The pub/sub publisher for the current run.
            verbosity (int, optional): Verbosity level, passed to the Subscriber
                base class. Defaults to ``2``.
            h_split (float, optional): Fraction of unique individuals placed in the
                H-group. Must be in ``(0, 1]``. Defaults to ``0.2``.
            l_split (float, optional): Fraction of unique individuals placed in the
                L-group. Must be in ``(0, 1]``. Defaults to ``0.2``.
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
        self.archive = archive
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

    def do(self) -> pl.DataFrame | None:
        """Run one learning mode iteration.

        Pulls all past evaluations from the archive, trains a SkopeRulesClassifier
        on the H/L split, and returns a fresh batch of decision vectors instantiated
        from the extracted rules.

        Returns:
            pl.DataFrame | None: The instantiated decision-variable DataFrame
                (one row per candidate), or ``None`` when no usable rules can
                be extracted (e.g. the archive is empty for one of the groups,
                or SkopeRules returned an empty ruleset). The caller should
                fall back to the existing population in that case.
        """
        target_column = self.selector.target_column

        all_solutions = self.archive.solutions
        if all_solutions is None or all_solutions.height == 0:
            return None

        unique = all_solutions.unique(subset=self.variable_symbols, maintain_order=True)
        sorted_unique = unique.sort(target_column)

        n_total = sorted_unique.height
        h_size = int(self.h_split * n_total)
        l_size = int(self.l_split * n_total)
        if h_size == 0 or l_size == 0:
            return None

        h_group = sorted_unique.head(h_size)
        l_group = sorted_unique.tail(l_size)

        h_vars = h_group[self.variable_symbols].to_numpy()
        l_vars = l_group[self.variable_symbols].to_numpy()

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

    def update(self, message: Message) -> None:
        """No-op: the operator subscribes to nothing."""

    def state(self) -> Sequence[Message]:
        """No outgoing messages; learning results are exposed via the return value of :meth:`do`."""
        return []
