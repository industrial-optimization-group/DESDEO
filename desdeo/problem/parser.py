from functools import reduce

import polars as pl


class ParserError(Exception):
    """Raised when an error related to the MathParser class in encountered."""


class MathParser:
    """A inner class for only parsing functions in JSON file which defined as CortexJS:
    https://cortexjs.io/compute-engine/

    Arguments:
    parser (str): Names of the parser:choose (polars,pandas)
    """

    def __init__(self, parser: str = "polars"):
        # DEFINE OPERATORS
        # Whenever the OPERATORS in the json file has been altered,
        # change the name here instead of going into the environment model.

        # TRIGONOMETRIC OPERATION
        self.ARCCOS: str = "Arccos"
        self.ARCCOSH: str = "Arccosh"
        self.ARCSIN: str = "Arcsin"
        self.ARCSINH: str = "Arcsinh"
        self.ARCTAN: str = "Arctan"
        self.ARCTANH: str = "Arctanh"
        self.COS: str = "Cos"
        self.COSH: str = "Cosh"
        self.SIN: str = "Sin"
        self.SINH: str = "Sinh"
        self.TAN: str = "Tan"
        self.TANH: str = "Tanh"
        # ROUDING OPERATION
        self.ABS: str = "Abs"
        self.CEIL: str = "Ceil"
        self.FLOOR: str = "Floor"
        # EXPONENTS AND LOGARITHMS
        self.EXP: str = "Exp"
        self.LN: str = "Ln"
        self.LB: str = "Lb"
        self.LG: str = "Lg"
        self.LOP: str = "LogOnePlus"
        # BASIC OPERATORS
        self.SQRT: str = "Sqrt"
        self.SQUARE: str = "Square"
        self.NEGATE: str = "Negate"
        self.ADD: str = "Add"
        self.SUB: str = "Subtract"
        self.MUL: str = "Multiply"
        self.DIV: str = "Divide"
        self.RATIONAL: str = "Rational"
        self.POW: str = "Power"
        self.MAX: str = "Max"

        self.EQUAL: str = "Equal"
        self.GREATER: str = "Greater"
        self.GE: str = "GreaterEqual"
        self.LESS: str = "Less"
        self.LE: str = "LessEqual"
        self.NE: str = "NotEqual"
        # Environment model:
        # It provides a way to represent and track the association between variables and their corresponding
        self.env: dict = {}
        self.parser: str = parser
        if parser == "polars":
            polars_env = {
                # TRIGONOMETRIC OPERATION
                self.ARCCOS: lambda x: pl.Expr.arccos(x),  #  x ∊ [−1, 1]
                self.ARCCOSH: lambda x: pl.Expr.arccosh(x),
                self.ARCSIN: lambda x: pl.Expr.arcsin(x),
                self.ARCSINH: lambda x: pl.Expr.arcsinh(x),
                self.ARCTAN: lambda x: pl.Expr.arctan(x),  #
                self.ARCTANH: lambda x: pl.Expr.arctanh(x),  # # x ∊ [−1, 1]
                self.COS: lambda x: pl.Expr.cos(x),
                self.COSH: lambda x: pl.Expr.cosh(x),
                self.SIN: lambda x: pl.Expr.sin(x),
                self.SINH: lambda x: pl.Expr.sinh(x),
                self.TAN: lambda x: pl.Expr.tan(x),
                self.TANH: lambda x: pl.Expr.tanh(x),
                # ROUDING OPERATION
                self.ABS: lambda x: pl.Expr.abs(x),
                self.CEIL: lambda x: pl.Expr.ceil(x),  #
                self.FLOOR: lambda x: pl.Expr.floor(x),  #
                # EXPONENTS AND LOGARITHMS
                self.EXP: lambda x: pl.Expr.exp(x),
                self.LN: lambda x: pl.Expr.log(x),  # 30
                self.LB: lambda x: pl.Expr.log(x, 2),
                self.LG: lambda x: pl.Expr.log10(x),
                self.LOP: lambda x: pl.Expr.log1p(x),
                # BASIC OPERATORS
                self.SQRT: lambda x: pl.Expr.sqrt(x),
                self.SQUARE: lambda x: x**2,
                self.NEGATE: lambda x: -x,
                self.ADD: lambda lst: reduce(lambda x, y: x + y, lst),
                self.SUB: lambda lst: reduce(lambda x, y: x - y, lst),
                self.MUL: lambda lst: reduce(lambda x, y: x * y, lst),
                self.DIV: lambda lst: reduce(lambda x, y: x / y, lst),
                self.RATIONAL: lambda lst: reduce(lambda x, y: x / y, lst),
                self.POW: lambda lst: reduce(lambda x, y: x**y, lst),
                self.MAX: lambda lst: reduce(lambda x, y: pl.max(x, y), lst),
                # BOOL OPERATION
                self.EQUAL: lambda lst: reduce(lambda x, y: x == y, lst),
                self.GREATER: lambda lst: reduce(lambda x, y: x > y, lst),
                self.GE: lambda lst: reduce(lambda x, y: x >= y, lst),
                self.LESS: lambda lst: reduce(lambda x, y: x < y, lst),
                self.LE: lambda lst: reduce(lambda x, y: x <= y, lst),
                self.NE: lambda lst: reduce(lambda x, y: x != y, lst),
            }
            self.append(polars_env)
        elif parser == "pandas":
            pandas_env = {
                # TRIGONOMETRIC OPERATION
                self.ARCCOS: lambda a: "arccos(%s)" % (a),
                self.ARCCOSH: lambda a: "arccosh(%s)" % (a),  # ∀x >= 1 ,
                self.ARCSIN: lambda a: "arcsin(%s)" % (a),  # ∀ x ∊ [ − 1 , 1 ]
                self.ARCSINH: lambda a: "arcsinh(%s)" % (a),
                self.ARCTAN: lambda a: "arctan(%s)" % (a),  # ∀ x ∊ ( − 1 , 1 )
                self.ARCTANH: lambda a: "arctanh(%s)" % (a),
                self.COS: lambda a: "cos(%s)" % (a),
                self.COSH: lambda a: "cosh(%s)" % (a),
                self.SIN: lambda a: "sin(%s)" % (a),
                self.SINH: lambda a: "sinh(%s)" % (a),
                self.TAN: lambda a: "tan(%s)" % (a),
                self.TANH: lambda a: "tanh(%s)" % (a),
                # ROUDING OPERATION
                self.ABS: lambda a: "abs(%s)" % (a),
                # self.CEIL:              lambda a: 'ceil(%s)'%(a),   #Pandas.eval() not support ceil
                # self.FLOOR:             lambda a: 'floor(%s)'%(a),  #Pandas.eval() not support floor
                # EXPONENTS AND LOGARITHMS
                self.EXP: lambda a: "exp(%s)" % (a),
                self.LN: lambda a: "log(%s)" % (a),
                self.LB: lambda a: "log(%s,2)" % a,
                self.LG: lambda a: "log10(%s)" % (a),
                self.LOP: lambda a: "log1p(%s)" % (a),
                # BASIC OPERATION
                self.SQRT: lambda a: "(%s ** (1/2))" % a
                if isinstance(a, str)
                else a ** (1 / 2),
                self.SQUARE: lambda a: "(%s ** (2))" % a
                if isinstance(a, str)
                else a ** (2),
                self.NEGATE: lambda a: "(-%s)" % a,
                self.ADD: lambda lst: reduce(
                    lambda x, y: "(%s +  %s)" % (x, y)
                    if isinstance(x, str) or isinstance(y, str)
                    else x + y,
                    lst,
                ),
                self.SUB: lambda lst: reduce(
                    lambda x, y: "(%s -  %s)" % (x, y)
                    if isinstance(x, str) or isinstance(y, str)
                    else x - y,
                    lst,
                ),
                self.MUL: lambda lst: reduce(
                    lambda x, y: "(%s *  %s)" % (x, y)
                    if isinstance(x, str) or isinstance(y, str)
                    else x * y,
                    lst,
                ),
                self.DIV: lambda lst: reduce(
                    lambda x, y: "(%s /  %s)" % (x, y)
                    if isinstance(x, str) or isinstance(y, str)
                    else x / y,
                    lst,
                ),
                self.RATIONAL: lambda lst: reduce(
                    lambda x, y: "(%s /  %s)" % (x, y)
                    if isinstance(x, str) or isinstance(y, str)
                    else x / y,
                    lst,
                ),
                self.POW: lambda lst: reduce(
                    lambda x, y: "(%s**  %s)" % (x, y)
                    if isinstance(x, str) or isinstance(y, str)
                    else x**y,
                    lst,
                ),
                # self.MAX:                lambda lst:reduce(lambda a,b:'where(%s,%s)'%(a,b), lst),    # Max function is not supported in pandas.eval()
                # BOOL OPERATION
                self.EQUAL: lambda a, b: "(%s == %s)" % (a, b),
                self.GREATER: lambda a, b: "(%s >  %s)" % (a, b),
                self.GE: lambda a, b: "(%s >= %s)" % (a, b),
                self.LESS: lambda a, b: "(%s <  %s)" % (a, b),
                self.LE: lambda a, b: "(%s <= %s)" % (a, b),
                self.NE: lambda a, b: "(%s != %s)" % (a, b),
            }
            self.append(pandas_env)
        else:
            msg = "incorrect parser"
            raise ParserError(msg)
        # DEFINE KEYWORDS
        # Whenever the keyword in the json file has been altered,
        # change the name here instead of going into the functions.
        self.CONSTANTS: str = "constants"
        self.VARIABLES: str = "variables"
        self.EXTRA: str = "extra_func"
        self.OBJECTIVES: str = "objectives"
        self.CONSTRAINTS: str = "constraints"
        self.NAME: str = "shortname"
        self.VALUE: str = "value"
        self.FUNC: str = "func"
        self.LB: str = "lowerbound"
        self.UB: str = "upperbound"
        self.TYPE: str = "type"
        self.IV: str = "initialvalue"
        self.MAX: str = "max"

        # #CREATE MATH PARSER
        # self.parser = self.MathParser(parser=parser)

        # #GET DESDEO PROBLEM
        # variables,objectives,constraints = \
        # self.json_to_problem(json_data)
        # super().__init__(objectives, variables, constraints)

    def __get_parser_name__(self):
        return self.parser

    def append(self, d: dict):
        self.env.update(d)

    def replace_str(self, lst, target: str, sub) -> list:
        """Replace a target in list with a substitution

        Example
        replace_str("["Max", "g_i", ["Add","g_i","f_i"]]]", "_i", "_1") --->
        ["Max", "g_1", ["Add","g_1","f_1"]]]
        """
        if isinstance(lst, list):
            return [self.replace_str(item, target, sub) for item in lst]
        elif isinstance(lst, str):
            if target in lst:
                if isinstance(sub, str):
                    s = lst.replace(target, sub)
                    return s
                else:
                    return sub
            else:
                return lst
        else:
            return lst

    def parse_sum(self, expr):
        """Convert Sum Operation into Add Operation

        Example:
        parse_sum(" ["Sum", ["Max", "g_i", 0], ["Triple", ["Hold", "i"], 1, 3]]" ) --->
        ["Add", ["Max", "g_1", 0],["Max", "g_2", 0],["Max", "g_3", 0] ]
        """
        if not expr or len(expr) != 3:
            msg = "The Sum Expression List is either empty or wrong format"
            raise ParserError(msg)

        # GET ITERATER
        logic_list = expr[2]
        if logic_list[0] != "Triple":
            msg = "The Control Operation is not recognizable, No keyword: Triple is not found "
            raise ParserError(msg)
        hold_list = logic_list[1]
        if hold_list[0] != "Hold":
            msg = (
                "The Control Operation is not recognizable,No keyword:Hold is not found"
            )
            raise ParserError(msg)
        holder: str = hold_list[1]
        start = logic_list[2]
        end = logic_list[3]

        # REPLACE ITERATER IN EXPRESSION WITH HODLER
        expr = expr[1]
        pl_list = []
        for i in range(start, end + 1):
            it_name = "_" + holder
            new_it = "_" + str(i)
            l = self.replace_str(expr, it_name, new_it)
            pl_list.append(l)
        new_expr = ["Add"]
        for e in pl_list:
            new_expr.append(e)
        return new_expr

    def parse(self, expr):
        """
        it will parse Polish Notation, and return polars expression.
        Arguments:
            expr, It is a Polish notation that describe a function in list e.g.
            ["Multiply", ["Sqrt", 2], "x2"]
        Raises:
            ParserError: If the type of the text neither str,list nor int,float, it will
            raise type error; If the operation in expr not found, it means we currently
            don't support such function operation.
        """
        if expr is None:
            return expr
        if isinstance(expr, str):
            # Handle variable symbols
            if expr in self.env:
                return self.parse(self.env[expr])
            else:
                if self.__get_parser_name__() == "polars":
                    return pl.col(expr)
                elif self.__get_parser_name__() == "pandas":
                    return expr
                else:
                    msg = "incorrect parser"
                    raise ParserError(msg)
        elif isinstance(expr, (int, float)):
            # Handle numeric constants
            return expr
        elif isinstance(expr, list):
            # Handle function expressions
            op = expr[0]
            operands = expr[1:]
            length = len(operands)
            if op in self.env:
                if length == 1:
                    return self.env[op](self.parse(expr[1]))
                elif length > 1:
                    return self.env[op](self.parse(e) for e in operands)
            elif op == "Sum":
                new_expr = self.parse_sum(expr)
                return self.parse(new_expr)
            else:
                # raise error message:
                msg = f"I am sorry the operator:{op} is not found."
                raise ParserError(msg)
        else:
            # raise error message:
            text_type = type(expr)
            msg = f"The type of {text_type} is not found."
            raise ParserError(msg)

    """SHOULD BE CHANGED TO JSON TO DATACLASS THAT MIMICS THE JSON FORMAT
    def json_to_problem(self, json_data: dict):
        """ """
        it will parse json data that decribe in multi-objective optimization format.
        , and return desdeo Variables, Objectives, and Constraints.

        Arguments:
            json_data(dict), it is a json file that contains muti-objective optimization
            information. 
        Raises:
            ParserError:
        """ """

        #GET DATA FROM JSON
        constants_list      = json_data[self.CONSTANTS]
        variables_list      = json_data[self.VARIABLES]
        extra_func          = json_data[self.EXTRA]
        objectives_list     = json_data[self.OBJECTIVES]
        constraints_list    = json_data[self.CONSTRAINTS]
        #VARIABLES AND OBJECTIVES ARE MANDITORY
        if not variables_list :
            msg = ("Decision Variable is empty.")
            raise ParserError(msg)
        if not objectives_list:
            msg = ("Objective Functions is empty.")
            raise ParserError(msg)
        
        #CONSTANTS     
        constants = {}
        if constants_list:
            for d in constants_list:
                name = d[self.NAME]
                value = d[self.VALUE]
                constants[name] = value
            #UPDATE PARSER ENVIRONMENT
            self.append(constants)
        
        #DESDEO VARIABLES
        desdeo_vars = []
        for d in variables_list:
            name = d[self.NAME] 
            lower_bound = self.parse(d[self.LB])           
            upper_bound = self.parse(d[self.UB])
            var_type = d[self.TYPE]
            initial_value = d[self.IV] 
            if initial_value is None: initial_value = (lower_bound+upper_bound)/2
            desdeo_var = Variable(name, 
                            initial_value,
                            lower_bound,
                            upper_bound,
                            var_type)
            desdeo_vars.append(desdeo_var)

        #FUNCTIONS THAT NEED BEFORE OBJECTIVES AND CONSTAINTS 
        extra_funcs = {}            
        if extra_func:
            for f in extra_func:
                name = f[self.NAME]
                expr = f[self.FUNC]
                extra_funcs[name] = expr
            #UPDATE PARSER ENVIRONMENT
            self.append(extra_funcs)

        #DESDEO OBJECTIVES
        desdeo_objs = []
        for obj in objectives_list:
            name = obj[self.NAME]
            lower_bound = self.parse(obj[self.LB])
            upper_bound = self.parse(obj[self.UB])

            is_maximize = obj[self.MAX]
            polars_func = self.parse(obj[self.FUNC])
            if lower_bound is None: lower_bound = -np.inf
            if upper_bound is None: upper_bound = np.inf
            desdeo_obj = ScalarObjective(name,polars_func,lower_bound,upper_bound,
                                 maximize=[is_maximize])
            desdeo_objs.append(desdeo_obj)

        #DESDEO CONSTRAINTS
        desdeo_csts = []
        if constraints_list:
            for cst in constraints_list:
                name = cst[self.NAME]  
                polars_func = self.parse(cst[self.FUNC])   
                desdeo_cst = ScalarConstraint(name,len(variables_list),len(objectives_list),
                                    polars_func)
                desdeo_csts.append(desdeo_cst)   
        return desdeo_vars,desdeo_objs,desdeo_csts
"""


math_parser = MathParser()
test1 = [
    "Add",
    ["Divide", ["Multiply", -7.735, ["Square", "x_1"]], "x_2"],
    ["Multiply", "x_1", "x_3"],
    -180,
]

expr = math_parser.parse(expr=test1)
print(expr)

data = pl.DataFrame({"x_1": [20, 30], "x_2": [5, 7], "x_3": [60, 21]})

objectives = data.select(expr.alias("Objective 1"))
print(objectives)
