// Type definitions for EMO operations
export interface EMOSolveRequest {
  problem_id: number;
  method: 'NSGA3' | 'RVEA';
  preference: {
    aspiration_levels: Record<string, number>;
  };
  max_evaluations: number;
  number_of_vectors: number;
  use_archive: boolean;
  session_id?: number;
  parent_state_id?: number;
}

export interface EMOState {
  method: string;
  max_evaluations: number;
  number_of_vectors: number;
  use_archive: boolean;
  solutions: any[];
  outputs: any[];
}

export interface EMOSolution {
  variables?: Record<string, number>;
  objectives?: Record<string, number>;
  constraint_values?: Record<string, number>;
  extra_func_values?: Record<string, number>;
}

export interface UserSavedEMOResult {
  name: string;
  optimal_variables: Record<string, number>;
  optimal_objectives: Record<string, number>;
  constraint_values: Record<string, number>;
  extra_func_values: Record<string, number>;
}

export interface EMOSaveRequest {
  problem_id: number;
  solutions: UserSavedEMOResult[];
  session_id?: number;
  parent_state_id?: number;
}

export interface EMOSaveState {
  method: string;
  phase: 'save_solutions';
  problem_id: number;
  saved_solutions: any[];
}

export interface ActionResult {
  success?: boolean;
  error?: string;
  message?: string;
  data?: any;
}
