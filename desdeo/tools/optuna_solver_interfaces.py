from pydantic import BaseModel, Field
from desdeo.problem import Problem, SympyEvaluator
from desdeo.tools.generics import BaseSolver, SolverResults
import traceback
import optuna


class OptunaOptions(BaseModel):
    """options for optuna solver
        dont increase num_jobs yet, parallel calculation"""
    budget: int = Field(description="The maximum number of allowed function evaluations.", default=50)
    """The maximum number of allowed function evaluations. Defaults to 100."""
    early_stopping_limit: float = Field(description="limit for sum consecutive samples difference", default=0.01)

_default_optuna_options = OptunaOptions()
"""The set of default options for optuna optimizer."""


def parse_optuna_results(results: dict, problem: Problem, evaluator: SympyEvaluator) -> SolverResults:
    """Parses the optimization results returned by Optuna solvers.

    Args:
        results (dict): the results. A dict with at least the keys
            `recommendation`, which points to a parametrization returned by
            nevergrad solvers, `message` with information about the optimization,
            and `success` indicating whether a recommendation was found successfully
        or not.
        problem (Problem): the problem the results belong to.
        evaluator (GenericEvaluator): the evaluator used to evaluate the problem.

    Returns:
        SolverResults: a pydantic dataclass with the relevant optimization results.
    """
    success = results["success"]

    optimal_variables = results["recommendation"]

    msg = results["message"]
    print("results:", results)
    print("optimal variables:",optimal_variables)
    results = evaluator.evaluate(optimal_variables)

    optimal_objectives = {obj.symbol: results[obj.symbol] for obj in problem.objectives}

    constraint_values = (
        {con.symbol: results[con.symbol] for con in problem.constraints} if problem.constraints is not None else None
    )
    extra_func_values = (
        {extra.symbol: results[extra.symbol] for extra in problem.extra_funcs}
        if problem.extra_funcs is not None
        else None
    )
    scalarization_values = (
        {scal.symbol: results[scal.symbol] for scal in problem.scalarization_funcs}
        if problem.scalarization_funcs is not None
        else None
    )

    return SolverResults(
        optimal_variables=optimal_variables,
        optimal_objectives=optimal_objectives,
        constraint_values=constraint_values,
        extra_func_values=extra_func_values,
        scalarization_values=scalarization_values,
        success=success,
        message=msg,
    )


class OptunaSolver(BaseSolver):
    """Creates a solver that utilizes optimizations routines found in the nevergrad library."""

    def __init__(self, problem: Problem, options: OptunaOptions | None = _default_optuna_options):
        """
        Creates a solver that utilizes optimizations routines found in the Optuna library.
        Optuna is an automatic hyperparameter optimization software framework,
        particularly designed for machine learning.
        See https://optuna.org/ for further information on Optuna

        References:
            Akiba, Takuya and Sano, Shotaro and Yanase, Toshihiko and Ohta, Takeru and Koyama, Masanori (2019).
            Optuna: A Next-Generation Hyperparameter Optimization Framework
            https://github.com/optuna/optuna

        Args:
            problem (Problem): the problem to be solved.
            options (OptunaOptions | None): options to be passes to the solver.
                If none, `_default_optuna_options` are used. Defaults to None.

        Returns:
            Callable[[str], SolverResults]: returns a callable function that takes
                as its argument one of the symbols defined for a function expression in
                problem.
        """
        self.problem = problem
        self.early_stopped = False
        self.options = options if options is not None else _default_optuna_options
        self.evaluator = SympyEvaluator(problem)

        self.result = {"recommendation": {}, "message": "init", "success": False}

    def solve(self, target: str) -> SolverResults:
        """Solve the problem for the given target.

        Args:
            target (str): the symbol of the objective function to be optimized.

        Returns:
            SolverResults: the results of the optimization.
        """

        """OPTUNA EXAMPLE FOR INCLUDING CONSTRAINTS
        https://optuna.readthedocs.io/en/stable/faq.html#how-can-i-optimize-a-model-with-some-constraints

        """
        """SILENCE THE DEBUG LOGGING"""
        # optuna.logging.set_verbosity(optuna.logging.WARNING)

        """handle constraints"""
        constraint_symbols = (
            None if self.problem.constraints is None else [con.symbol for con in self.problem.constraints]
        )

        """objective function definition and constraint addition according to Optuna documentation"""
        def optuna_objective(trial):
            xs = {
                var.symbol: trial.suggest_float(var.symbol, var.lowerbound, var.upperbound)
                for var in self.problem.variables
            }
            objective_value = self.evaluator.evaluate_target(xs, target)

            if constraint_symbols is not None:
                constraint_value = self.evaluator.evaluate_constraints(xs)
                tuple_of_constraint_values = tuple(constraint_value.values())
                """OPTUNA TAKES constraint values as tuple """
                trial.set_user_attr("constraint", tuple_of_constraint_values)

            return objective_value

        def constraints(trial):
            return trial.user_attrs["constraint"]

        """ self made early stopping in case optuna starts repeating same parameter search space
            or doesnt make significant improvement
            original N=5 can be overshoot, consider decreasing
        """

        def early_stopping_callback(study: optuna.Study, trial: optuna.Trial):
            N = 5

            if len(study.trials) > N:
                improvement = 0
                improvement_calculated = False
                for i in range(N - 2):
                    temp_list = study.trials[-N:]
                    data = temp_list[i].values
                    data2 = temp_list[i + 1].values
                    data3 = temp_list[i + 2].values
                    if data == data2 == data3:
                        improvement_calculated = True
                        improvement = 0
                        break
                    else:
                        for j in range(len(data)):
                            improvement += abs(data[j] - data2[j])
                            improvement_calculated = True

                if improvement < self.options.early_stopping_limit and improvement_calculated:
                    print("no improvement in optimization for the last 5 trials")
                    print("or last three samples were equal -> early stopping")

                    msg = "early stopping activated"
                    self.result = {"recommendation": study.trials[len(study.trials) - 1].params, "message": msg, "success": True}
                    self.early_stopped = True
                    study.stop()


        try:
            if constraint_symbols is not None:
                """sampler selection for hyperparameter space searching"""
                # sampler = optuna.samplers.NSGAIISampler(constraints_func=constraints)
                sampler = optuna.samplers.GPSampler(constraints_func=constraints)
                study = optuna.create_study(
                    directions=["minimize"],
                    sampler=sampler,
                )
            else:
                study = optuna.create_study(
                    direction="minimize")

            try:
                study.optimize(optuna_objective, n_trials=self.options.budget, callbacks=[early_stopping_callback])
            except Exception as e:
                print("⚠️ Optimization failed!")
                traceback.print_exc()

            n_trials = len(study.trials)
            if hasattr(study, "best_params"):
                print("Found best parameters:")
                msg = "best params found"
                self.result = {"recommendation": study.best_params, "message": msg, "success": True}
            else:
                msg = "using most recent trial"
                self.result = {"recommendation": study.trials[n_trials - 1].params, "message": msg, "success": True}
            # if n_trials == self.options.budget or self.early_stopped:
            #     msg = "max iterations reached or slow converge speed. using most recent trial as best"
            #     print("has attribute best_params:",hasattr(study,"best_params"))
            #     if hasattr(study,"best_params"):
            #         self.result = {"recommendation": study.best_params, "message": msg, "success": True}
            #     else:
            #         self.result = {"recommendation": study.trials[n_trials-1].params, "message": msg, "success": True}
            # else:
            #     msg = "best params found"
            #     self.result = {"recommendation": study.best_params, "message": msg, "success": True}

        except Exception as e:
            msg = f"{self.options} failed or study finalized. Possible reason: {e}"
            self.result = {"recommendation": study.trials[n_trials-1].params, "message": msg, "success": False}


        return parse_optuna_results(self.result, self.problem, self.evaluator)


