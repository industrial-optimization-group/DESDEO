# How to add a solution description to a problem

By default, the web-GUI shows a solution as a list of objective values. For many
problems, those numbers alone do not tell a decision maker what the solution
actually means. They may also want to know which investments it makes, what each
part of the cost is, or how many hours of demand go unmet. A
`SolutionDescriptionMetaData` attached to a problem tells the web-API how to turn
any solution of that problem into a short, human-readable text. The web-GUI then
shows that text in a "Solution Description" panel next to the selected solution.

This guide explains how a description is defined, how to attach one to a problem,
and what to watch out for.

!!! Note "Where it is used"

    The NIMBUS and CUMULUS views in the web-GUI show the description panel. It
    appears whenever the problem has solution description metadata, unless the
    problem also has forest (map) metadata, in which case the map is shown
    instead.

## The idea: a template made of parts

A description is a list of
[`DescriptionPart`](https://github.com/industrial-optimization-group/DESDEO/blob/master/desdeo/api/models/problem.py)
objects. When a solution is described, each part is rendered to a string, and the
strings are joined with `separator` (a newline by default):

```python
from desdeo.api.models.problem import DescriptionPart

parts = [
    DescriptionPart(text="Investment decisions:"),
    DescriptionPart(label="  Battery capacity", symbol="E", format_spec=".1f", suffix=" kWh"),
    DescriptionPart(label="  Solar panels", symbol="n", format_spec=".0f"),
    DescriptionPart(
        label="  Solar panel cost",
        expression=["Multiply", 200, "n"],
        format_spec=".0f",
        suffix=" €",
    ),
]
```

For a solution with `E = 12.0` and `n = 8`, this renders as:

```text
Investment decisions:
  Battery capacity: 12.0 kWh
  Solar panels: 8
  Solar panel cost: 1600 €
```

The panel preserves whitespace, so leading spaces in a label indent that line.

### Fields of a part

Each part should set exactly one of `text`, `symbol` or `expression`:

| Field        | Meaning                                                                                       |
| ------------ | --------------------------------------------------------------------------------------------- |
| `text`       | Static text, included as is. `label`, `format_spec` and `suffix` are ignored.                 |
| `symbol`     | The symbol of a value in the solution (see [below](#which-values-are-available)).             |
| `expression` | A [MathJSON](../explanation/problem_format.ipynb) expression, evaluated with the solution's values. |

The remaining fields only apply to `symbol` and `expression` parts:

| Field         | Meaning                                                                                    |
| ------------- | ------------------------------------------------------------------------------------------ |
| `format_spec` | A Python [format spec](https://docs.python.org/3/library/string.html#formatspec) applied to the value, e.g. `".0f"`, `".2f"`, `",.0f"`, `".1%"`. Without it, the value is shown with `str()`. |
| `label`       | Placed before the value, followed by `": "`.                                                |
| `suffix`      | Appended right after the value, e.g. a unit such as `" kWh"`. Include the leading space yourself. |

A rendered part therefore looks like `<label>: <formatted value><suffix>`, or
`<formatted value><suffix>` when there is no label.

### Expressions

An `expression` is a MathJSON list, the same format the problem's own functions
use. Use one to show a quantity that is not itself a symbol of the problem, such
as one term of a cost:

```python
DescriptionPart(label="Battery fixed cost", expression=["Multiply", 2000, "y"], format_spec=".0f", suffix=" €")
DescriptionPart(label="Worst objective", expression=["Max", "f_1", "f_2", "f_3"], format_spec=".2f")
```

Before the expression is evaluated, every symbol in it is replaced by its numeric
value. This means symbol names that SymPy normally reserves, such as `E` or `I`,
are safe to use as long as the problem defines them.

## Which values are available

A `symbol`, or a symbol inside an `expression`, can refer to:

- decision variables,
- objectives,
- constraints,
- extra functions,
- scalarization functions,
- the problem's constants.

These are read from the solver results of the selected solution. Constants come
from the problem itself. If a symbol is both a constant and part of the solution,
the solution's value is used.

**Tensors** are expanded element by element using DESDEO's 1-based naming. A
tensor variable `x` of shape `[3]` gives `x_1`, `x_2` and `x_3`. One of shape
`[2, 3]` gives `x_1_1` … `x_2_3`. A bare tensor symbol such as `x` refers to its
first element, not to the whole tensor. To aggregate over a tensor, list its
elements explicitly:

```python
DescriptionPart(label="Peak load", expression=["Max", "x_1", "x_2", "x_3"], format_spec=".1f", suffix=" kW")
```

If the template is long, generate these lists in Python, e.g.
`["Add", *[f"x_{i}" for i in range(1, 25)]]`.

!!! Warning "Saved solutions"

    A saved solution (in NIMBUS or CUMULUS) only stores its **decision variable
    and objective values**. A part that refers to a constraint, extra function or
    scalarization function then renders as `[unknown symbol: ...]`. If saved
    solutions also need to be described, write the template in terms of
    variables, objectives and constants where possible.

## Attaching a description to a problem

There are two ways to attach a description. Neither is possible through the
"Create custom problem" screen of the web-GUI.

### Option A: in a database init script

This is the way to go when you add problems ahead of time (see
[How to solve problems with the web-GUI](./webui_solving_problems.md#adding-your-own-problems-ahead-of-time-with-a-custom-init-script)).
After storing the problem, create a `ProblemMetaDataDB` row for it if one does not
exist yet. Then add a `SolutionDescriptionMetaData` that points to it:

```python
from sqlmodel import Session, select

from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User
from desdeo.api.models.problem import DescriptionPart, ProblemMetaDataDB, SolutionDescriptionMetaData
from desdeo.api.routers.solution_description import validate_description_parts

parts = [
    DescriptionPart(label="Battery capacity", symbol="E", format_spec=".1f", suffix=" kWh"),
    DescriptionPart(label="Investment cost", symbol="f_2", format_spec=".0f", suffix=" €"),
]

# Fail early if a part refers to a symbol the problem does not have.
validate_description_parts(parts, problem)

with Session(engine) as session:
    user = session.exec(select(User).where(User.username == "analyst")).one()

    problem_db = ProblemDB.from_problem(problem, user)
    session.add(problem_db)
    session.commit()
    session.refresh(problem_db)

    metadata = ProblemMetaDataDB(problem_id=problem_db.id, problem=problem_db)
    session.add(metadata)
    session.commit()
    session.refresh(metadata)

    session.add(
        SolutionDescriptionMetaData(
            metadata_id=metadata.id,
            parts=[p.model_dump(exclude_none=True) for p in parts],
            separator="\n",
        )
    )
    session.commit()
```

Things to note:

- `parts` is stored as a JSON column, so pass **dicts** (`p.model_dump(...)`), not
  `DescriptionPart` objects.
- Inserting rows directly skips the validation that the API endpoint does, which
  is why the example calls `validate_description_parts` itself. Without it, a typo
  in a symbol only shows up when a solution is viewed. A plain `symbol` part then
  renders as `[unknown symbol: ...]`, and an `expression` part makes the request
  fail.

[`desdeo/api/db_init_summer_cabin.py`](https://github.com/industrial-optimization-group/DESDEO/blob/master/desdeo/api/db_init_summer_cabin.py)
is a complete working example. It defines a longer template with section headings,
cost breakdowns computed by expressions, and expected-value and worst-case
objectives.

### Option B: through the web-API

To attach or change the description of a problem that is already in the
database, send a POST request to `/solution-description/update_metadata`:

```json
{
  "problem_id": 3,
  "parts": [
    {"text": "Investment decisions:"},
    {"label": "  Battery capacity", "symbol": "E", "format_spec": ".1f", "suffix": " kWh"},
    {"label": "  Solar panel cost", "expression": ["Multiply", 200, "n"], "format_spec": ".0f", "suffix": " €"}
  ],
  "separator": "\n"
}
```

The endpoint checks every part against the problem first. If an expression does
not parse, or a part refers to a symbol the problem does not have, it responds
with `422` and a message naming the part. It responds with `404` if the problem
has no `ProblemMetaDataDB` row yet.

The endpoint *adds* a new `SolutionDescriptionMetaData` rather than overwriting
the old one. When a description is generated, the most recently added one is
used, so in effect, posting again replaces the description.

## Getting a description

The web-GUI does this for you. To call it yourself, send a POST request to
`/solution-description/get` with the problem and a reference to a solution
(the `state_id` of the state that produced it and the `solution_index` within
that state):

```json
{
  "problem_id": 3,
  "solution": {"state_id": 17, "solution_index": 0}
}
```

The response is `{"available": true, "description": "..."}`. If the problem has
no description metadata or the solution cannot be found, it is
`{"available": false, "description": ""}`.

## Derived problems

When CUMULUS creates a new problem from an existing one (e.g. by adding soft
constraints or uncertainty measures), the original problem's metadata, including
its solution description, is copied to the new problem. So a description written
for a base problem also describes the solutions of the problems CUMULUS derives
from it.

A template may therefore mention symbols that only the derived problem has, such
as the `E_f_1` and `robust_f_1` symbols of expected-value and worst-case
objectives. The scenario base problem in `db_init_summer_cabin.py` does this.
Such a template has to be inserted directly (Option A, without calling
`validate_description_parts` against the base problem), because
`/update_metadata` would reject the unknown symbols. Those parts show
`[unknown symbol: ...]` for solutions of the base problem itself.
