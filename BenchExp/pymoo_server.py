# A FastAPI server to expose pymoo benchmark problems

# lru
from functools import lru_cache
from typing import Any

import polars as pl
from fastapi import FastAPI
from pydantic import BaseModel
from pymoo.problems import get_problem


class PymooParameters(BaseModel):
    name: str
    n_vars: int = 2
    n_objs: int = 2


app = FastAPI()


def get_pymoo_problem(name: str, n_vars: int, n_objs: int):
    """
    Get a pymoo problem instance by name, number of variables, and number of objectives.
    """
    print(name, type(n_vars), type(n_objs))
    problem = get_problem(name, n_vars=n_vars, n_objs=n_objs)
    return problem


@app.get("/evaluate")
def evaluate(d: dict[str, list[float]], p: PymooParameters) -> dict[str, Any]:
    """
    Evaluate a pymoo problem instance with given parameters and input values.
    """
    problem = get_pymoo_problem(p.name, p.n_vars, p.n_objs)

    xs_df = pl.DataFrame(d)

    output = problem.evaluate(xs_df.to_numpy())
    output_df = pl.DataFrame(output, schema=[f"f_{i+1}" for i in range(problem.n_obj)])

    return d | output_df.to_dict(as_series=False)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
