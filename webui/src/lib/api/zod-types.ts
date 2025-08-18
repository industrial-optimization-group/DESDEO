import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";



type Tensor = (Array<Tensor> | Array<(number | number | boolean) | Array<number | number | boolean>> | number | number | boolean | string | null) | Array<Array<Tensor> | Array<(number | number | boolean) | Array<number | number | boolean>> | number | number | boolean | string | null>;;

const UserRole = z.enum(["guest", "dm", "analyst", "admin"]);
const UserPublic = z.object({ username: z.string(), id: z.number().int(), role: UserRole, group: z.string() }).passthrough();
const Body_login_login_post = z.object({ grant_type: z.union([z.string(), z.null()]).optional(), username: z.string(), password: z.string(), scope: z.string().optional().default(""), client_id: z.union([z.string(), z.null()]).optional(), client_secret: z.union([z.string(), z.null()]).optional() }).passthrough();
const Tokens = z.object({ access_token: z.string(), refresh_token: z.string(), token_type: z.string() }).passthrough();
const ValidationError = z.object({ loc: z.array(z.union([z.string(), z.number()])), msg: z.string(), type: z.string() }).passthrough();
const HTTPValidationError = z.object({ detail: z.array(ValidationError) }).partial().passthrough();
const Body_add_new_dm_add_new_dm_post = z.object({ grant_type: z.union([z.string(), z.null()]).optional(), username: z.string(), password: z.string(), scope: z.string().optional().default(""), client_id: z.union([z.string(), z.null()]).optional(), client_secret: z.union([z.string(), z.null()]).optional() }).passthrough();
const Body_add_new_analyst_add_new_analyst_post = z.object({ grant_type: z.union([z.string(), z.null()]).optional(), username: z.string(), password: z.string(), scope: z.string().optional().default(""), client_id: z.union([z.string(), z.null()]).optional(), client_secret: z.union([z.string(), z.null()]).optional() }).passthrough();
const VariableDomainTypeEnum = z.enum(["continuous", "binary", "integer", "mixed"]);
const BaseProblemMetaData = z.object({ metadata_type: z.string().default("unset") }).partial().passthrough();
const ProblemMetaDataPublic = z.object({ data: z.union([z.array(BaseProblemMetaData), z.null()]) }).passthrough();
const ProblemInfoSmall = z.object({ name: z.string(), description: z.string(), is_convex: z.union([z.boolean(), z.null()]), is_linear: z.union([z.boolean(), z.null()]), is_twice_differentiable: z.union([z.boolean(), z.null()]), scenario_keys: z.union([z.array(z.string()), z.null()]), variable_domain: VariableDomainTypeEnum, id: z.number().int(), user_id: z.number().int(), problem_metadata: z.union([ProblemMetaDataPublic, z.null()]) }).passthrough();
const ConstantDB = z.object({ name: z.string(), symbol: z.string(), value: z.number(), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const Tensor: z.ZodType<Tensor> = z.lazy(() => z.union([z.array(Tensor), z.array(z.union([z.number(), z.number(), z.boolean()])), z.number(), z.number(), z.boolean(), z.string(), z.null()]));
const TensorConstantDB = z.object({ values: Tensor, shape: z.array(z.number().int()), name: z.string(), symbol: z.string(), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const VariableTypeEnum = z.enum(["real", "integer", "binary"]);
const VariableDB = z.object({ name: z.string(), symbol: z.string(), variable_type: VariableTypeEnum, lowerbound: z.union([z.number(), z.null()]).optional(), upperbound: z.union([z.number(), z.null()]).optional(), initial_value: z.union([z.number(), z.null()]).optional(), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const TensorVariableDB = z.object({ initial_values: z.union([Tensor, z.null()]), lowerbounds: z.union([Tensor, z.null()]), upperbounds: z.union([Tensor, z.null()]), shape: z.array(z.number().int()), name: z.string(), symbol: z.string(), variable_type: VariableTypeEnum, id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const Url = z.object({ url: z.string(), auth: z.union([z.array(z.any()), z.null()]).optional() });
const ObjectiveTypeEnum = z.enum(["analytical", "data_based", "simulator", "surrogate"]);
const ObjectiveDB = z.object({ func: z.union([z.array(z.unknown()), z.null()]), scenario_keys: z.union([z.array(z.string()), z.null()]).optional(), surrogates: z.union([z.array(z.string()), z.null()]).optional(), simulator_path: z.union([z.string(), Url, z.null()]).optional(), name: z.string(), symbol: z.string(), unit: z.union([z.string(), z.null()]).optional(), maximize: z.boolean().optional().default(false), ideal: z.union([z.number(), z.null()]).optional(), nadir: z.union([z.number(), z.null()]).optional(), objective_type: ObjectiveTypeEnum.optional(), is_linear: z.boolean().optional().default(false), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const ConstraintTypeEnum = z.enum(["=", "<="]);
const ConstraintDB = z.object({ func: z.array(z.unknown()), scenario_keys: z.union([z.array(z.string()), z.null()]).optional(), surrogates: z.union([z.array(z.string()), z.null()]).optional(), simulator_path: z.union([z.string(), Url, z.null()]).optional(), name: z.string(), symbol: z.string(), cons_type: ConstraintTypeEnum, is_linear: z.boolean().optional().default(true), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const ScalarizationFunctionDB = z.object({ func: z.array(z.unknown()), scenario_keys: z.array(z.string()), name: z.string(), symbol: z.union([z.string(), z.null()]).optional(), is_linear: z.boolean().optional().default(false), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const ExtraFunctionDB = z.object({ func: z.array(z.unknown()), scenario_keys: z.union([z.array(z.string()), z.null()]).optional(), surrogates: z.union([z.array(z.string()), z.null()]).optional(), simulator_path: z.union([z.string(), Url, z.null()]).optional(), name: z.string(), symbol: z.string(), is_linear: z.boolean().optional().default(false), is_convex: z.boolean().optional().default(false), is_twice_differentiable: z.boolean().optional().default(false), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const DiscreteRepresentationDB = z.object({ non_dominated: z.boolean().optional().default(false), variable_values: z.record(z.array(z.union([z.number(), z.number(), z.boolean()]))), objective_values: z.record(z.array(z.number())), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const SimulatorDB = z.object({ file: z.union([z.string(), z.null()]).optional(), url: z.union([Url, z.null()]).optional(), parameter_options: z.union([z.object({}).partial().passthrough(), z.null()]).optional(), name: z.string(), symbol: z.string(), id: z.union([z.number(), z.null()]).optional(), problem_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const ProblemInfo = z.object({ name: z.string(), description: z.string(), is_convex: z.union([z.boolean(), z.null()]), is_linear: z.union([z.boolean(), z.null()]), is_twice_differentiable: z.union([z.boolean(), z.null()]), scenario_keys: z.union([z.array(z.string()), z.null()]), variable_domain: VariableDomainTypeEnum, id: z.number().int(), user_id: z.number().int(), constants: z.union([z.array(ConstantDB), z.null()]), tensor_constants: z.union([z.array(TensorConstantDB), z.null()]), variables: z.union([z.array(VariableDB), z.null()]), tensor_variables: z.union([z.array(TensorVariableDB), z.null()]), objectives: z.array(ObjectiveDB), constraints: z.union([z.array(ConstraintDB), z.null()]), scalarization_funcs: z.union([z.array(ScalarizationFunctionDB), z.null()]), extra_funcs: z.union([z.array(ExtraFunctionDB), z.null()]), discrete_representation: z.union([DiscreteRepresentationDB, z.null()]), simulators: z.union([z.array(SimulatorDB), z.null()]), problem_metadata: z.union([ProblemMetaDataPublic, z.null()]) }).passthrough();
const ProblemGetRequest = z.object({ problem_id: z.number().int() }).passthrough();
const ProblemMetaDataGetRequest = z.object({ problem_id: z.number().int(), metadata_type: z.string() }).passthrough();
const CreateSessionRequest = z.object({ info: z.union([z.string(), z.null()]) }).partial().passthrough();
const InteractiveSessionBase = z.object({ id: z.union([z.number(), z.null()]), user_id: z.union([z.number(), z.null()]), info: z.union([z.string(), z.null()]) }).passthrough();
const GetSessionRequest = z.object({ session_id: z.number().int() }).passthrough();
const ReferencePoint = z.object({ preference_type: z.string().optional().default("reference_point"), aspiration_levels: z.record(z.number()) }).passthrough();
const RPMSolveRequest = z.object({ problem_id: z.number().int(), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional(), scalarization_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional(), solver_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), preference: ReferencePoint.optional() }).passthrough();
const SolverResults = z.object({ optimal_variables: z.record(z.union([z.number(), z.number(), z.array(z.unknown())])), optimal_objectives: z.record(z.union([z.number(), z.array(z.number())])), constraint_values: z.union([z.record(z.union([z.number(), z.number(), z.array(z.number()), z.array(z.unknown())])), z.unknown(), z.null()]).optional(), extra_func_values: z.union([z.record(z.union([z.number(), z.array(z.number())])), z.null()]).optional(), scalarization_values: z.union([z.record(z.union([z.number(), z.array(z.number())])), z.null()]).optional(), success: z.boolean(), message: z.string() }).passthrough();
const RPMState = z.object({ method: z.string().optional().default("reference_point_method"), phase: z.string().optional().default("solve_candidates"), scalarization_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional(), solver_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver_results: z.array(SolverResults) }).passthrough();
const NIMBUSClassificationRequest = z.object({ problem_id: z.number().int(), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional(), scalarization_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional(), solver_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), preference: ReferencePoint.optional(), current_objectives: z.record(z.number()), num_desired: z.union([z.number(), z.null()]).optional().default(1) }).passthrough();
const SolutionAddress = z.object({ objective_values: z.record(z.number()), address_state: z.number().int(), address_result: z.number().int() }).passthrough();
const UserSavedSolutionAddress = z.object({ objective_values: z.record(z.number()), address_state: z.number().int(), address_result: z.number().int(), name: z.union([z.string(), z.null()]).optional() }).passthrough();
const NIMBUSClassificationResponse = z.object({ state_id: z.union([z.number(), z.null()]), previous_preference: ReferencePoint, previous_objectives: z.record(z.number()), current_solutions: z.array(SolutionAddress), saved_solutions: z.array(UserSavedSolutionAddress), all_solutions: z.array(SolutionAddress) }).passthrough();
const NIMBUSInitializationRequest = z.object({ problem_id: z.number().int(), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional() }).passthrough();
const NIMBUSInitializationResponse = z.object({ state_id: z.union([z.number(), z.null()]), current_solutions: z.array(SolutionAddress), saved_solutions: z.array(UserSavedSolutionAddress), all_solutions: z.array(SolutionAddress) }).passthrough();
const IntermediateSolutionResponse = z.object({ state_id: z.union([z.number(), z.null()]), reference_solution_1: z.record(z.number()), reference_solution_2: z.record(z.number()), current_solutions: z.array(SolutionAddress), saved_solutions: z.array(UserSavedSolutionAddress), all_solutions: z.array(SolutionAddress) }).passthrough();
const NIMBUSSaveRequest = z.object({ problem_id: z.number().int(), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional(), solutions: z.array(UserSavedSolutionAddress) }).passthrough();
const NIMBUSSaveResponse = z.object({ state_id: z.union([z.number(), z.null()]) }).passthrough();
const IntermediateSolutionRequest = z.object({ problem_id: z.number().int(), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional(), context: z.union([z.string(), z.null()]).optional(), scalarization_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), solver: z.union([z.string(), z.null()]).optional(), solver_options: z.union([z.record(z.union([z.number(), z.string(), z.boolean()])), z.null()]).optional(), num_desired: z.union([z.number(), z.null()]).optional().default(1), reference_solution_1: SolutionAddress, reference_solution_2: SolutionAddress }).passthrough();
const PreferredSolutions = z.object({ preference_type: z.string().optional().default("preferred_solutions"), preferred_solutions: z.record(z.array(z.number())) }).passthrough();
const NonPreferredSolutions = z.object({ preference_type: z.string().optional().default("non_preferred_solutions"), non_preferred_solutions: z.record(z.array(z.number())) }).passthrough();
const PreferredRanges = z.object({ preference_type: z.string().optional().default("preferred_ranges"), preferred_ranges: z.record(z.array(z.number())) }).passthrough();
const EMOSolveRequest = z.object({ problem_id: z.number().int(), method: z.string().optional().default("NSGA3"), max_evaluations: z.number().int().optional().default(50000), number_of_vectors: z.number().int().optional().default(30), use_archive: z.boolean().optional().default(true), preference: z.union([ReferencePoint, PreferredSolutions, NonPreferredSolutions, PreferredRanges]), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional() }).passthrough();
const EMOState = z.object({ method: z.string().optional().default("EMO"), phase: z.string().optional().default("unset"), max_evaluations: z.number().int().optional().default(1000), number_of_vectors: z.number().int().optional().default(20), use_archive: z.boolean().optional().default(true), solutions: z.array(z.unknown()), outputs: z.array(z.unknown()) }).passthrough();
const UserSavedEMOResults = z.object({ optimal_variables: z.record(z.union([z.number(), z.number(), z.array(z.unknown())])), optimal_objectives: z.record(z.union([z.number(), z.array(z.number())])), constraint_values: z.union([z.record(z.union([z.number(), z.number(), z.array(z.number()), z.array(z.unknown())])), z.unknown(), z.null()]).optional(), extra_func_values: z.union([z.record(z.union([z.number(), z.array(z.number())])), z.null()]).optional(), name: z.union([z.string(), z.null()]).optional() }).passthrough();
const EMOSaveRequest = z.object({ problem_id: z.number().int(), session_id: z.union([z.number(), z.null()]).optional(), parent_state_id: z.union([z.number(), z.null()]).optional(), solutions: z.array(UserSavedEMOResults) }).passthrough();
const EMOResults = z.object({ optimal_variables: z.record(z.union([z.number(), z.number(), z.array(z.unknown())])), optimal_objectives: z.record(z.union([z.number(), z.array(z.number())])), constraint_values: z.union([z.record(z.union([z.number(), z.number(), z.array(z.number()), z.array(z.unknown())])), z.unknown(), z.null()]).optional(), extra_func_values: z.union([z.record(z.union([z.number(), z.array(z.number())])), z.null()]).optional() }).passthrough();
const EMOSaveState = z.object({ method: z.string().optional().default("EMO"), phase: z.string().optional().default("save_solutions"), max_evaluations: z.number().int().optional().default(1000), number_of_vectors: z.number().int().optional().default(20), use_archive: z.boolean().optional().default(true), problem_id: z.number().int(), saved_solutions: z.array(EMOResults), solutions: z.array(z.unknown()).optional() }).passthrough();
const UtopiaRequest = z.object({ problem_id: z.number().int(), solution: SolutionAddress }).passthrough();
const UtopiaResponse = z.object({ is_utopia: z.boolean(), map_name: z.string(), map_json: z.object({}).partial().passthrough(), options: z.object({}).partial().passthrough(), description: z.string(), years: z.array(z.string()) }).passthrough();

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
	BaseProblemMetaData,
	ProblemMetaDataPublic,
	ProblemInfoSmall,
	ConstantDB,
	Tensor,
	TensorConstantDB,
	VariableTypeEnum,
	VariableDB,
	TensorVariableDB,
	Url,
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
	ProblemMetaDataGetRequest,
	CreateSessionRequest,
	InteractiveSessionBase,
	GetSessionRequest,
	ReferencePoint,
	RPMSolveRequest,
	SolverResults,
	RPMState,
	NIMBUSClassificationRequest,
	SolutionAddress,
	UserSavedSolutionAddress,
	NIMBUSClassificationResponse,
	NIMBUSInitializationRequest,
	NIMBUSInitializationResponse,
	IntermediateSolutionResponse,
	NIMBUSSaveRequest,
	NIMBUSSaveResponse,
	IntermediateSolutionRequest,
	PreferredSolutions,
	NonPreferredSolutions,
	PreferredRanges,
	EMOSolveRequest,
	EMOState,
	UserSavedEMOResults,
	EMOSaveRequest,
	EMOResults,
	EMOSaveState,
	UtopiaRequest,
	UtopiaResponse,
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
		path: "/method/emo/save",
		alias: "save_method_emo_save_post",
		description: `Save solutions.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: EMOSaveRequest
			},
		],
		response: EMOSaveState,
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
		path: "/method/emo/saved-solutions",
		alias: "get_saved_solutions_method_emo_saved_solutions_get",
		description: `Get all saved solutions for the current user.`,
		requestFormat: "json",
		response: z.unknown(),
	},
	{
		method: "post",
		path: "/method/emo/solve",
		alias: "start_emo_optimization_method_emo_solve_post",
		description: `Start interactive evolutionary multiobjective optimization.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: EMOSolveRequest
			},
		],
		response: EMOState,
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
		response: z.array(z.any()).min(2).max(2),
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
		path: "/method/nimbus/initialize",
		alias: "initialize_method_nimbus_initialize_post",
		description: `Initialize the problem for the NIMBUS method.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: NIMBUSInitializationRequest
			},
		],
		response: z.union([NIMBUSClassificationResponse, NIMBUSInitializationResponse, IntermediateSolutionResponse]),
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
		path: "/method/nimbus/intermediate",
		alias: "solve_nimbus_intermediate_method_nimbus_intermediate_post",
		description: `Solve intermediate solutions by forwarding the request to generic intermediate endpoint with context nimbus.`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: IntermediateSolutionRequest
			},
		],
		response: IntermediateSolutionResponse,
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
		response: NIMBUSSaveResponse,
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
		response: NIMBUSClassificationResponse,
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
		response: ProblemInfo,
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
		path: "/problem/get_metadata",
		alias: "get_metadata_problem_get_metadata_post",
		description: `Fetch specific metadata for a specific problem. See all the possible metadata types from DESDEO/desdeo/api/models/problem.py Problem Metadata section.

Args:
    request (MetaDataGetRequest): requesting certain problem&#x27;s certain metadata
    user (Annotated[User, Depends]): the current user
    session (Annotated[Session, Depends]): the database session

Returns:
    list[Any] | None: list of all forest metadata for this problem, or nothing if there&#x27;s nothing`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: ProblemMetaDataGetRequest
			},
		],
		response: z.array(z.unknown()),
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
	{
		method: "post",
		path: "/utopia/",
		alias: "get_utopia_data_utopia__post",
		description: `Request and receive the Utopia map corresponding to the decision variables sent. Can be just the optimal_variables form a SolverResult

Args:
    request (UtopiaRequest): the set of decision variables and problem for which the utopia forest map is requested for.
    user (Annotated[User, Depend(get_current_user)]) the current user
    session (Annotated[Session, Depends(get_session)]) the current database session

Raises:
    HTTPException: 

Returns:
    UtopiaResponse: the map for the forest, to be rendered in frontend`,
		requestFormat: "json",
		parameters: [
			{
				name: "body",
				type: "Body",
				schema: UtopiaRequest
			},
		],
		response: UtopiaResponse,
		errors: [
			{
				status: 422,
				description: `Validation Error`,
				schema: HTTPValidationError
			},
		]
	},
]);

export const api = new Zodios(endpoints);

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
    return new Zodios(baseUrl, endpoints, options);
}
