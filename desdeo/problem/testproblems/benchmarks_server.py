# A FastAPI server to expose pymoo benchmark problems
from typing import Any

import polars as pl
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from pymoo.problems import get_problem

from desdeo.problem.schema import Objective, Problem, Simulator, Url, Variable


class PymooParameters(BaseModel):
    """Parameters for a pymoo problem instance."""

    name: str
    n_var: int
    n_obj: int
    minus: bool = False


class ProblemInfo(BaseModel):
    """Information about a pymoo problem instance."""

    lower_bounds: dict[str, float]
    """Lower bounds of the decision variables. Keys are the names of the decision variables, e.g. "x_1", "x_2", etc."""
    upper_bounds: dict[str, float]
    """Upper bounds of the decision variables."""
    objective_names: list[str]


app = FastAPI()


def get_pymoo_problem(p: PymooParameters):
    """Get a pymoo problem instance by name, number of variables, and number of objectives."""
    params = p.model_dump()
    params.pop("minus")
    return get_problem(**params)


@app.get("/evaluate")
def evaluate(d: dict[str, list[float]], p: PymooParameters) -> dict[str, Any]:
    """Evaluate a pymoo problem instance with given parameters and input values."""
    problem = get_pymoo_problem(p)

    xs_df = pl.DataFrame(d)

    output = problem.evaluate(xs_df.to_numpy())
    output_df = pl.DataFrame(output, schema=[f"f_{i + 1}" for i in range(problem.n_obj)])

    return d | output_df.to_dict(as_series=False)


@app.get("/info")
def info(p: PymooParameters) -> ProblemInfo:
    """Get information about a pymoo problem instance, including bounds and objective names."""
    problem = get_pymoo_problem(p)
    bounds = problem.bounds()

    return ProblemInfo(
        lower_bounds={f"x_{i + 1}": bounds[0][i] for i in range(problem.n_var)},
        upper_bounds={f"x_{i + 1}": bounds[1][i] for i in range(problem.n_var)},
        objective_names=[f"f_{i + 1}" for i in range(problem.n_obj)],
    )


url = "http://127.0.0.1"
port = 8000


def server_problem(parameters: PymooParameters) -> Problem:
    """Create a Problem instance from pymoo parameters."""
    try:
        info = requests.get(url + f":{port}/info", json=parameters.model_dump())
        info.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError("Failed to fetch problem info. Is the server running?") from e
    info: ProblemInfo = ProblemInfo.model_validate(info.json())

    simulator_url = Url(url=f"{url}:{port}/evaluate")

    return Problem(
        name=parameters.name,
        description=f"Problem {parameters.name} with {parameters.n_var} variables and {parameters.n_obj} objectives.",
        variables=[
            Variable(
                name=f"x_{i + 1}",
                symbol=f"x_{i + 1}",
                lowerbound=info.lower_bounds[f"x_{i + 1}"],
                upperbound=info.upper_bounds[f"x_{i + 1}"],
                variable_type="real",
            )
            for i in range(parameters.n_var)
        ],
        objectives=[
            Objective(
                name=f"f_{i + 1}",
                symbol=f"f_{i + 1}",
                simulator_path=simulator_url,
                objective_type="simulator",
                maximize=parameters.minus,
            )
            for i in range(parameters.n_obj)
        ],
        simulators=[
            Simulator(
                name="s1",
                symbol="s1",
                url=simulator_url,
                parameter_options=parameters.model_dump(),
            )
        ],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
