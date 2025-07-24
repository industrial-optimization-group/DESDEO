import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";



type Tensor_Input = (Array<Tensor_Input> | Array<(number | number | boolean) | Array<number | number | boolean>> | number | number | boolean | string | null) | Array<Array<Tensor_Input> | Array<(number | number | boolean) | Array<number | number | boolean>> | number | number | boolean | string | null>;;
type Tensor_Output = (Array<Tensor_Output> | Array<(number | number | boolean) | Array<number | number | boolean>> | number | number | boolean | string | null) | Array<Array<Tensor_Output> | Array<(number | number | boolean) | Array<number | number | boolean>> | number | number | boolean | string | null>;;

const UserRole = z.enum(["guest", "dm", "analyst", "admin"]);
const UserPublic = z.object({ username: z.string(), id: z.number().int(), role: UserRole, group: z.string() }).passthrough();
const Body_login_login_post = z.object({ grant_type: z.union([z.string(), z.null()]).optional(), username: z.string(), password: z.string(), scope: z.string().optional().default(""), client_id: z.union([z.string(), z.null()]).optional(), client_secret: z.union([z.string(), z.null()]).optional() }).passthrough();
const Tokens = z.object({ access_token: z.string(), refresh_token: z.string(), token_type: z.string() }).passthrough();
const ValidationError = z.object({ loc: z.array(z.union([z.string(), z.number()])), msg: z.string(), type: z.string() }).passthrough();
const HTTPValidationError = z.object({ detail: z.array(ValidationError) }).partial().passthrough();
const Body_add_new_dm_add_new_dm_post = z.object({ grant_type: z.union([z.string(), z.null()]).optional(), username: z.string(), password: z.string(), scope: z.string().optional().default(""), client_id: z.union([z.string(), z.null()]).optional(), client_secret: z.union([z.string(), z.null()]).optional() }).passthrough();
const Body_add_new_analyst_add_new_analyst_post = z.object({ grant_type: z.union([z.string(), z.null()]).optional(), username: z.string(), password: z.string(), scope: z.string().optional().default(""), client_id: z.union([z.string(), z.null()]).optional(), client_secret: z.union([z.string(), z.null()]).optional() }).passthrough();
const VariableDomainTypeEnum = z.enum(["continuous", "binary", "integer", "mixed"]);
const ProblemInfoSmall = z.object({ name: z.string(), description: z.string(), is_convex: z.union([z.boolean(), z.null()]), is_linear: z.union([z.boolean(), z.null()]), is_twice_differentiable: z.union([z.boolean(), z.null()]), scenario_keys: z.union([z.array(z.string()), z.null()]), variable_domain: VariableDomainTypeEnum, id: z.number().int(), user_id: z.number().int() }).passthrough();
const ConstantDB = z.object({ name: z.string(), symbol: z.string(), value: z.number(), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const Tensor_Output: z.ZodType<Tensor_Output> = z.lazy(() => z.union([z.array(Tensor_Output), z.array(z.union([z.number(), z.number(), z.boolean()])), z.number(), z.number(), z.boolean(), z.string(), z.null()]));
const TensorConstantDB = z.object({ values: Tensor_Output, shape: z.array(z.number().int()), name: z.string(), symbol: z.string(), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const VariableTypeEnum = z.enum(["real", "integer", "binary"]);
const VariableDB = z.object({ name: z.string(), symbol: z.string(), variable_type: VariableTypeEnum, lowerbound: z.union([z.number(), z.null()]).optional(), upperbound: z.union([z.number(), z.null()]).optional(), initial_value: z.union([z.number(), z.null()]).optional(), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const TensorVariableDB = z.object({ initial_values: z.union([Tensor_Output, z.null()]), lowerbounds: z.union([Tensor_Output, z.null()]), upperbounds: z.union([Tensor_Output, z.null()]), shape: z.array(z.number().int()), name: z.string(), symbol: z.string(), variable_type: VariableTypeEnum, id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const ObjectiveTypeEnum = z.enum(["analytical", "data_based", "simulator", "surrogate"]);
const ObjectiveDB = z.object({ func: z.union([z.array(z.unknown()), z.null()]), scenario_keys: z.union([z.array(z.string()), z.null()]).optional(), surrogates: z.union([z.array(z.string()), z.null()]).optional(), simulator_path: z.union([z.string(), z.null()]).optional(), name: z.string(), symbol: z.string(), unit: z.union([z.string(), z.null()]).optional(), maximize: z.boolean().optional().default(false), ideal: z.union([z.number(), z.null()]).optional(), nadir: z.union([z.number(), z.null()]).optional(), objective_type: ObjectiveTypeEnum.optional(), is_linear: z.boolean().optional().default(false), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const ConstraintTypeEnum = z.enum(["=", "<="]);
const ConstraintDB = z.object({ func: z.array(z.unknown()), scenario_keys: z.union([z.array(z.string()), z.null()]).optional(), surrogates: z.union([z.array(z.string()), z.null()]).optional(), simulator_path: z.union([z.string(), z.null()]).optional(), name: z.string(), symbol: z.string(), cons_type: ConstraintTypeEnum, is_linear: z.boolean().optional().default(true), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const ScalarizationFunctionDB = z.object({ func: z.array(z.unknown()), scenario_keys: z.array(z.string()), name: z.string(), symbol: z.union([z.string(), z.null()]).optional(), is_linear: z.boolean().optional().default(false), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const ExtraFunctionDB = z.object({ func: z.array(z.unknown()), scenario_keys: z.union([z.array(z.string()), z.null()]).optional(), surrogates: z.union([z.array(z.string()), z.null()]).optional(), simulator_path: z.union([z.string(), z.null()]).optional(), name: z.string(), symbol: z.string(), is_linear: z.boolean().optional().default(false), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const DiscreteRepresentationDB = z.object({ non_dominated: z.boolean().optional().default(false), variable_values: z.record(z.array(z.union([z.number(), z.number(), z.boolean()]))), objective_values: z.record(z.array(z.number())), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const SimulatorDB = z.object({ file: z.string(), parameter_options: z.union([z.object({}).partial().passthrough(), z.null()]).optional(), name: z.string(), symbol: z.string(), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const ProblemInfo = z.object({ name: z.string(), description: z.string(), is_convex: z.union([z.boolean(), z.null()]), is_linear: z.union([z.boolean(), z.null()]), is_twice_differentiable: z.union([z.boolean(), z.null()]), scenario_keys: z.union([z.array(z.string()), z.null()]), variable_domain: VariableDomainTypeEnum, id: z.number().int(), user_id: z.number().int(), constants: z.union([z.array(ConstantDB), z.null()]), tensor_constants: z.union([z.array(TensorConstantDB), z.null()]), variables: z.union([z.array(VariableDB), z.null()]), tensor_variables: z.union([z.array(TensorVariableDB), z.null()]), objectives: z.array(ObjectiveDB), constraints: z.union([z.array(ConstraintDB), z.null()]), scalarization_funcs: z.union([z.array(ScalarizationFunctionDB), z.null()]), extra_funcs: z.union([z.array(ExtraFunctionDB), z.null()]), discrete_representation: z.union([DiscreteRepresentationDB, z.null()]), simulators: z.union([z.array(SimulatorDB), z.null()]) }).passthrough();
const ProblemGetRequest = z.object({ problem_id: z.number().int() }).passthrough();
const Constant = z.object({ name: z.string(), symbol: z.string(), value: z.union([z.number(), z.number(), z.boolean()]) }).passthrough();
const Tensor_Input: z.ZodType<Tensor_Input> = z.lazy(() => z.union([z.array(Tensor_Input), z.array(z.union([z.number(), z.number(), z.boolean()])), z.number(), z.number(), z.boolean(), z.string(), z.null()]));
const TensorConstant = z.object({ name: z.string(), symbol: z.string(), shape: z.array(z.number().int()), values: Tensor_Input }).passthrough();
const Variable = z.object({ name: z.string(), symbol: z.string(), variable_type: VariableTypeEnum, lowerbound: z.union([z.number(), z.number(), z.boolean(), z.null()]).optional(), upperbound: z.union([z.number(), z.number(), z.boolean(), z.null()]).optional(), initial_value: z.union([z.number(), z.number(), z.boolean(), z.null()]).optional() }).passthrough();
const TensorVariable = z.object({ name: z.string(), symbol: z.string(), variable_type: VariableTypeEnum, shape: z.array(z.number().int()), lowerbounds: z.union([Tensor_Input, z.null()]).optional(), upperbounds: z.union([Tensor_Input, z.number(), z.number(), z.boolean(), z.null()]).optional(), initial_values: z.union([Tensor_Input, z.number(), z.number(), z.boolean(), z.null()]).optional() }).passthrough();
const Objective = z.object({ name: z.string(), symbol: z.string(), unit: z.union([z.string(), z.null()]).optional(), func: z.union([z.array(z.unknown()), z.null()]).optional(), simulator_path: z.union([z.string(), z.null()]).optional(), surrogates: z.union([z.array(z.string()), z.null()]).optional(), maximize: z.boolean().optional().default(false), ideal: z.union([z.number(), z.null()]).optional(), nadir: z.union([z.number(), z.null()]).optional(), objective_type: ObjectiveTypeEnum.optional(), is_linear: z.boolean().optional().default(false), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), scenario_keys: z.union([z.array(z.string()), z.null()]).optional() }).passthrough();
const Constraint = z.object({ name: z.string(), symbol: z.string(), cons_type: ConstraintTypeEnum, func: z.union([z.array(z.unknown()), z.null()]).optional(), simulator_path: z.union([z.string(), z.null()]).optional(), surrogates: z.union([z.array(z.string()), z.null()]).optional(), is_linear: z.boolean().optional().default(true), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), scenario_keys: z.union([z.array(z.string()), z.null()]).optional() }).passthrough();
const ExtraFunction = z.object({ name: z.string(), symbol: z.string(), func: z.union([z.array(z.unknown()), z.null()]).optional(), simulator_path: z.union([z.string(), z.null()]).optional(), surrogates: z.union([z.array(z.string()), z.null()]).optional(), is_linear: z.boolean().optional().default(false), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), scenario_keys: z.union([z.array(z.string()), z.null()]).optional() }).passthrough();
const ScalarizationFunction = z.object({ name: z.string(), symbol: z.union([z.string(), z.null()]).optional(), func: z.array(z.unknown()), is_linear: z.boolean().optional().default(false), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), scenario_keys: z.array(z.string()).optional() }).passthrough();
const DiscreteRepresentation = z.object({ variable_values: z.record(z.array(z.union([z.number(), z.number(), z.boolean()]))), objective_values: z.record(z.array(z.number())), non_dominated: z.boolean().optional().default(false) }).passthrough();
const Simulator = z.object({ name: z.string(), symbol: z.string(), file: z.string(), parameter_options: z.union([z.object({}).partial().passthrough(), z.null()]).optional() }).passthrough();
const Problem = z.object({ name: z.string(), description: z.string(), constants: z.union([z.array(z.union([Constant, TensorConstant])), z.null()]).optional(), variables: z.array(z.union([Variable, TensorVariable])), objectives: z.array(Objective), constraints: z.union([z.array(Constraint), z.null()]).optional(), extra_funcs: z.union([z.array(ExtraFunction), z.null()]).optional(), scalarization_funcs: z.union([z.array(ScalarizationFunction), z.null()]).optional(), discrete_representation: z.union([DiscreteRepresentation, z.null()]).optional(), scenario_keys: z.union([z.array(z.string()), z.null()]).optional(), simulators: z.union([z.array(Simulator), z.null()]).optional(), is_convex: z.union([z.boolean(), z.null()]).optional(), is_linear: z.union([z.boolean(), z.null()]).optional(), is_twice_differentiable: z.union([z.boolean(), z.null()]).optional() }).passthrough();
const CreateSessionRequest = z.object({ info: z.union([z.string(), z.null()]) }).partial().passthrough();
const InteractiveSessionBase = z.object({ id: z.union([z.number(), z.null()]), user_id: z.union([z.number(), z.null()]), info: z.union([z.string(), z.null()]) }).passthrough();
const GetSessionRequest = z.object({ session_id: z.number().int() }).passthrough();
const ReferencePoint = z.object({ preference_type: z.string().optional().default("reference_point"), aspiration_levels: z.record(z.number()) }).passthrough();
const RPMSolveRequest = z.object({ problem_id: z.number().int(), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional(), scalarization_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional(), solver_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), preference: ReferencePoint.optional() }).passthrough();
const SolverResults = z.object({ optimal_variables: z.record(z.union([z.number(), z.number(), z.array(z.unknown())])), optimal_objectives: z.record(z.union([z.number(), z.array(z.number())])), constraint_values: z.union([z.record(z.union([z.number(), z.number(), z.array(z.number()), z.array(z.unknown())])), z.unknown(), z.null()]).optional(), extra_func_values: z.union([z.record(z.union([z.number(), z.array(z.number())])), z.null()]).optional(), scalarization_values: z.union([z.record(z.union([z.number(), z.array(z.number())])), z.null()]).optional(), success: z.boolean(), message: z.string() }).passthrough();
const RPMState = z.object({ method: z.string().optional().default("reference_point_method"), phase: z.string().optional().default("solve_candidates"), scalarization_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional(), solver_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver_results: z.array(SolverResults) }).passthrough();
const NIMBUSClassificationRequest = z.object({ problem_id: z.number().int(), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional(), scalarization_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional(), solver_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), preference: ReferencePoint.optional(), current_objectives: z.record(z.number()), num_desired: z.union([z.number(), z.null()]).optional().default(1) }).passthrough();
const NIMBUSClassificationState = z.object({ method: z.string().optional().default("nimbus"), phase: z.string().optional().default("solve_candidates"), scalarization_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional(), solver_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), current_objectives: z.record(z.number()), num_desired: z.union([z.number(), z.null()]).optional().default(1), solver_results: z.array(SolverResults) }).passthrough();
const UserSavedSolverResults = z.object({ optimal_variables: z.record(z.union([z.number(), z.number(), z.array(z.unknown())])), optimal_objectives: z.record(z.union([z.number(), z.array(z.number())])), constraint_values: z.union([z.record(z.union([z.number(), z.number(), z.array(z.number()), z.array(z.unknown())])), z.unknown(), z.null()]).optional(), extra_func_values: z.union([z.record(z.union([z.number(), z.array(z.number())])), z.null()]).optional(), scalarization_values: z.union([z.record(z.union([z.number(), z.array(z.number())])), z.null()]).optional(), success: z.boolean(), message: z.string(), name: z.union([z.string(), z.null()]).optional() }).passthrough();
const NIMBUSSaveRequest = z.object({ problem_id: z.number().int(), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional(), solutions: z.array(UserSavedSolverResults) }).passthrough();
const NIMBUSSaveState = z.object({ method: z.string().optional().default("nimbus"), phase: z.string().optional().default("save_solutions"), solver_results: z.array(SolverResults) }).passthrough();
const IntermediateSolutionRequest = z.object({ problem_id: z.number().int(), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional(), scalarization_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional(), solver_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), num_desired: z.union([z.number(), z.null()]).optional().default(1), reference_solution_1: z.record(z.number()), reference_solution_2: z.record(z.number()) }).passthrough();
const IntermediateSolutionState = z.object({ method: z.string().optional().default("generic"), phase: z.string().optional().default("solve_intermediate"), scalarization_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional(), solver_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), num_desired: z.union([z.number(), z.null()]).optional().default(1), reference_solution_1: z.record(z.number()), reference_solution_2: z.record(z.number()), solver_results: z.array(SolverResults) }).passthrough();

export const schemas = {
	UserRole,
	UserPublic,
	Body_login_login_post,
	Tokens,
	ValidationError,
	HTTPValidationError,
	Body_add_new_dm_add_new_dm_post,
	Body_add_new_analyst_add_new_analyst_post,
	VariableDomainTypeEnum,
	ProblemInfoSmall,
	ConstantDB,
	Tensor_Output,
	TensorConstantDB,
	VariableTypeEnum,
	VariableDB,
	TensorVariableDB,
	ObjectiveTypeEnum,
	ObjectiveDB,
	ConstraintTypeEnum,
	ConstraintDB,
	ScalarizationFunctionDB,
	ExtraFunctionDB,
	DiscreteRepresentationDB,
	SimulatorDB,
	ProblemInfo,
	ProblemGetRequest,
	Constant,
	Tensor_Input,
	TensorConstant,
	Variable,
	TensorVariable,
	Objective,
	Constraint,
	ExtraFunction,
	ScalarizationFunction,
	DiscreteRepresentation,
	Simulator,
	Problem,
	CreateSessionRequest,
	InteractiveSessionBase,
	GetSessionRequest,
	ReferencePoint,
	RPMSolveRequest,
	SolverResults,
	RPMState,
	NIMBUSClassificationRequest,
	NIMBUSClassificationState,
	UserSavedSolverResults,
	NIMBUSSaveRequest,
	NIMBUSSaveState,
	IntermediateSolutionRequest,
	IntermediateSolutionState,
};


const endpoints = makeApi([
	{
		method: "post",
		path: "/add_new_analyst",
		alias: "add_new_analyst_add_new_analyst_post",
		description: `Add a new user of the role Analyst to the database. Requires a logged in analyst or an admin

Args:
    user Annotated[User, Depends(get_current_user)]: Logged in user with the role &quot;analyst&quot; or &quot;admin&quot;.
    form_data (Annotated[OAuth2PasswordRequestForm, Depends()]): The user credentials to add to the database.
    session (Annotated[Session, Depends(get_session)]): the database session.

Returns:
    JSONResponse: A JSON response

Raises:
    HTTPException: if the logged in user is not an analyst or an admin or if
    username is already in use or if saving to the database fails for some reason.`,
		requestFormat: "form-url",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: Body_add_new_analyst_add_new_analyst_post
			},
		],
		response: z.unknown(),
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "post",
		path: "/add_new_dm",
		alias: "add_new_dm_add_new_dm_post",
		description: `Add a new user of the role Decision Maker to the database. Requires no login.

Args:
    form_data (Annotated[OAuth2PasswordRequestForm, Depends()]): The user credentials to add to the database.
    session (Annotated[Session, Depends(get_session)]): the database session.

Returns:
    JSONResponse: A JSON response

Raises:
    HTTPException: if username is already in use or if saving to the database fails for some reason.`,
		requestFormat: "form-url",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: Body_add_new_dm_add_new_dm_post
			},
		],
		response: z.unknown(),
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "post",
		path: "/login",
		alias: "login_login_post",
		description: `Login to get an authentication token.

Return an access token in the response and a cookie storing a refresh token.

Args:
    form_data (Annotated[OAuth2PasswordRequestForm, Depends()]):
        The form data to authenticate the user.
    session (Annotated[Session, Depends(get_db)]): The database session.
    cookie_max_age (int): the lifetime of the cookie storing the refresh token.`,
		requestFormat: "form-url",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: Body_login_login_post
			},
			{
				name: "cookie_max_age",
				type: "Query",
				schema: z.number().int().optional().default(30)
			},
		],
		response: Tokens,
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "post",
		path: "/logout",
		alias: "logout_logout_post",
		description: `Log the current user out. Deletes the refresh token that was set by logging in.

Args:
    None

Returns:
    JSONResponse: A response in which the cookies are deleted`,
		requestFormat: "json",
		response: z.unknown(),
	},
	{
		method: "post",
		path: "/method/generic/intermediate",
		alias: "solve_intermediate_method_generic_intermediate_post",
		description: `Solve intermediate solutions between given two solutions.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: IntermediateSolutionRequest
			},
		],
		response: IntermediateSolutionState,
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "post",
		path: "/method/nimbus/save",
		alias: "save_method_nimbus_save_post",
		description: `Save solutions.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: NIMBUSSaveRequest
			},
		],
		response: NIMBUSSaveState,
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "post",
		path: "/method/nimbus/solve",
		alias: "solve_solutions_method_nimbus_solve_post",
		description: `Solve the problem using the NIMBUS method.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: NIMBUSClassificationRequest
			},
		],
		response: NIMBUSClassificationState,
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "post",
		path: "/method/rpm/solve",
		alias: "solve_solutions_method_rpm_solve_post",
		description: `.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: RPMSolveRequest
			},
		],
		response: RPMState,
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "post",
		path: "/problem/add",
		alias: "add_problem_problem_add_post",
		description: `Add a newly defined problem to the database.

Args:
    request (Problem): the JSON representation of the problem.
    user (Annotated[User, Depends): the current user.
    session (Annotated[Session, Depends): the database session.

Note:
    Users with the role &#x27;guest&#x27; may not add new problems.

Raises:
    HTTPException: when any issue with defining the problem arises.

Returns:
    ProblemInfo: the information about the problem added.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: Problem
			},
		],
		response: ProblemInfo,
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "get",
		path: "/problem/all",
		alias: "get_problems_problem_all_get",
		description: `Get information on all the current user&#x27;s problems.

Args:
    user (Annotated[User, Depends): the current user.

Returns:
    list[ProblemInfoSmall]: a list of information on all the problems.`,
		requestFormat: "json",
		response: z.array(ProblemInfoSmall),
	},
	{
		method: "get",
		path: "/problem/all_info",
		alias: "get_problems_info_problem_all_info_get",
		description: `Get detailed information on all the current user&#x27;s problems.

Args:
    user (Annotated[User, Depends): the current user.

Returns:
    list[ProblemInfo]: a list of the detailed information on all the problems.`,
		requestFormat: "json",
		response: z.array(ProblemInfo),
	},
	{
		method: "post",
		path: "/problem/get",
		alias: "get_problem_problem_get_post",
		description: `Get the model of a specific problem.

Args:
    request (ProblemGetRequest): the request containing the problem&#x27;s id &#x60;problem_id&#x60;.
    user (Annotated[User, Depends): the current user.
    session (Annotated[Session, Depends): the database session.

Raises:
    HTTPException: could not find a problem with the given id.

Returns:
    ProblemInfo: detailed information on the requested problem.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ problem_id: z.number().int() }).passthrough()
			},
		],
		response: ProblemInfo,
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "post",
		path: "/refresh",
		alias: "refresh_access_token_refresh_post",
		description: `Refresh the access token using the refresh token stored in the cookie.

Args:
    request (Request): The request containing the cookie.
    session (Annotated[Session, Depends(get_db)]): the database session.
    refresh_token (Annotated[Str | None, Cookie()]): the refresh
        token, which is fetched from a cookie included in the response.

Returns:
    dict: A dictionary containing the new access token.`,
		requestFormat: "json",
		response: z.unknown(),
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "post",
		path: "/session/get",
		alias: "get_session_session_get_post",
		description: `Return an interactive session with a given id for the current user.

Args:
    request (GetSessionRequest): a request containing the id of the session.
    user (Annotated[User, Depends): the current user.
    session (Annotated[Session, Depends): the database session.

Raises:
    HTTPException: could not find an interactive session with the given id
        for the current user.

Returns:
    InteractiveSessionInfo: info on the requested interactive session.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: z.object({ session_id: z.number().int() }).passthrough()
			},
		],
		response: InteractiveSessionBase,
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "post",
		path: "/session/new",
		alias: "create_new_session_session_new_post",
		description: `.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: CreateSessionRequest
			},
		],
		response: InteractiveSessionBase,
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
	{
		method: "get",
		path: "/user_info",
		alias: "get_current_user_info_user_info_get",
		description: `Return information about the current user.

Args:
    user (Annotated[User, Depends): user dependency, handled by &#x60;get_current_user&#x60;.

Returns:
    UserPublic: public information about the current user.`,
		requestFormat: "json",
		response: UserPublic,
	},
]);