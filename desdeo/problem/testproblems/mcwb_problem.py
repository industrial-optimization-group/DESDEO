from desdeo.problem.schema import (
    Constraint,
Constant,
    ConstraintTypeEnum,
    ExtraFunction,
    Objective,
    Problem,
    Variable,
    VariableTypeEnum,
)

"""
This script defines multi-objective optimization problems for cantilever welded beams 
using various cross-section types. The problems aim to minimize the total cost of 
weld and beam construction while ensuring the structural integrity of the beam 
by considering constraints related to stress and deflection.

Each problem represents a specific configuration of a cantilever beam, and includes:
- Variables (e.g., dimensions of the beam and weld),
- Constants (e.g., material properties),
- Extra functions (e.g., derived calculations for area, moment of inertia),
- Objectives (e.g., minimizing cost and deflection),
- Constraints (e.g., shear stress, buckling, and geometric constraints).

Returns:
    Problem: A DESDEO problem instance representing the multi-objective optimization problem.
"""

CONSTANTS = [
    Constant(name="P", symbol="P", value=30000),  # Load [N]
    Constant(name="L", symbol="L", value=0.5),  # Beam length [m]
    Constant(name="E", symbol="E", value=200e9),  # Young's modulus [Pa]
    Constant(name="tau_max", symbol="tau_max", value=95e6),  # Max shear stress [Pa]
    Constant(name="sigma_max", symbol="sigma_max", value=200e6),  # Max normal stress [Pa]
    Constant(name="C_w", symbol="C_w", value=209600),  # Welding cost factor [$/m^3]
    Constant(name="steel_cost", symbol="C_s", value=0.7),  # Price of HRC steel [$/kg]
    Constant(name="steel_density", symbol="rho_s", value=7850),  # Steel density [kg/m^3]
    Constant(name="C_b", symbol="C_b", value=0.7 * 7850),  # Beam material cost factor [$/m^3]
    Constant(name="K", symbol="K", value=2),  # Cantilever beam coefficient
    Constant(name="pi", symbol="pi", value=3.141592653589793),
    Constant(name="delta_t", symbol="delta_t", value=0.05 - 0.005),
]

EXTRAFUNCTION = [
    ExtraFunction(name="weld_cost", symbol="W_c", func="C_w * x_1**2 * x_2"),  # Weld cost
    ExtraFunction(name="beam_cost", symbol="B_c", func="C_b * A * (L + x_2)"),  # Beam cost
    ExtraFunction(name="polar_moment", symbol="J",
                  func="2 * ((2**(1/2))/2 * x_1 * x_2 * (x_2**2 / 12 + ((x_1 + x_3) / 2) ** 2))"),  # J calculation
    ExtraFunction(name="effective_radius", symbol="R", func="((x_2**2 / 4) + ((x_3 + x_1) / 2) ** 2) ** (1/2)"),
    # R calculation
    ExtraFunction(name="bending_moment", symbol="M", func="P * (L + x_2 / 2)"),  # M calculation
    ExtraFunction(name="primary_shear_stress", symbol="tau_1", func="P / ((2**(1/2)) * x_1 * x_2)"),
    # tau_1 calculation
    ExtraFunction(name="torsional_stress", symbol="tau_2", func="M * R / J"),  # tau_2 calculation
    ExtraFunction(name="cos_theta", symbol="c_theta", func="x_2 / (2 * R)"),
    ExtraFunction(name="combined_shear", symbol="tau",
                  func="(tau_1**2 + (2 * tau_1 * tau_2 * c_theta) + tau_2**2) ** (1/2)"),
    # Combined shear stress
    ExtraFunction(name="bending_stress", symbol="sigma_x", func="P * L * x_3 / (2 * I_x)"),  # sigma_x calculation
    ExtraFunction(name="critical_buckling", symbol="P_c", func="(pi**2 * E * I_x) / (K * L)**2"),  # P_c calculation
]

OBJECTIVES = [
    Objective(name="f_1", symbol="f_1", func="W_c + B_c", maximize=False),  # Minimize total cost
    Objective(name="f_2", symbol="f_2", func="P * L**3 / (3 * E * I_x)", maximize=False),  # Minimize beam deflection
]

CONSTRAINTS = [
    Constraint(name="g_1", symbol="g_1", cons_type=ConstraintTypeEnum.LTE, func="(1 / tau_max) * (tau - tau_max)"), # Shear stress
    Constraint(name="g_2", symbol="g_2", cons_type=ConstraintTypeEnum.LTE,
                   func="(1 / sigma_max) * (sigma_x - sigma_max)"),  # Normal stress
    Constraint(name="g_3", symbol="g_3", cons_type=ConstraintTypeEnum.LTE, func="(1 / P) * (P - P_c)"), # Buckling constraint
]

def mcwb_solid_rectangular_problem() -> Problem:
    r"""Defines the multi-objective cantilever welded beam (MCWB) optimization problem.

    The objective functions and constraints for the MCWB design problem are defined as follows:

    Objectives:
    1. Minimize the total cost, \( f_1 = W_c + B_c \), where \( W_c \) is the weld cost and \( B_c \) is the beam cost.
    2. Minimize the deflection of the beam, \( f_2 = \frac{P L^3}{3 E I_x} \), where \( P \) is the applied load, \( L \) is the beam length, \( E \) is the Young's modulus, and \( I_x \) is the moment of inertia.

    Constraints:
    1. Shear stress constraint: \( \tau \leq \tau_{max} \), where \( \tau \) is the combined shear stress and \( \tau_{max} \) is the maximum shear stress.
    2. Normal stress constraint: \( \sigma_x \leq \sigma_{max} \), where \( \sigma_x \) is the bending stress and \( \sigma_{max} \) is the maximum allowable normal stress.
    3. Buckling constraint: \( P \leq P_c \), where \( P_c \) is the critical buckling load.
    4. Weld height constraint: \( x_1 \leq x_4 \), ensuring that the weld height \( x_1 \) is less than or equal to the flange thickness \( x_4 \).

    Where:
    - \( x_1 \) is the weld height.
    - \( x_2 \) is the weld length.
    - \( x_3 \) is the beam height.
    - \( x_4 \) is the beam width.

    The parameters are defined as:
    - \( P = 30000 \, \text{N} \) (load),
    - \( L = 0.5 \, \text{m} \) (beam length),
    - \( E = 200 \times 10^9 \, \text{Pa} \) (Young's modulus),
    - \( \tau_{max} = 95 \times 10^6 \, \text{Pa} \) (max shear stress),
    - \( \sigma_{max} = 200 \times 10^6 \, \text{Pa} \) (max normal stress),
    - \( C_w = 209600 \, \text{\$/m}^3 \) (welding cost factor),
    - \( C_s = 0.7 \, \text{\$/kg} \) (price of HRC steel),
    - \( \rho_s = 7850 \, \text{kg/m}^3 \) (steel density),
    - \( C_b = 0.7 \times 7850 \, \text{\$/m}^3 \) (beam material cost factor),
    - \( K = 2 \) (cantilever beam coefficient),
    - \( \pi = 3.141592653589793 \) (constant for calculations),
    - \( \delta_t = 0.045 \) (tolerance factor for calculations).

    Returns:
        Problem: An instance of the multi-objective cantilever welded beam optimization problem.
    """
    # Variables
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0.005, upperbound=0.15),  # height of weld
        Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.3),  # length of weld
        Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.3),  # height of beam
        Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.15),  # width of beam
        ]

    # Constants
    constants = CONSTANTS

    # Extra Functions (Intermediate Calculations)
    extra_functions = [
        ExtraFunction(name="cross_section_area", symbol="A", func="x_3 * x_4"),  # A = h * b
        ExtraFunction(name="moment_of_inertia", symbol="I_x", func="(x_4 * x_3**3) / 12"),# I_x = (b * h³) / 12
    ] + EXTRAFUNCTION

    # Objectives (minimize cost, minimize deflection)
    objectives = OBJECTIVES

    # NO DUMMY CONSTRAINTS
    # Constraints
    constraints = CONSTRAINTS + [
        Constraint(
            name="g_4", symbol="g_4", cons_type=ConstraintTypeEnum.LTE,
            func="(x_1 - x_4) / (0.25 - 0.005)"  # Ensures x_1 <= x_4 (weld height <= flange thickness)
        )
    ]

    return Problem(
        name="MCWB Solid Rectangular",
        description="Multi-objective optimization of a welded beam using a solid rectangular cross-section.",
        constants=constants,
        variables=variables,
        extra_funcs=extra_functions,
        objectives=objectives,
        constraints=constraints,
    )

def mcwb_hollow_rectangular_problem() -> Problem:
    r"""Defines the multi-objective cantilever welded beam (MCWB) optimization problem using a hollow rectangular cross-section.

    The objective functions and constraints for the MCWB design problem are defined as follows:

    Objectives:
    1. Minimize the total cost, \( f_1 = W_c + B_c \), where \( W_c \) is the weld cost and \( B_c \) is the beam cost.
    2. Minimize the deflection of the beam, \( f_2 = \frac{P L^3}{3 E I_x} \), where \( P \) is the applied load, \( L \) is the beam length, \( E \) is the Young's modulus, and \( I_x \) is the moment of inertia.

    Constraints:
    1. Shear stress constraint: \( \tau \leq \tau_{max} \), where \( \tau \) is the combined shear stress and \( \tau_{max} \) is the maximum shear stress.
    2. Normal stress constraint: \( \sigma_x \leq \sigma_{max} \), where \( \sigma_x \) is the bending stress and \( \sigma_{max} \) is the maximum allowable normal stress.
    3. Buckling constraint: \( P \leq P_c \), where \( P_c \) is the critical buckling load.
    4. Weld height constraint: \( x_1 \leq x_4 \), ensuring that the weld height \( x_1 \) is less than or equal to the flange thickness \( x_4 \).
    5. Wall thickness constraint: \( t \geq h \), where \( t \) is the wall thickness and \( h \) is the outer height.

    Where:
    - \( x_1 \) is the weld height.
    - \( x_2 \) is the weld length.
    - \( x_3 \) is the outer height of the beam.
    - \( x_4 \) is the outer width of the beam.
    - \( x_5 \) is the wall thickness of the hollow beam.

    The parameters are defined as:
    - \( P = 30000 \, \text{N} \) (load),
    - \( L = 0.5 \, \text{m} \) (beam length),
    - \( E = 200 \times 10^9 \, \text{Pa} \) (Young's modulus),
    - \( \tau_{max} = 95 \times 10^6 \, \text{Pa} \) (max shear stress),
    - \( \sigma_{max} = 200 \times 10^6 \, \text{Pa} \) (max normal stress),
    - \( C_w = 209600 \, \text{\$/m}^3 \) (welding cost factor),
    - \( C_s = 0.7 \, \text{\$/kg} \) (price of HRC steel),
    - \( \rho_s = 7850 \, \text{kg/m}^3 \) (steel density),
    - \( C_b = 0.7 \times 7850 \, \text{\$/m}^3 \) (beam material cost factor),
    - \( K = 2 \) (cantilever beam coefficient),
    - \( \pi = 3.141592653589793 \) (constant for calculations),
    - \( \delta_t = 0.045 \) (tolerance factor for calculations).

    Returns:
        Problem: An instance of the multi-objective cantilever welded beam optimization problem using a hollow rectangular cross-section.
    """
    # Constants
    constants = CONSTANTS

    # Variables
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0.005, upperbound=0.15),  # weld height
        Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.3),   # weld length
        Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.3),   # outer height
        Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.15),  # outer width
        Variable(name="x_5", symbol="x_5", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.03),  # wall thickness
    ]

    # Extra Functions
    extra_functions = [
        ExtraFunction(
            name="cross_section_area", symbol="A",
            func="(x_4 * x_3) - ((x_4 - 2*x_5) * (x_3 - 2*x_5))"
        ),
        ExtraFunction(
            name="moment_of_inertia", symbol="I_x",
            func="((x_4 * x_3**3)/12) - (((x_4 - 2*x_5) * (x_3 - 2*x_5)**3)/12)"
        )
    ] + EXTRAFUNCTION

    # Objectives
    objectives = OBJECTIVES

    # Constraints
    constraints = CONSTRAINTS + [Constraint(
        name="g_4", symbol="g_4", cons_type=ConstraintTypeEnum.LTE,
        func="(x_1 - x_4) / (0.25 - 0.005)"
        ),
        Constraint(
            name="g_5", symbol="g_5", cons_type=ConstraintTypeEnum.LTE,
            func="(x_4 - x_3) / (0.25 - 0.005)"  # Ensures t >= h
        )
    ]

    return Problem(
        name="MCWB Hollow Rectangular",
        description="Multi-objective optimization of a welded beam with hollow rectangular cross-section.",
        constants=constants,
        variables=variables,
        extra_funcs=extra_functions,
        objectives=objectives,
        constraints=constraints,
    )

def mcwb_equilateral_tbeam_problem() -> Problem:
    r"""Defines the multi-objective cantilever welded beam (MCWB) optimization problem using an equilateral T-beam cross-section.

    The objective functions and constraints for the MCWB design problem are defined as follows:

    Objectives:
    1. Minimize the total cost, \( f_1 = W_c + B_c \), where \( W_c \) is the weld cost and \( B_c \) is the beam cost.
    2. Minimize the deflection of the beam, \( f_2 = \frac{P L^3}{3 E I_x} \), where \( P \) is the applied load, \( L \) is the beam length, \( E \) is the Young's modulus, and \( I_x \) is the moment of inertia.

    Constraints:
    1. Shear stress constraint: \( \tau \leq \tau_{max} \), where \( \tau \) is the combined shear stress and \( \tau_{max} \) is the maximum shear stress.
    2. Normal stress constraint: \( \sigma_x \leq \sigma_{max} \), where \( \sigma_x \) is the bending stress and \( \sigma_{max} \) is the maximum allowable normal stress.
    3. Buckling constraint: \( P \leq P_c \), where \( P_c \) is the critical buckling load.
    4. Weld height constraint: \( x_1 \leq x_4 \), ensuring that the weld height \( x_1 \) is less than or equal to the flange/web thickness \( x_4 \).
    5. Flange thickness constraint: \( x_4 \geq x_3 \), ensuring that the flange thickness \( x_4 \) is greater than or equal to the beam height \( x_3 \).

    Where:
    - \( x_1 \) is the weld height.
    - \( x_2 \) is the weld length.
    - \( x_3 \) is the beam height.
    - \( x_4 \) is the beam thickness (flange/web thickness).

    The parameters are defined as:
    - \( P = 30000 \, \text{N} \) (load),
    - \( L = 0.5 \, \text{m} \) (beam length),
    - \( E = 200 \times 10^9 \, \text{Pa} \) (Young's modulus),
    - \( \tau_{max} = 95 \times 10^6 \, \text{Pa} \) (max shear stress),
    - \( \sigma_{max} = 200 \times 10^6 \, \text{Pa} \) (max normal stress),
    - \( C_w = 209600 \, \text{\$/m}^3 \) (welding cost factor),
    - \( C_s = 0.7 \, \text{\$/kg} \) (price of HRC steel),
    - \( \rho_s = 7850 \, \text{kg/m}^3 \) (steel density),
    - \( C_b = 0.7 \times 7850 \, \text{\$/m}^3 \) (beam material cost factor),
    - \( K = 2 \) (cantilever beam coefficient),
    - \( \pi = 3.141592653589793 \) (constant for calculations),
    - \( \delta_t = 0.045 \) (tolerance factor for calculations).

    Returns:
        Problem: An instance of the multi-objective cantilever welded beam optimization problem using an equilateral T-beam cross-section.
    """
    # Variables
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0.005, upperbound=0.25),  # weld height
        Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.3),  # weld length
        Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.25),  # beam height
        Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real, lowerbound=0.005, upperbound=0.25),  # beam thickness (flange/web thickness)
    ]

    # Constants
    constants = CONSTANTS

    # Extra Functions (Intermediate Calculations)
    extra_functions = [
          ExtraFunction(
              name="cross_section_area", symbol="A",
              func="x_4 * x_3 + (x_3 - x_4) * x_4"  # t * h + (h - t) * t
          ),
          ExtraFunction(
              name="moment_of_inertia", symbol="I_x",
              func="(x_4 * x_3 ** 3) / 12 + ((x_3 - x_4) * x_4 ** 3) / 12"
          )
    ] + EXTRAFUNCTION

    # Objectives (minimize cost, minimize deflection)
    objectives = OBJECTIVES

    # Constraints
    constraints = CONSTRAINTS + [
        Constraint(
            name="g_4", symbol="g_4", cons_type=ConstraintTypeEnum.LTE,
            func="(x_1 - x_4) / (0.25 - 0.005)"  # weld height <= flange thickness
        ),
        Constraint(
            name="g_5", symbol="g_5", cons_type=ConstraintTypeEnum.LTE,
            func="(x_4 - x_3) / (0.25 - 0.005)"  # flange thickness >= beam height
        )
    ]

    return Problem(
        name="MCWB Equilateral T-Beam",
        description="Multi-objective optimization of a welded T-beam with an equilateral cross-section.",
        constants=constants,
        variables=variables,
        extra_funcs=extra_functions,
        objectives=objectives,
        constraints=constraints,
    )

def mcwb_square_channel_problem() -> Problem:
    r"""Defines the multi-objective cantilever welded beam (MCWB) optimization problem using a square channel cross-section.

    The objective functions and constraints for the MCWB design problem are defined as follows:

    Objectives:
    1. Minimize the total cost, \( f_1 = W_c + B_c \), where \( W_c \) is the weld cost and \( B_c \) is the beam cost.
    2. Minimize the deflection of the beam, \( f_2 = \frac{P L^3}{3 E I_x} \), where \( P \) is the applied load, \( L \) is the beam length, \( E \) is the Young's modulus, and \( I_x \) is the moment of inertia.

    Constraints:
    1. Weld height constraint: \( x_1 \leq x_4 \), ensuring that the weld height \( x_1 \) is less than or equal to the flange thickness \( x_4 \).
    2. Beam width constraint: \( x_4 \geq x_3 \), ensuring that the beam width \( x_4 \) is greater than or equal to the beam height \( x_3 \).
    3. Web thickness constraint: \( x_6 \geq \frac{x_3}{2} \), ensuring that the web thickness \( x_6 \) is greater than or equal to half the beam height \( x_3 \).
    4. Flange thickness constraint: \( x_5 \geq x_4 \), ensuring that the flange thickness \( x_5 \) is greater than or equal to the beam width \( x_4 \).

    Where:
    - \( x_1 \) is the weld height.
    - \( x_2 \) is the weld length.
    - \( x_3 \) is the beam height.
    - \( x_4 \) is the beam width.
    - \( x_5 \) is the flange thickness.
    - \( x_6 \) is the web thickness.

    The parameters are defined as:
    - \( P = 30000 \, \text{N} \) (load),
    - \( L = 0.5 \, \text{m} \) (beam length),
    - \( E = 200 \times 10^9 \, \text{Pa} \) (Young's modulus),
    - \( \tau_{max} = 95 \times 10^6 \, \text{Pa} \) (max shear stress),
    - \( \sigma_{max} = 200 \times 10^6 \, \text{Pa} \) (max normal stress),
    - \( C_w = 209600 \, \text{\$/m}^3 \) (welding cost factor),
    - \( C_s = 0.7 \, \text{\$/kg} \) (price of HRC steel),
    - \( \rho_s = 7850 \, \text{kg/m}^3 \) (steel density),
    - \( C_b = 0.7 \times 7850 \, \text{\$/m}^3 \) (beam material cost factor),
    - \( K = 2 \) (cantilever beam coefficient),
    - \( \pi = 3.141592653589793 \) (constant for calculations),
    - \( \delta_t = 0.045 \) (tolerance factor for calculations).

    Returns:
        Problem: An instance of the multi-objective cantilever welded beam optimization problem using a square channel cross-section.
    """
    # Variables
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0.0005, upperbound=0.15),  # weld height (a)
        Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.3),  # weld length (l)
        Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.25),  # beam height (h)
        Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.15),  # beam width (b)
        Variable(name="x_5", symbol="x_5", variable_type=VariableTypeEnum.real, lowerbound=0.0075, upperbound=0.03),  # flange thickness (t)
        Variable(name="x_6", symbol="x_6", variable_type=VariableTypeEnum.real, lowerbound=0.0075, upperbound=0.03),  # web thickness (u)
    ]

    # Constants
    constants = CONSTANTS

    # Extra Functions (Intermediate Calculations)
    extra_functions = [
        ExtraFunction(
            name="cross_section_area", symbol="A",
            func="(x_3 * x_4) - ((x_4 - x_5) * (x_3 - 2 * x_6))"
        ),
        ExtraFunction(
            name="moment_of_inertia", symbol="I_x",
            func="(x_4 * x_3 ** 3) / 12 - ((x_4 - x_5) * (x_3 - 2 * x_6) ** 3) / 12"
        )
    ] + EXTRAFUNCTION

    # Objectives (minimize cost, minimize deflection, etc.)
    objectives = OBJECTIVES

    # Constraints
    constraints = CONSTRAINTS + [
        # Weld height constraint (g_4)
        Constraint(
            name="g_4", symbol="g_4", cons_type=ConstraintTypeEnum.LTE,
            func="(x_1 - x_4) / (0.15 - 0.0075)"  # weld height <= flange thickness
        ),
        # Beam width >= weld height (g_5)
        Constraint(
            name="g_5", symbol="g_5", cons_type=ConstraintTypeEnum.LTE,
            func="(x_4 - x_3) / (0.25 - 0.0075)"  # beam width >= beam height
        ),
        # Cross-section geometric constraints (g_6 and g_7)
        Constraint(
            name="g_6", symbol="g_6", cons_type=ConstraintTypeEnum.LTE,
            func="(x_6 - x_3 / 2) / (0.03 - 0.0075)"
            # web thickness must be greater than half the beam height (normalized)
        ),
        Constraint(
            name="g_7", symbol="g_7", cons_type=ConstraintTypeEnum.LTE,
            func="(x_5 - x_4) / (0.03 - 0.0075)"  # flange thickness >= beam width
        )
    ]

    return Problem(
        name="MCWB Square Channel",
        description="Multi-objective optimization of a welded square channel beam with constraints on geometry and load-bearing capacity.",
        constants=constants,
        variables=variables,
        extra_funcs=extra_functions,
        objectives=objectives,
        constraints=constraints,
    )

def mcwb_tapered_channel_problem() -> Problem:
    r"""Defines the multi-objective cantilever welded beam (MCWB) optimization problem using a tapered channel cross-section.

    The objective functions and constraints for the MCWB design problem are defined as follows:

    Objectives:
    1. Minimize the total cost, \( f_1 = W_c + B_c \), where \( W_c \) is the weld cost and \( B_c \) is the beam cost.
    2. Minimize the deflection of the beam, \( f_2 = \frac{P L^3}{3 E I_x} \), where \( P \) is the applied load, \( L \) is the beam length, \( E \) is the Young's modulus, and \( I_x \) is the moment of inertia.

    Constraints:
    1. Weld height constraint: \( x_1 \leq x_5 \), ensuring that the weld height \( x_1 \) is less than or equal to the outer flange thickness \( x_5 \).
    2. Beam width constraint: \( x_4 \geq x_3 \), ensuring that the beam width \( x_4 \) is greater than or equal to the beam height \( x_3 \).
    3. Inner flange height constraint: \( x_6 \geq \frac{x_3}{2} \), ensuring that the inner flange height \( x_6 \) is greater than or equal to half the beam height \( x_3 \).
    4. Web thickness constraint: \( x_7 \leq x_4 \), ensuring that the web thickness \( x_7 \) is less than or equal to the beam width \( x_4 \).
    5. Outer flange thickness constraint: \( x_5 \leq x_6 \), ensuring that the outer flange thickness \( x_5 \) is less than or equal to the inner flange thickness \( x_6 \).

    Where:
    - \( x_1 \) is the weld height.
    - \( x_2 \) is the weld length.
    - \( x_3 \) is the beam height.
    - \( x_4 \) is the beam width.
    - \( x_5 \) is the outer flange thickness.
    - \( x_6 \) is the inner flange thickness.
    - \( x_7 \) is the web thickness.

    The parameters are defined as:
    - \( P = 30000 \, \text{N} \) (load),
    - \( L = 0.5 \, \text{m} \) (beam length),
    - \( E = 200 \times 10^9 \, \text{Pa} \) (Young's modulus),
    - \( \tau_{max} = 95 \times 10^6 \, \text{Pa} \) (max shear stress),
    - \( \sigma_{max} = 200 \times 10^6 \, \text{Pa} \) (max normal stress),
    - \( C_w = 209600 \, \text{\$/m}^3 \) (welding cost factor),
    - \( C_s = 0.7 \, \text{\$/kg} \) (price of HRC steel),
    - \( \rho_s = 7850 \, \text{kg/m}^3 \) (steel density),
    - \( C_b = 0.7 \times 7850 \, \text{\$/m}^3 \) (beam material cost factor),
    - \( K = 2 \) (cantilever beam coefficient),
    - \( \pi = 3.141592653589793 \) (constant for calculations),
    - \( \delta_t = 0.045 \) (tolerance factor for calculations).

    Returns:
        Problem: An instance of the multi-objective cantilever welded beam optimization problem using a tapered channel cross-section.
"""
    # Variables
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0.005, upperbound=0.15),  # weld height (a)
        Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.3),  # weld length (l)
        Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.2),  # beam height (h)
        Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.15),  # beam width (b)
        Variable(name="x_5", symbol="x_5", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.03),  # flange thickness outer (u)
        Variable(name="x_6", symbol="x_6", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=2*0.03),  # flange thickness inner (v)
        Variable(name="x_7", symbol="x_7", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.03),  # web thickness (t)
    ]

    # Constants
    constants = CONSTANTS

    # Extra Functions (Intermediate Calculations)
    extra_functions = [
         # b_inner: the inner width of the flange (b - t)
         ExtraFunction(
             name="b_inner", symbol="b_inner",
             func="x_4 - x_5"
         ),
         # A_web: area of the web (h * t)
         ExtraFunction(
             name="A_web", symbol="A_web",
             func="x_3 * x_5"
         ),
         # A_flange: area of the flange (b_inner * (u + v))
         ExtraFunction(
             name="A_flange", symbol="A_flange",
             func="b_inner * (x_6 + x_7)"
         ),
         # Total cross-sectional area (A = A_web + A_flange)
         ExtraFunction(
             name="cross_section_area", symbol="A",
             func="A_web + A_flange"
         ),
        # Moment of inertia for the outer rectangle (Ix_rectangle)
        ExtraFunction(
          name="Ix_rectangle", symbol="Ix_rectangle",
          func="(x_4 * x_3 ** 3) / 12"
        ),
        ExtraFunction(
            name="flange_to_flange_outer", symbol="flange_to_flange_outer",
            func="x_3 - 2 * x_6"
        ),
        ExtraFunction(
            name="flange_to_flange_inner", symbol="flange_to_flange_inner",
            func="x_3 - 2 * x_7"
        ),
          ExtraFunction(
              name="slope_flange", symbol="slope_flange",
              func="(flange_to_flange_outer - flange_to_flange_inner) / 2 * (x_4 - x_5)"
          ),
        # Moment of inertia for the outer flange (Ix_flange_outer)
        ExtraFunction(
          name="Ix_flange_outer", symbol="Ix_flange_outer",
          func="(flange_to_flange_outer ** 4 / 8 * slope_flange)"
        ),
        # Moment of inertia for the inner flange (Ix_flange_inner)
        ExtraFunction(
          name="Ix_flange_inner", symbol="Ix_flange_inner",
          func="(flange_to_flange_inner) ** 4 / 8 * slope_flange / 12"
        ),
        ExtraFunction(
            name="Ix_flange", symbol="Ix_flange",
            func="Ix_flange_outer - Ix_flange_inner"
        ),
        # Total moment of inertia: Ix = Ix_rectangle + Ix_flange_outer - Ix_flange_inner
        ExtraFunction(
          name="moment_of_inertia", symbol="I_x",
          func="Ix_rectangle + Ix_flange"
        )
    ] + EXTRAFUNCTION

    # Objectives (minimize cost, minimize deflection, etc.)
    objectives = OBJECTIVES

    # Constraints
    constraints = CONSTRAINTS + [
        # Weld height constraint (g_4) - weld height should be less than or equal to flange thickness
        Constraint(
            name="g_4", symbol="g_4", cons_type=ConstraintTypeEnum.LTE,
            func="(x_1 - x_5) / (0.03 - 0.01)"  # Weld height should be <= outer flange thickness
        ),
        # Beam width constraint (g_5) - beam width should be greater than or equal to beam height
        Constraint(
            name="g_5", symbol="g_5", cons_type=ConstraintTypeEnum.LTE,
            func="(x_4 - x_3) / (0.2 - 0.01)"  # Beam width should be >= beam height
        ),
        # Cross-section geometric constraints (g_6 and g_7)
        # Inner flange height must be greater than or equal to half the beam height
        Constraint(
            name="g_6", symbol="g_6", cons_type=ConstraintTypeEnum.LTE,
            func="(x_6 - x_3 / 2) / (0.03 - 0.01)"  # Inner flange thickness must be greater than half the beam height
        ),
        # Web thickness constraint: web thickness should be less than the beam width
        Constraint(
            name="g_7", symbol="g_7", cons_type=ConstraintTypeEnum.LTE,
            func="(x_7 - x_4) / (0.03 - 0.01)"  # Web thickness should be <= beam width
        ),
        # Outer flange thickness constraint: outer flange thickness must be less than or equal to inner flange thickness
        Constraint(
            name="g_8", symbol="g_8", cons_type=ConstraintTypeEnum.LTE,
            func="(x_5 - x_6) / (0.03 - 0.01)"  # Outer flange thickness <= inner flange thickness
        )
    ]

    return Problem(
        name="MCWB Tapered Channel",
        description="Multi-objective optimization of a welded tapered channel beam with constraints on geometry and load-bearing capacity.",
        constants=constants,
        variables=variables,
        extra_funcs=extra_functions,
        objectives=objectives,
        constraints=constraints,
    )

def mcwb_ragsdell1976_problem() -> Problem:
    r"""Defines the multi-objective cantilever welded beam (MCWB) optimization problem based on the framework proposed by Ragsdell (1976).

    This problem involves optimizing the design of a welded cantilever beam considering welding costs, material costs, and stress constraints. The goal is to minimize both the total cost and the deflection of the beam, while adhering to the given constraints on material properties, geometry, and loading conditions.

    Objectives:
    1. Minimize the total cost, \( f_1 = W_c + B_c \), where:
        - \( W_c \) is the weld cost, calculated as the sum of welding labor cost and material cost.
        - \( B_c \) is the beam material cost, based on the beam's dimensions and the cost of the steel used.
    2. Minimize the deflection of the beam, \( f_2 = \frac{P L^3}{3 E I_x} \), where:
        - \( P \) is the applied load.
        - \( L \) is the beam length.
        - \( E \) is the Young's modulus.
        - \( I_x \) is the moment of inertia of the beam's cross-section.

    Constraints:
    1. **Weld height constraint**: \( x_1 \leq x_4 \), ensuring that the weld height \( x_1 \) is less than or equal to the beam width \( x_4 \) (flange thickness).
    2. The problem also considers the material constraints on maximum shear stress and normal stress, but these are not explicitly listed as constraints in this setup.

    Where:
    - \( x_1 \) is the height of the weld.
    - \( x_2 \) is the length of the weld.
    - \( x_3 \) is the height of the beam.
    - \( x_4 \) is the width of the beam.

    Constants:
    - \( P = 30000 \, \text{N} \) (load),
    - \( L = 0.5 \, \text{m} \) (beam length),
    - \( E = 200 \times 10^9 \, \text{Pa} \) (Young's modulus),
    - \( \tau_{\text{max}} = 95 \times 10^6 \, \text{Pa} \) (maximum shear stress),
    - \( \sigma_{\text{max}} = 200 \times 10^6 \, \text{Pa} \) (maximum normal stress),
    - \( C_{\text{wl}} = 1 \, \text{\$/in} \) (welding labor cost),
    - \( C_{\text{wm}} = 0.10471 \, \text{\$/in} \) (welding material cost),
    - \( C_{\text{w}} = 1 \times 0.10471 \, \text{\$/in} \) (total welding cost),
    - \( C_s = 0.7 \, \text{\$/kg} \) (steel price),
    - \( \rho_s = 7850 \, \text{kg/m}^3 \) (steel density),
    - \( C_b = 0.04811 \, \text{\$/in} \) (beam material cost),
    - \( K = 2 \) (cantilever beam coefficient),
    - \( \pi = 3.141592653589793 \) (constant),
    - \( \delta_t = 0.05 - 0.005 \) (tolerance factor).

    Intermediate Functions:
    1. **Cross-sectional area**: \( A = x_3 \times x_4 \).
    2. **Moment of inertia**: \( I_x = \frac{x_4 \times x_3^3}{12} \), representing the beam's resistance to bending.

    References:
        - Ragsdell, K. M. (1976). Engineering Optimization: Methods and Applications. Wiley.
        - Cheng, F. Y., & Li, X. S. (1999). Generalized center method for multiobjective engineering optimization. Engineering Optimization, 31(5), 641-661.

    Args:
        None (Constants and variables are predefined within the function).

    Returns:
        Problem: An instance of the multi-objective cantilever welded beam optimization problem based on Ragsdell's method (1976).
    """
    # Variables (decision variables: weld height, weld length, beam height, beam width)
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0.125, upperbound=5),  # height of weld [in]
        Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0.1, upperbound=10),  # length of weld [in]
        Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=0.1, upperbound=10),  # height of beam [in]
        Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real, lowerbound=0.1, upperbound=5),  # width of beam [in]
    ]

    constants = [
        Constant(name="P", symbol="P", value=30000),  # Load [N]
        Constant(name="L", symbol="L", value=0.5),  # Beam length [m]
        Constant(name="E", symbol="E", value=200e9),  # Young's modulus [Pa]
        Constant(name="tau_max", symbol="tau_max", value=95e6),  # Max shear stress [Pa]
        Constant(name="sigma_max", symbol="sigma_max", value=200e6),  # Max normal stress [Pa]
        Constant(name="C_wl", symbol="C_wl", value=1),  # Welding labor cost [$/in]
        Constant(name="C_wm", symbol="C_wm", value=0.10471),  # Welding material cost [$/in]
        Constant(name="C_w", symbol="C_w", value=1 * 0.10471),  # Total welding cost [$/in]
        Constant(name="steel_cost", symbol="C_s", value=0.7),  # Price of HRC steel [$/kg]
        Constant(name="steel_density", symbol="rho_s", value=7850),  # Steel density [kg/m^3]
        Constant(name="C_b", symbol="C_b", value=0.04811),  # Beam material cost [$/in]
        Constant(name="K", symbol="K", value=2),  # Cantilever beam coefficient
        Constant(name="pi", symbol="pi", value=3.141592653589793),
        Constant(name="delta_t", symbol="delta_t", value=0.05 - 0.005),
    ]

    # Extra Functions (Intermediate Calculations)
    extra_functions = [
          ExtraFunction(name="cross_section_area", symbol="A", func="x_3 * x_4"),  # A = h * b
          ExtraFunction(name="moment_of_inertia", symbol="I_x", func="(x_4 * x_3**3) / 12"),
          # I_x = (b * h³) / 12
      ] + EXTRAFUNCTION

    # Objectives (minimize cost, minimize deflection)
    objectives = OBJECTIVES

    # NO DUMMY CONSTRAINTS
    # Constraints
    extra_functions = [
          ExtraFunction(name="cross_section_area", symbol="A", func="x_3 * x_4"),  # A = h * b
          ExtraFunction(name="moment_of_inertia", symbol="I_x", func="(x_4 * x_3**3) / 12"),
          # I_x = (b * h³) / 12
      ] + EXTRAFUNCTION

    # Constraints
    constraints = CONSTRAINTS + [
        Constraint(
            name="g_4", symbol="g_4", cons_type=ConstraintTypeEnum.LTE,
            func="(x_1 - x_4) / (0.25 - 0.005)"  # Ensures x_1 <= x_4 (weld height <= flange thickness)
        )
    ]

    return Problem(
        name="MCWB Ragsdell1976",
        description="Optimization of a welded beam based on Ragsdell's method (1976), considering welding and material costs and stress constraints.",
        constants=constants,
        variables=variables,
        extra_funcs=extra_functions,
        objectives=objectives,
        constraints=constraints,
    )