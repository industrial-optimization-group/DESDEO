"""Defines a GurobipyModel class that facilitates storing extra functions and objectives in a gurobipy.Model"""

import gurobipy as gp

class GurobipyModel(gp.Model):
    objectiveFunctions: dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr] = {}
    scalarizations: dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr] = {}
    extraFunctions: dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr | int | float] = {}
    constants: dict[str, int|float] = {}

    def getExpressionByName(self, name:str) -> (
            gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr | int | float
    ):
        expression = self.getVarByName(name)
        if expression is None:
            if name in self.objectiveFunctions:
                expression = self.objectiveFunctions[name]
            elif name in self.scalarizations:
                expression = self.scalarizations[name]
            elif name in self.extraFunctions:
                expression = self.extraFunctions[name]
            elif name in self.constants:
                expression = self.constants[name]
        return expression

    def addObjectiveFunction(self,
            function: (gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr),
            name:str):
        self.objectiveFunctions[name] = function

    def addScalarization(self,
            function: (gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr),
            name:str):
        self.scalarizations[name] = function

    def addExtraFunction(self,
            function: (gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr | int | float),
            name:str):
        self.extraFunctions[name] = function

    def addConstant(self, constant: int|float, name:str):
        self.constants[name] = constant

    def removeObjectiveFunction(self, name:str):
        del self.objectiveFunctions[name]

    def removeScalarization(self, name:str):
        del self.scalarizations[name]

    def removeExtraFunction(self, name:str):
        del self.extraFunctions[name]

    def removeConstant(self, name:str):
        del self.constants[name]