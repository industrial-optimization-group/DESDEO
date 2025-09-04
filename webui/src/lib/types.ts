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
