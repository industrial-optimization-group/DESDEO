import type {
	BodyAddProblemJsonProblemAddJsonPost,
	ConstraintDB,
	ConstantDB,
	ObjectiveDB,
	ProblemInfo,
	VariableDB
} from '$lib/gen/models';
import { addProblemJsonProblemAddJsonPost, addProblemProblemAddPost } from '$lib/gen/endpoints/DESDEOFastAPI';

export type ProblemPayload = {
	name: string;
	description: string;
	variables: VariableDB[];
	objectives: ObjectiveDB[];
	constants?: ConstantDB[] | null;
	constraints?: ConstraintDB[] | null;
	scenario_keys?: string[] | null;
	is_convex?: boolean | null;
	is_linear?: boolean | null;
	is_twice_differentiable?: boolean | null;
};

export type ProblemResponse =
	| { ok: true; data: ProblemInfo }
	| { ok: false; error: string; status?: number };

export async function createProblem(payload: ProblemPayload): Promise<ProblemResponse> {
	try {
		const response = await addProblemProblemAddPost({
			body: JSON.stringify(payload),
			headers: { 'Content-Type': 'application/json' }
		});

		if (response.status !== 200) {
			return { ok: false, error: 'Failed to create problem.', status: response.status };
		}

		return { ok: true, data: response.data };
	} catch (error) {
		console.error('createProblem error', error);
		return { ok: false, error: 'Unexpected error while creating problem.' };
	}
}

export async function uploadProblemJson(
	body: BodyAddProblemJsonProblemAddJsonPost
): Promise<ProblemResponse> {
	try {
		const response = await addProblemJsonProblemAddJsonPost(body);

		if (response.status !== 200) {
			return { ok: false, error: 'Failed to upload problem JSON.', status: response.status };
		}

		return { ok: true, data: response.data };
	} catch (error) {
		console.error('uploadProblemJson error', error);
		return { ok: false, error: 'Unexpected error while uploading JSON.' };
	}
}
