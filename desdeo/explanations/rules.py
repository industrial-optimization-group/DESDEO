"""Utilities for extracting, instantiating, and parsing rules learned by interpretable classifiers.

These helpers operate on rules produced by interpretable classifiers (notably
the SkopeRulesClassifier from the imodels package) and convert them into
actionable per-variable bounds. All functions that need to map between
variable symbols and array column indices accept an explicit list of variable
symbols, so any naming scheme (e.g. ``"thickness"``, ``"x_1"``, ``"speed"``)
is supported. The list of variable symbols is treated as the canonical
ordering: position ``i`` in the list corresponds to column ``i`` in the
samples and population arrays.
"""

import numpy as np

Rule = dict[tuple[str, str], str]
"""A single rule: keys are ``(variable_symbol, comparison_operator)`` pairs,
values are threshold values as strings. Comparison operators are ``"<"``,
``"<="``, ``">"``, ``">="``, ``"="``, or ``"=="``."""


def extract_skoped_rules(classifier) -> tuple[list[Rule], list[float]]:
    """Extract rules and their precisions from a trained ``SkopeRulesClassifier``.

    Args:
        classifier: A trained ``imodels.SkopeRulesClassifier`` exposing a
            ``rules_`` attribute. Each rule must provide ``agg_dict`` and a
            ``args`` tuple whose first element is the precision.

    Returns:
        tuple[list[Rule], list[float]]: The extracted rules and their precisions.
    """
    precisions = [rule.args[0] for rule in classifier.rules_]
    rules = [rule.agg_dict for rule in classifier.rules_]
    return rules, precisions


def instantiate_from_rules(
    rules: Rule,
    variable_symbols: list[str],
    variable_bounds: list[tuple[float, float]],
    n_samples: int,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Sample decision vectors that satisfy the bounds defined by a single rule.

    For each variable, the sampling range is the variable's box constraint
    intersected with any tighter bounds the rule defines. Variables not
    referenced by the rule are sampled uniformly within their box constraints.
    If the rule's threshold falls outside the box constraint, the box
    constraint is kept (it overrides the rule). Rule keys whose variable
    symbol is not present in ``variable_symbols`` are silently ignored.

    Args:
        rules (Rule): A single rule dict mapping ``(variable_symbol, op)`` to
            a threshold string.
        variable_symbols (list[str]): The decision-variable symbols. Position
            ``i`` in this list determines column ``i`` of the returned array.
        variable_bounds (list[tuple[float, float]]): ``(lower, upper)`` for each
            variable, in the same order as ``variable_symbols``.
        n_samples (int): How many decision vectors to generate.
        rng (np.random.Generator | None, optional): Random generator used for
            sampling. If ``None``, a fresh OS-seeded generator is created on
            every call (non-deterministic). Pass an explicit generator for
            reproducibility.

    Returns:
        np.ndarray: A 2D array of shape ``(n_samples, len(variable_symbols))``.
    """
    if rng is None:
        rng = np.random.default_rng()
    symbol_to_index = {symbol: i for i, symbol in enumerate(variable_symbols)}

    op_value_per_index: dict[int, list[tuple[str, float]]] = {}
    for (var_symbol, op), threshold in rules.items():
        if var_symbol not in symbol_to_index:
            continue
        idx = symbol_to_index[var_symbol]
        op_value_per_index.setdefault(idx, []).append((op, float(threshold)))

    n_variables = len(variable_symbols)
    new_samples = np.zeros((n_samples, n_variables))
    for feature_i in range(n_variables):
        current_min, current_max = variable_bounds[feature_i]

        if feature_i not in op_value_per_index:
            new_samples[:, feature_i] = rng.uniform(current_min, current_max, n_samples)
            continue

        for op, value in op_value_per_index[feature_i]:
            if op in ("<", "<="):
                if current_min < value < current_max:
                    current_max = value
            elif op in (">", ">="):
                if current_min < value < current_max:
                    current_min = value
            elif op in ("=", "=="):
                current_min = value
                current_max = value

        new_samples[:, feature_i] = rng.uniform(current_min, current_max, n_samples)

    return new_samples


def instantiate_from_ruleset(
    rules_list: list[Rule],
    weights: list[float],
    variable_symbols: list[str],
    variable_bounds: list[tuple[float, float]],
    n_samples: int,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Distribute ``n_samples`` across a list of rules proportional to their weights.

    Rules with negative weights are skipped. The total number of returned rows
    may differ slightly from ``n_samples`` due to per-rule rounding.

    Args:
        rules_list (list[Rule]): The rule dicts to instantiate from.
        weights (list[float]): The weight of each rule. Must be at least as
            long as ``rules_list``; surplus rules are dropped if shorter.
        variable_symbols (list[str]): The decision-variable symbols. Position
            ``i`` in this list determines column ``i`` of the returned array.
        variable_bounds (list[tuple[float, float]]): ``(lower, upper)`` for each
            variable, in the same order as ``variable_symbols``.
        n_samples (int): Approximate total number of samples to generate.
        rng (np.random.Generator | None, optional): Random generator used for
            sampling. If ``None``, a fresh OS-seeded generator is created on
            every call (non-deterministic). Pass an explicit generator for
            reproducibility.

    Returns:
        np.ndarray: A 2D array stacking all generated samples.
    """
    if rng is None:
        rng = np.random.default_rng()
    if len(weights) < len(rules_list):
        rules_list = rules_list[: len(weights)]

    w_arr = np.array(weights, dtype=float)
    positive_mask = w_arr >= 0
    fractions = w_arr[positive_mask] / np.sum(w_arr[positive_mask])
    n_per_rule = np.round(fractions * n_samples).astype(int)

    rules_pos = [rule for rule, keep in zip(rules_list, positive_mask, strict=True) if keep]

    instantiated = [
        instantiate_from_rules(rule, variable_symbols, variable_bounds, int(n_per_rule[i]), rng=rng)
        for i, rule in enumerate(rules_pos)
    ]
    return np.vstack(instantiated)


def parse_rules_to_variable_bounds(
    rules_list: list[Rule],
    accuracies: list[float],
    variable_symbols: list[str],
    variable_bounds: list[tuple[float, float]],
) -> dict:
    """Aggregate rules into per-variable upper and lower bounds with accuracies.

    For every variable symbol, returns the tightest bound found across all
    rules together with the precision of the rule supplying it. If no rule
    references a given bound, the box-constraint bound is used and its
    accuracy is set to ``-1``.

    Args:
        rules_list (list[Rule]): Rules to aggregate.
        accuracies (list[float]): Precision/accuracy for each rule, paired by
            index with ``rules_list``.
        variable_symbols (list[str]): Variable symbols, in the same order as
            ``variable_bounds``.
        variable_bounds (list[tuple[float, float]]): Box constraints
            ``(lower, upper)`` per variable.

    Returns:
        dict: Mapping ``{symbol: {">": [bound, accuracy], "<=": [bound, accuracy]}}``.
    """
    rules_for_vars: dict[str, dict[str, list[float]]] = {
        symbol: {
            ">": [float(variable_bounds[i][0]), -1.0],
            "<=": [float(variable_bounds[i][1]), -1.0],
        }
        for i, symbol in enumerate(variable_symbols)
    }

    for accuracy, rule in zip(accuracies, rules_list, strict=True):
        for key in rule:
            var_name, op = key
            if var_name not in rules_for_vars or op not in rules_for_vars[var_name]:
                continue
            if rules_for_vars[var_name][op][1] < accuracy:
                rules_for_vars[var_name][op][1] = accuracy
                threshold = float(rule[key])
                current = rules_for_vars[var_name][op][0]
                if (op == "<=" and threshold <= current) or (op == ">" and threshold > current):
                    rules_for_vars[var_name][op][0] = threshold

    return rules_for_vars


def complete_bounds_from_population(
    parsed_bounds: dict,
    population: np.ndarray,
    variable_symbols: list[str],
) -> dict:
    """Replace placeholder bounds (accuracy ``-1``) with the population's per-variable extrema.

    Args:
        parsed_bounds (dict): Output of :func:`parse_rules_to_variable_bounds`.
        population (np.ndarray): A 2D array of shape ``(n_individuals, n_variables)``.
        variable_symbols (list[str]): Variable symbols matching the columns of
            ``population``.

    Returns:
        dict: The updated bounds dict.
    """
    lower_bounds = np.min(population, axis=0)
    upper_bounds = np.max(population, axis=0)

    for var_i, var_name in enumerate(variable_symbols):
        for op in parsed_bounds[var_name]:
            if parsed_bounds[var_name][op][1] != -1:
                continue
            if op == "<=":
                parsed_bounds[var_name][op][0] = float(upper_bounds[var_i])
            elif op == ">":
                parsed_bounds[var_name][op][0] = float(lower_bounds[var_i])

    return parsed_bounds


def format_rule_summary(
    parsed_bounds: dict,
    variable_symbols: list[str],
    population_bounds: dict[str, tuple[float, float]],
) -> list[dict]:
    """Combine parsed rule bounds with population-derived bounds into a row-per-variable summary.

    Each entry has the variable symbol, the rule-derived lower/upper bound and the
    accuracy of the rule that supplied each bound, plus the empirical lower/upper bound
    observed in the final population. Accuracies of ``-1`` indicate that the rule-side
    bound came from the box constraint (no rule covered it).

    Args:
        parsed_bounds (dict): Output of :func:`parse_rules_to_variable_bounds`
            (or :func:`complete_bounds_from_population`).
        variable_symbols (list[str]): Variable symbols, in display order.
        population_bounds (dict[str, tuple[float, float]]): ``{symbol: (min, max)}`` from
            the final population.

    Returns:
        list[dict]: One dict per variable with keys ``"variable"``, ``"rule_lower"``,
            ``"rule_lower_accuracy"``, ``"rule_upper"``, ``"rule_upper_accuracy"``,
            ``"pop_lower"``, ``"pop_upper"``.
    """
    summary: list[dict] = []
    for symbol in variable_symbols:
        bounds = parsed_bounds[symbol]
        pop_lower, pop_upper = population_bounds[symbol]
        summary.append(
            {
                "variable": symbol,
                "rule_lower": float(bounds[">"][0]),
                "rule_lower_accuracy": float(bounds[">"][1]),
                "rule_upper": float(bounds["<="][0]),
                "rule_upper_accuracy": float(bounds["<="][1]),
                "pop_lower": float(pop_lower),
                "pop_upper": float(pop_upper),
            }
        )
    return summary


def format_rule_table(rule_summary: list[dict]) -> str:
    """Render :func:`format_rule_summary` output as an aligned plain-text table.

    Bound values are shown with 5-decimal precision; accuracies with 3-decimal
    precision. Accuracy ``-1`` is rendered as the literal ``"-1"`` to flag that
    the bound came from the box constraint rather than a rule.

    Args:
        rule_summary (list[dict]): Output of :func:`format_rule_summary`.

    Returns:
        str: The formatted table including a header row.
    """
    headers = ["Variable", "Rule Lower", "Acc", "Rule Upper", "Acc", "Pop Lower", "Pop Upper"]

    def _fmt_acc(value: float) -> str:
        return "-1" if value == -1 else f"{value:.3f}"

    rows: list[list[str]] = [headers]
    for entry in rule_summary:
        rows.append(
            [
                entry["variable"],
                f"{entry['rule_lower']:.5f}",
                _fmt_acc(entry["rule_lower_accuracy"]),
                f"{entry['rule_upper']:.5f}",
                _fmt_acc(entry["rule_upper_accuracy"]),
                f"{entry['pop_lower']:.5f}",
                f"{entry['pop_upper']:.5f}",
            ]
        )

    col_widths = [max(len(row[c]) for row in rows) for c in range(len(headers))]
    lines = ["  ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) for row in rows]
    return "\n".join(lines)
