from abc import ABCMeta

from desdeo.problem.Problem import PythonProblem


class Objective(object):

    def __init__(self, name, maximized=False, ideal=None, nadir=None):
        self.name = name
        self.maximized = maximized
        self.ideal = ideal
        self.nadir = nadir

    def __call__(self, inner):
        self.inner = inner
        return self


class Constraint(object):

    def __init__(self, name):
        self.name = name

    def __call__(self, inner):
        self.inner = inner
        return self


class Variable(object):

    def __init__(self, low, high, start, name):
        self.low = low
        self.high = high
        self.start = start
        self.name = name


# Inheritance from ABC is compulsary to interoperate with it
class PorcelainProblemMeta(ABCMeta):

    def __new__(cls, name, bases, attrs):
        objs = []
        constrs = []
        vars = []
        to_drop = []
        for key, value in attrs.items():
            if isinstance(value, Objective):
                to_drop.append(key)
                objs.append((key, value))
            elif isinstance(value, Constraint):
                to_drop.append(key)
                constrs.append((key, value))
            elif isinstance(value, Variable):
                to_drop.append(key)
                vars.append((key, value))
        for key in to_drop:
            del attrs[key]
        disp_name = name
        attr_meta = attrs.pop("Meta", None)
        if attr_meta:
            meta_name = getattr(attr_meta, "name")
            if meta_name:
                disp_name = meta_name
        attrs["_porc_objs"] = objs
        attrs["_porc_constrs"] = constrs
        assert len(constrs) == 0, "Constraints not supported yet"
        attrs["_porc_vars"] = vars
        attrs["_porc_name"] = disp_name
        return type.__new__(cls, name, bases, attrs)


class PorcelainProblem(PythonProblem, metaclass=PorcelainProblemMeta):

    def __init__(self):
        from desdeo.optimization import SciPyDE
        from desdeo.problem import Variable as ProblemVariable
        from desdeo.problem.RangeEstimators import default_estimate

        super().__init__(
            nobj=len(self._porc_objs),
            nconst=len(self._porc_constrs),
            maximized=[obj.maximized for _, obj in self._porc_objs],
            objectives=[obj.name for _, obj in self._porc_objs],
            name=self._porc_name,  # Optional
        )
        for _, var in self._porc_vars:
            self.add_variables(
                ProblemVariable(
                    [var.low, var.high], starting_point=var.start, name=var.name
                )
            )
        # TODO: Use user defined ideal/nadir override for relevant dimensions
        ideal, nadir = default_estimate(SciPyDE, self)
        self.ideal = ideal
        self.nadir = nadir

    def evaluate(self, population):
        objectives = []

        for values in population:
            vals_dict = dict(zip((k for k, _ in self._porc_vars), values))
            obj_vals = []
            for _, obj in self._porc_objs:
                val = obj.inner(**vals_dict)
                obj_vals.append(-val if obj.maximized else val)
            objectives.append(obj_vals)

        return objectives
