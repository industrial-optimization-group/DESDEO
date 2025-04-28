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

def mcwb_solid_rectangular_problem() -> Problem:
    # Variables
    variables = [
        Variable(name="x_1", symbol="x_1", variable_type=VariableTypeEnum.real, lowerbound=0.005, upperbound=0.15),  # height of weld
        Variable(name="x_2", symbol="x_2", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.3),  # length of weld
        Variable(name="x_3", symbol="x_3", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.3),  # height of beam
        Variable(name="x_4", symbol="x_4", variable_type=VariableTypeEnum.real, lowerbound=0.01, upperbound=0.15),  # width of beam
        ]

    # Constants
    constants = [
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
    ]

    # Extra Functions (Intermediate Calculations)
    # TODO odkial su extra functions
    extra_functions = [
        ExtraFunction(name="cross_section_area", symbol="A", func="x_3 * x_4"),  # A = h * b
        ExtraFunction(name="moment_of_inertia", symbol="I_x", func="(x_4 * x_3**3) / 12"),  # I_x = (b * h³) / 12
        ExtraFunction(name="weld_cost", symbol="W_c", func="C_w * x_1**2 * x_2"),  # Weld cost
        ExtraFunction(name="beam_cost", symbol="B_c", func="C_b * A * (L + x_2)"),  # Beam cost
        ExtraFunction(name="polar_moment", symbol="J",
                      func="2 * ((2**(1/2))/2 * x_1 * x_2 * (x_2**2 / 12 + ((x_1 + x_3) / 2) ** 2))"),  # J calculation
        ExtraFunction(name="effective_radius", symbol="R", func="((x_2**2 / 4) + ((x_3 + x_1) / 2) ** 2) ** (1/2)"),
        # R calculation
        ExtraFunction(name="bending_moment", symbol="M", func="P * (L + x_2 / 2)"),  # M calculation
        ExtraFunction(name="primary_shear_stress", symbol="tau_1", func="P / ((2**(1/2)) * x_1 * x_2)"),  # tau_1 calculation
        ExtraFunction(name="torsional_stress", symbol="tau_2", func="M * R / J"),  # tau_2 calculation
        ExtraFunction(name="combined_shear", symbol="tau",
                      func="(tau_1**2 + (2 * tau_1 * tau_2 * (x_2 / (2 * R))) + tau_2**2) ** (1/2)"),  # Combined shear stress
        ExtraFunction(name="bending_stress", symbol="sigma_x", func="P * L * x_3 / (2 * I_x)"),  # sigma_x calculation
        ExtraFunction(name="critical_buckling", symbol="P_c", func="(pi**2 * E * I_x) / (K * L)**2"),  # P_c calculation
    ]

    # Objectives (minimize cost, minimize deflection)
    objectives = [
        Objective(name="f_1", symbol="f_1", func="W_c + B_c", maximize=False),  # Minimize total cost
        Objective(name="f_2", symbol="f_2", func="P * L**3 / (3 * E * I_x)", maximize=False), # Minimize beam deflection
    ]

    # Constraints
    constraints = [
        Constraint(name="g_1", symbol="g_1", cons_type=ConstraintTypeEnum.LTE, func="(1 / tau_max) * (tau - tau_max)"), # Shear stress
        Constraint(name="g_2", symbol="g_2", cons_type=ConstraintTypeEnum.LTE,
                   func="(1 / sigma_max) * (sigma_x - sigma_max)"),  # Normal stress
        Constraint(name="g_3", symbol="g_3", cons_type=ConstraintTypeEnum.LTE, func="(1 / P) * (P - P_c)"), # Buckling constraint
        Constraint(name="g_4", symbol="g_4", cons_type=ConstraintTypeEnum.LTE, func="(x_1 - x_4) / (0.15 - 0.005)"), # Weld geometry constraint
    ]

    # if dummy_constraints:
    #     constraints.extend([
    #         Constraint(name="g_5", symbol="g_5", cons_type=ConstraintTypeEnum.LTE, func="0"),  # Placeholder
    #         Constraint(name="g_6", symbol="g_6", cons_type=ConstraintTypeEnum.LTE, func="0"),  # Placeholder
    #         Constraint(name="g_7", symbol="g_7", cons_type=ConstraintTypeEnum.LTE, func="0"),  # Placeholder
    #     ])

    return Problem(
        name="MCWB Solid Rectangular",
        description="Multi-objective optimization of a welded beam using a solid rectangular cross-section.",
        constants=constants,
        variables=variables,
        extra_functions=extra_functions,
        objectives=objectives,
        constraints=constraints,
    )