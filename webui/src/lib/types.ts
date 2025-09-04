import type { components } from '$lib/api/client-types';

/*Types for the entire UI*/

export type ProblemInfo = components['schemas']['ProblemInfo'];
export type Solution = components['schemas']['SolutionReferenceResponse'];

export type MethodMode = 'iterate' | 'final' | 'intermediate';
export type SolutionType = 'current' | 'best' | 'all';

export type DialogConfig = {
	open: boolean;
	title: string;
	description: string;
	confirmText: string;
	cancelText: string;
	onConfirm: () => void;
	onCancel?: () => void;
	confirmVariant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
};
/*Related to UTOPIA: SHUOLD BE MOVED ELSEWHERE */
export type PeriodKey = 'period1' | 'period2' | 'period3';

// Common base response type that all NIMBUS method responses share
export type BaseMethodResponse = {
    state_id: number | null;
    current_solutions: Solution[];
    saved_solutions: Solution[];
    all_solutions: Solution[];
};

export interface MethodHandlers<T extends BaseMethodResponse = BaseMethodResponse> {
	handle_initial_solutions: (problem: ProblemInfo) => Promise<Solution[] | null>;
	handle_intermediate_solutions: (problem: ProblemInfo, current_preference: number[], current_num_intermediate_solutions: number) => Promise<Solution[] | null>;
	handle_iterate: (problem: ProblemInfo, current_preference: number[], selected_iteration_objectives: Record<string, number>, current_num_iteration_solutions: number) => Promise<T | null>;
	handle_end: (problem: ProblemInfo | null, solutions: Solution[]) => Promise<boolean>;
}
