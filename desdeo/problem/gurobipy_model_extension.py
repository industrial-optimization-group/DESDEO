'''Defines a GurobipyModel class that facilitates including extra functions and objectives to a gurobipy.Model'''

import gurobipy as gp

class GurobipyModel(gp.Model):
    _objectiveFunctions: dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr] = {}
    _extraFunctions: dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr] = {}
    _constants: dict[str, int|float] = {}

    def getExpressionByName(self, name:str) -> (
            gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr
    ):
        expression = self.getVarByName(name)
        if expression is None:
            if name in self._objectiveFunctions:
                expression = self._objectiveFunctions[name]
            elif name in self._extraFunctions:
                expression = self._extraFunctions[name]
            elif name in self._constants:
                expression = self._constants[name]
        return expression

    def addObjectiveFunction(self,
            function: (gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr),
            name:str):
        self._objectiveFunctions[name] = function

    def addExtraFunction(self,
            function: (gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr | int | float),
            name:str):
        self._extraFunctions[name] = function

    def addConstant(self, constant: int|float, name:str):
        self._constants[name] = constant

    def removeObjectiveFunction(self, name:str):
        del self._objectiveFunctions[name]

    def removeExtraFunction(self, name:str):
        del self._extraFunctions[name]

    def removeConstant(self, name:str):
        del self._constants[name]