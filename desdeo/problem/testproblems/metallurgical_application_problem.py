"""The microalloyed steel design problem of Saini et al. (2023).

A steel is designed by choosing the concentration of 17 alloying elements. Four mechanical properties
-- yield strength, ultimate tensile strength, elongation and Charpy impact energy -- are predicted from
the composition by surrogate models fitted to measurement data, and two further objectives, the carbon
equivalent and the material cost, are computed analytically from the same composition.

The property datasets are separate and barely overlap: the paper notes that "the different properties
are measured for entirely different alloy compositions", so each property gets its own model fitted to
its own data.

The datasets ship with the DESDEO repository under `datasets/MetallApplication/`, but they are not
part of the installed package, so `metallurgical_application` looks for them in the repository first
and downloads them from GitHub when it cannot find them. The surrogate models are trained on first use
and cached; see `metallurgical_application` for where.

References:
    Saini, B. S., Chakrabarti, D., Chakraborti, N., Shavazipour, B., & Miettinen, K. (2023).
        Interactive data-driven multiobjective optimization of metallurgical properties of
        microalloyed steels using the DESDEO framework. Engineering Applications of Artificial
        Intelligence, 120, 105918. https://doi.org/10.1016/j.engappai.2023.105918.

    Lancaster, J. F. (1999). Metallurgy of welding (6th ed.). Abington Publishing. The source of the
        carbon equivalent formula, cited as equation (2) of the paper above.

    `docs/howtoguides/advancedSurrogates.ipynb` documents a reduced four-objective version of this
    problem as a worked example of using surrogates in DESDEO. Where the guide and the paper differ,
    this module follows the paper; the differences are listed in `metallurgical_application`.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from desdeo.problem.schema import (
    Objective,
    ObjectiveTypeEnum,
    Problem,
    Variable,
    VariableTypeEnum,
)

_ELEMENTS: tuple[str, ...] = (
    "C",
    "Si",
    "Mn",
    "P",
    "S",
    "Mo",
    "Ni",
    "Al",
    "N",
    "Nb",
    "V",
    "B",
    "Ti",
    "Cr",
    "Ce",
    "Cu",
    "Zr",
)
"""The 17 alloying elements that are the decision variables, in weight per cent.

The datasets carry two further columns, `Ca` and `O`, which the paper does not use. The order matters:
the surrogate evaluator builds each model's input from the decision variable dictionary in insertion
order, with no reference to column names, so the models must see the columns in exactly this order.
"""

_ELEMENT_COSTS: dict[str, float] = {
    "C": 0.0,
    "Si": 0.122,
    "Mn": 1.7,
    "P": 1.82,
    "S": 2.69,
    "Mo": 0.0926,
    "Ni": 40.1,
    "Al": 13.9,
    "N": 1.79,
    "Nb": 0.140,
    "V": 72.0,
    "B": 3.68,
    "Ti": 11.5,
    "Cr": 9.4,
    "Ce": 4.6,
    "Cu": 6.0,
    "Zr": 237.0,
}
"""The cost of each alloying element in USD per kilogram, from Table 3 of the paper.

Carbon is priced at zero there, so it does not appear in the cost objective.
"""


@dataclass(frozen=True)
class _SurrogateSpec:
    """How one measured property is modelled.

    Attributes:
        dataset: the dataset file's stem, without the `.csv` suffix.
        column: the column of that file holding the measurement.
        regressor: the `sklearn.ensemble` class fitted to it.
        excluded: elements left out of this property's model.
        needs_temperature: whether the model also takes the test temperature.
    """

    dataset: str
    column: str
    regressor: str
    excluded: tuple[str, ...]
    needs_temperature: bool = False

    def inputs(self) -> tuple[str, ...]:
        """Return the elements this model is fitted on, in `_ELEMENTS` order."""
        return tuple(element for element in _ELEMENTS if element not in self.excluded)


# The regressors are the ones the paper selected by K-fold cross-validation (its Table 1), and the
# excluded elements are those its Table 2 reports no detectable effect for -- "the alloying elements
# with no reported effects were not considered for the model". The paper picked XGBoost for the
# tensile strength; see the note in `metallurgical_application` on why this uses gradient boosting.
_SURROGATE_SPEC: dict[str, _SurrogateSpec] = {
    "YS": _SurrogateSpec("ysdata", "YS", "ExtraTreesRegressor", excluded=("N", "B")),
    "UTS": _SurrogateSpec("utsdata", "UTS", "GradientBoostingRegressor", excluded=("N", "B")),
    "ELON": _SurrogateSpec("elondata", "ELON", "ExtraTreesRegressor", excluded=("Ce",)),
    "CHARPY": _SurrogateSpec(
        "charpydata",
        "Energy",
        "GradientBoostingRegressor",
        excluded=("Si", "B", "Ce", "Cu", "Zr"),
        needs_temperature=True,
    ),
}

_CARBON_EQUIVALENT = "C + (Mn + Si)/6 + (Cr + Mo + V)/5 + (Cu + Ni)/15"
"""The carbon equivalent, equation (2) of the paper, after Lancaster (1999).

Note the silicon: the how-to guide's version of this problem omits it and uses the plain International
Institute of Welding formula, `C + Mn/6 + (Cr + Mo + V)/5 + (Cu + Ni)/15`. The paper's version is used
here.
"""

DEFAULT_CHARPY_TEMPERATURE = -80.0
"""The test temperature in degrees Celsius the Charpy objective is evaluated at by default.

The paper holds it "constant at -80 C", which is the cold end of the range its Charpy data covers.
"""

OBJECTIVES: dict[str, tuple[str, bool]] = {
    "YS": ("Yield strength", True),
    "UTS": ("Ultimate tensile strength", True),
    "ELON": ("Elongation", True),
    "CHARPY": ("Charpy impact energy", True),
    "CE": ("Carbon equivalent", False),
    "COST": ("Material cost", False),
}
"""Every objective the problem can carry, mapped to its description and whether it is maximised.

The four measured properties are maximised; the carbon equivalent, which stands for how hard the alloy
is to weld, and the material cost are minimised. Pass any subset of the keys to
`metallurgical_application`.
"""

MOP_I: tuple[str, ...] = ("YS", "UTS", "ELON", "CHARPY", "CE", "COST")
"""The six-objective problem of the paper."""

MOP_II: tuple[str, ...] = ("YS", "UTS", "ELON", "CE", "COST")
"""The paper's simpler version of MOP-I, with the Charpy objective removed.

The paper introduces it "since, as mentioned, the Charpy surrogate model had a worse accuracy than the
other surrogate models", and notes that dropping it also widens the decision variable bounds. It is
the default here.
"""

_DATA_REPOSITORY = "https://raw.githubusercontent.com/industrial-optimization-group/DESDEO"
_DATA_REF = "master"
_DATA_SUBPATH = "datasets/MetallApplication"


class CompositionModel:
    """Adapts a model fitted on part of the composition to the full 17-element decision vector.

    Two things stand between the models and the decision vector. Each property's model is fitted only
    on the elements the paper found to affect it, so it takes fewer than 17 inputs; and the Charpy
    model additionally takes the temperature the impact test was run at, which is not a decision
    variable. This wrapper selects the columns the model was fitted on and, for Charpy, appends a
    fixed temperature.

    Holding the temperature constant is what keeps the decision space the same 17 elements for every
    objective. The temperature becomes a parameter of the problem instead, in the way that the load is
    a parameter of a beam design problem, and the paper does the same, fixing it at -80 degrees.
    """

    def __init__(self, model, indices: tuple[int, ...], temperature: float | None = None):
        """Wrap a fitted regressor.

        Args:
            model: a fitted regressor taking the selected elements, followed by the temperature when
                there is one.
            indices (tuple[int, ...]): positions in `_ELEMENTS` of the elements the model was fitted
                on, in the order it expects them.
            temperature (float | None, optional): the temperature to hold, in degrees Celsius, or None
                when the model does not take one. Defaults to None.
        """
        self.model = model
        self.indices = indices
        self.temperature = temperature

    def predict(self, x):
        """Predict for full compositions.

        Args:
            x: the compositions, one row per alloy, with all 17 columns in `_ELEMENTS` order.

        Returns:
            The model's prediction for each row.
        """
        x = np.asarray(x, dtype=float)[:, list(self.indices)]
        if self.temperature is not None:
            x = np.hstack((x, np.full((x.shape[0], 1), self.temperature)))
        return self.model.predict(x)


def _cache_root(cache_dir: Path | None = None) -> Path:
    """Return the directory that holds downloaded datasets and trained surrogates.

    Args:
        cache_dir (Path | None, optional): an explicit directory to use instead of the default.
            Defaults to None.

    Returns:
        Path: the cache directory, created if it did not exist.
    """
    if cache_dir is None:
        base = os.environ.get("XDG_CACHE_HOME")
        cache_dir = (Path(base) if base else Path.home() / ".cache") / "desdeo" / "MetallApplication"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _repository_data_dir() -> Path | None:
    """Find `datasets/MetallApplication` in a DESDEO checkout, if this module is running from one.

    Returns:
        Path | None: the directory, or None when running from an installed package.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / _DATA_SUBPATH
        if candidate.is_dir():
            return candidate
    return None


def _dataset_path(dataset: str, data_dir: Path | None, cache_dir: Path | None, *, download: bool) -> Path:
    """Locate one dataset, downloading it from the DESDEO repository if it is not available locally.

    The datasets are looked for in `data_dir` if given, then in the repository checkout this module
    lives in, then in the cache. Only if none of those has the file is it fetched.

    Args:
        dataset (str): the file's stem, for example `ysdata`.
        data_dir (Path | None): a directory to look in before anywhere else.
        cache_dir (Path | None): where to cache a downloaded file.
        download (bool): whether fetching from the repository is allowed.

    Raises:
        FileNotFoundError: if the file is not available locally and downloading is not allowed.
        RuntimeError: if the download fails.

    Returns:
        Path: the path to the dataset.
    """
    name = f"{dataset}.csv"

    for directory in (data_dir, _repository_data_dir(), _cache_root(cache_dir)):
        if directory is not None and (candidate := Path(directory) / name).is_file():
            return candidate

    target = _cache_root(cache_dir) / name
    url = f"{_DATA_REPOSITORY}/{_DATA_REF}/{_DATA_SUBPATH}/{name}"

    if not download:
        raise FileNotFoundError(
            f"The dataset {name} was not found locally and downloading is disabled. Either pass "
            f"data_dir pointing at a directory that contains it, or allow the download, which would "
            f"fetch {url} into {target.parent}."
        )

    import requests  # noqa: PLC0415  -- only needed when something actually has to be fetched

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"Could not download the dataset {name} from {url}: {error}") from error

    # Write beside the target and rename, so that a download interrupted halfway does not leave a
    # truncated file behind that later calls would happily read.
    partial = target.with_suffix(".csv.partial")
    partial.write_bytes(response.content)
    partial.replace(target)
    return target


def _read_dataset(target: str, data_dir: Path | None, cache_dir: Path | None, *, download: bool) -> pl.DataFrame:
    """Read one surrogate objective's dataset.

    Args:
        target (str): the objective symbol, for example `YS`.
        data_dir (Path | None): a directory to look in first.
        cache_dir (Path | None): where to cache downloaded files.
        download (bool): whether fetching from the repository is allowed.

    Returns:
        pl.DataFrame: the dataset.
    """
    return pl.read_csv(
        _dataset_path(_SURROGATE_SPEC[target].dataset, data_dir, cache_dir, download=download),
        # Several element columns are almost all zero, and the default schema inference reads a long
        # enough run of integers as an integer column.
        infer_schema_length=10000,
    )


def _variable_bounds(datasets: dict[str, pl.DataFrame]) -> tuple[dict[str, float], dict[str, float]]:
    """Derive the decision variable box as the intersection of the datasets' composition ranges.

    Args:
        datasets (dict[str, pl.DataFrame]): the datasets that define the box.

    Returns:
        tuple[dict[str, float], dict[str, float]]: the lower and upper bound of each element.
    """
    lower = {element: max(float(data[element].min()) for data in datasets.values()) for element in _ELEMENTS}
    upper = {element: min(float(data[element].max()) for data in datasets.values()) for element in _ELEMENTS}
    return lower, upper


def _surrogate_path(
    target: str, data: pl.DataFrame, random_state: int, temperature: float | None, cache_dir: Path | None
) -> Path:
    """Return where the surrogate for one property belongs in the cache.

    The name carries the scikit-learn version, the seed, the Charpy temperature where there is one,
    and a digest of the training data, so a cached model is only ever reused for the thing it was
    trained for. The version matters in particular: a model pickled by one scikit-learn release can
    fail to unpickle under another, and silently reusing a stale file is how that turns into a
    confusing import error at evaluation time.

    Args:
        target (str): the objective symbol, for example `YS`.
        data (pl.DataFrame): the training data, used for the digest.
        random_state (int): the seed the regressor is fitted with.
        temperature (float | None): the fixed Charpy temperature, or None for the other properties.
        cache_dir (Path | None): an explicit cache directory, or None for the default.

    Returns:
        Path: the path the model is cached at, which need not exist yet.
    """
    import sklearn  # noqa: PLC0415  -- imported here to keep it off the module import path

    digest = hashlib.blake2b(data.hash_rows().to_numpy().tobytes(), digest_size=8).hexdigest()
    suffix = "" if temperature is None else f"-t{temperature!r}"
    return _cache_root(cache_dir) / f"{target}-sklearn{sklearn.__version__}-seed{random_state}{suffix}-{digest}.joblib"


def _ensure_surrogate(
    target: str, data: pl.DataFrame, random_state: int, temperature: float | None, cache_dir: Path | None
) -> Path:
    """Return a usable surrogate for one property, training and caching it if necessary.

    Args:
        target (str): the objective symbol, for example `YS`.
        data (pl.DataFrame): the property's dataset.
        random_state (int): the seed the regressor is fitted with.
        temperature (float | None): the fixed Charpy temperature, or None for the other properties.
        cache_dir (Path | None): an explicit cache directory, or None for the default.

    Returns:
        Path: the path to a model file that loads.
    """
    import joblib  # noqa: PLC0415
    from sklearn import ensemble  # noqa: PLC0415

    spec = _SURROGATE_SPEC[target]
    path = _surrogate_path(target, data, random_state, temperature, cache_dir)

    if path.is_file():
        try:
            joblib.load(path)
        except Exception:  # any failure to load means the cache entry is unusable
            path.unlink(missing_ok=True)
        else:
            return path

    elements = spec.inputs()
    # The temperature goes last, which is where CompositionModel appends it at prediction time.
    columns = [*elements, "Temperature"] if temperature is not None else list(elements)

    model = getattr(ensemble, spec.regressor)(n_estimators=100, random_state=random_state)
    model.fit(data[columns].to_numpy(), data[spec.column].to_numpy())

    wrapped = CompositionModel(model, tuple(_ELEMENTS.index(element) for element in elements), temperature)

    partial = path.with_suffix(".joblib.partial")
    joblib.dump(wrapped, partial)
    partial.replace(path)
    return path


def _cost_expression() -> str:
    """Write the material cost as a weighted sum of the composition.

    Returns:
        str: the cost expression, omitting the elements priced at zero.
    """
    return " + ".join(f"{cost!r} * {element}" for element, cost in _ELEMENT_COSTS.items() if cost != 0.0)


def metallurgical_application(
    objectives: tuple[str, ...] | list[str] = MOP_II,
    *,
    random_state: int = 0,
    charpy_temperature: float = DEFAULT_CHARPY_TEMPERATURE,
    data_dir: Path | None = None,
    cache_dir: Path | None = None,
    download: bool = True,
) -> Problem:
    r"""Defines the microalloyed steel design problem of Saini et al. (2023).

    A steel is designed by choosing the weight per cent of 17 alloying elements. Four of the six
    objectives -- yield strength, ultimate tensile strength, elongation and Charpy impact energy --
    are predicted from the composition by surrogate models fitted to measurement data and are
    maximised. The other two are analytical and minimised: the carbon equivalent, which stands for how
    hard the alloy is to weld, and the material cost.

    \begin{align}
        \text{CE} &= C + \frac{Mn + Si}{6} + \frac{Cr + Mo + V}{5} + \frac{Cu + Ni}{15} \\
        \text{COST} &= \sum_i \text{price}_i \cdot c_i
    \end{align}

    The paper's own two formulations are available as `MOP_I`, all six objectives, and `MOP_II`, which
    drops the Charpy objective. `MOP_II` is the default, following the paper, which introduces it
    because "the Charpy surrogate model had a worse accuracy than the other surrogate models".

    Objective subsets:
        Pass any subset of `OBJECTIVES` to get a different version of the problem. Only the surrogates
        for the chosen properties are trained, so asking for `("CE", "YS")` does not pay for the
        models it will not use.

        **The decision variable bounds depend on which objectives are chosen.** They are the
        intersection of the composition ranges of the datasets behind the selected surrogate
        objectives, so dropping a property widens the box, as it does between the paper's MOP-I and
        MOP-II: "removing this objective also led to an expansion of the bounds of the decision
        variables (calculated as the bounds of the intersection of the remaining datasets)". The
        intersection is what keeps every point of the box inside the range each model was fitted on,
        so no model is asked to extrapolate. When no surrogate objective is selected at all, the
        intersection of all four datasets is used.

        A study that compares subsets against each other should know that they therefore do not share
        a decision space, and that the comparison is between problems, not between objective counts on
        one problem.

    Note:
        **Three deviations from the paper, and one from the how-to guide, all deliberate.**

        The paper selects XGBoost for the tensile strength by cross-validation, at a median $R^2$ of
        0.8440 against gradient boosting's 0.8437. Gradient boosting is used here instead: the gap is
        two parts in ten thousand of a quantity whose standard deviation across folds is 0.07, and
        `xgboost` is not a DESDEO dependency.

        The paper's Table 3 lists the bounds it used. Five of the seventeen upper bounds computed from
        the datasets in this repository differ from it -- manganese, nickel, aluminium, boron and
        copper -- so the data shipped here is not exactly the data the paper's numbers came from. The
        bounds are computed from the shipped data rather than hard-coded from the table, so that the
        box always matches the models actually fitted.

        The paper reports an ideal cost of about 43 USD per kg, which the cost formula above does not
        reproduce: read as weight per cent times USD per kg, the cheapest point of the box costs well
        under 1. The paper does not state the unit convention, so the formula is implemented as
        written and the discrepancy is left visible rather than tuned away.

        The how-to guide omits the silicon term from the carbon equivalent, uses gradient boosting for
        the tensile strength, fits every model on all 17 elements, and has neither the Charpy nor the
        cost objective. This module follows the paper.

        The training data contains repeated compositions with different measured values -- the same
        alloy behaves differently after different processing -- so the models cannot interpolate their
        own training data exactly. The paper's cross-validated $R^2$ is 0.75 for yield strength, 0.84
        for tensile strength, 0.67 for elongation and 0.44 for the Charpy energy, which is the one to
        keep in mind when reading results.

    Data and models:
        The datasets ship with the DESDEO repository but not with the installed package. They are
        looked for in `data_dir`, then in the repository checkout this module lives in, then in the
        cache; only if none of those has them are they downloaded from GitHub.

        Trained models are cached under `$XDG_CACHE_HOME/desdeo/MetallApplication` (or
        `~/.cache/desdeo/MetallApplication`), keyed by the scikit-learn version, the seed, the Charpy
        temperature and a digest of the training data. Training them takes a few seconds; later calls
        load the cache. A cached file that fails to load is discarded and retrained rather than
        raised, which is what happens when scikit-learn is upgraded under an old pickle.

        `random_state` is passed to every regressor, so the problem is reproducible for a given seed
        and scikit-learn version. The how-to guide leaves it unset, and its models therefore differ
        from run to run.

        Each model is wrapped in a `CompositionModel`, which selects the elements that model was
        fitted on and, for the Charpy energy, appends the fixed test temperature. The wrapper is what
        lets every objective share one 17-element decision vector.

    Args:
        objectives (tuple[str, ...] | list[str], optional): which objectives to include, as symbols
            from `OBJECTIVES`. The order given is the order they appear in. Defaults to `MOP_II`.
        random_state (int, optional): the seed the regressors are fitted with. Defaults to 0.
        charpy_temperature (float, optional): the temperature in degrees Celsius the Charpy impact
            energy is evaluated at. Ignored unless `CHARPY` is among the objectives. Defaults to
            `DEFAULT_CHARPY_TEMPERATURE`.
        data_dir (Path | None, optional): a directory to look for the datasets in before anywhere
            else. Defaults to None.
        cache_dir (Path | None, optional): where to cache datasets and models. Defaults to None,
            meaning the user cache directory.
        download (bool, optional): whether the datasets may be fetched from the DESDEO repository when
            they are not available locally. Defaults to True.

    Raises:
        ValueError: if `objectives` is empty, names an unknown objective, or repeats one.
        FileNotFoundError: if a dataset is missing locally and `download` is False.
        RuntimeError: if a dataset has to be downloaded and the download fails.

    Returns:
        Problem: an instance of the microalloyed steel design problem.
    """
    chosen = list(objectives)
    if not chosen:
        raise ValueError("At least one objective is needed; `objectives` was empty.")
    if unknown := [symbol for symbol in chosen if symbol not in OBJECTIVES]:
        raise ValueError(f"Unknown objective(s) {unknown}. Available objectives are {sorted(OBJECTIVES)}.")
    if len(set(chosen)) != len(chosen):
        raise ValueError(f"`objectives` repeats an objective: {chosen}.")

    surrogate_targets = [symbol for symbol in chosen if symbol in _SURROGATE_SPEC]
    # With no surrogate objective there is no data to derive a box from, so all four datasets are used
    # and the box is the narrowest of the ones any selection could give.
    bound_targets = surrogate_targets or list(_SURROGATE_SPEC)
    datasets = {
        target: _read_dataset(target, data_dir, cache_dir, download=download)
        for target in dict.fromkeys([*bound_targets, *surrogate_targets])
    }
    lower, upper = _variable_bounds({target: datasets[target] for target in bound_targets})

    variables = [
        Variable(
            name=element,
            symbol=element,
            variable_type=VariableTypeEnum.real,
            lowerbound=lower[element],
            upperbound=upper[element],
            initial_value=(lower[element] + upper[element]) / 2,
        )
        for element in _ELEMENTS
    ]

    analytical = {"CE": _CARBON_EQUIVALENT, "COST": _cost_expression()}

    problem_objectives = []
    for symbol in chosen:
        description, maximize = OBJECTIVES[symbol]

        if symbol in analytical:
            problem_objectives.append(
                Objective(
                    name=description,
                    symbol=symbol,
                    func=analytical[symbol],
                    objective_type=ObjectiveTypeEnum.analytical,
                    maximize=maximize,
                    is_linear=True,
                    is_convex=True,
                    is_twice_differentiable=True,
                )
            )
            continue

        temperature = charpy_temperature if _SURROGATE_SPEC[symbol].needs_temperature else None
        problem_objectives.append(
            Objective(
                name=description,
                symbol=symbol,
                surrogates=[_ensure_surrogate(symbol, datasets[symbol], random_state, temperature, cache_dir)],
                objective_type=ObjectiveTypeEnum.surrogate,
                maximize=maximize,
                is_linear=False,
                is_convex=False,
                is_twice_differentiable=False,
            )
        )

    charpy_note = f", with the Charpy energy at {charpy_temperature} degrees Celsius" if "CHARPY" in chosen else ""
    return Problem(
        name="metallurgical application",
        description=(
            f"Microalloyed steel design from 17 alloying elements, with {len(chosen)} objective(s): "
            f"{', '.join(chosen)}{charpy_note}. The mechanical properties come from surrogate models "
            "fitted to measurement data; the carbon equivalent and the material cost are analytical."
        ),
        variables=variables,
        objectives=problem_objectives,
    )
