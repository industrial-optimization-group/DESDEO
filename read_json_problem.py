from desdeo.problem.schema import Problem
from pathlib import Path

problem = Problem.load_json(Path("utopia_forest.json"))
print(problem)
