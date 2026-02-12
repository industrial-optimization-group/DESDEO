import type { deleteProblemProblemProblemIdDeleteResponse } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { getProblemJsonProblemProblemIdJsonGetResponse } from '$lib/gen/endpoints/DESDEOFastAPI';
import { deleteProblemProblemProblemIdDelete } from '$lib/gen/endpoints/DESDEOFastAPI';
import { getProblemJsonProblemProblemIdJsonGet } from '$lib/gen/endpoints/DESDEOFastAPI';
import { getMetadataProblemGetMetadataPost } from '$lib/gen/endpoints/DESDEOFastAPI';
import { getAvailableSolversProblemAssignSolverGet } from '$lib/gen/endpoints/DESDEOFastAPI';
import { selectSolverProblemAssignSolverPost } from '$lib/gen/endpoints/DESDEOFastAPI';
import { addRepresentativeSolutionSetProblemAddRepresentativeSolutionSetPost } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { RepresentativeSolutionSetRequest } from '$lib/gen/models';

export async function deleteProblem(problemId: number): Promise<boolean> {
	const response: deleteProblemProblemProblemIdDeleteResponse =
		await deleteProblemProblemProblemIdDelete(problemId);

	if (response.status !== 204) {
		console.error('Failed to delete problem:', response.status);
		return false;
	}

	return true;
}

export async function downloadProblemJson(problemId: number, problemName: string): Promise<void> {
	const response: getProblemJsonProblemProblemIdJsonGetResponse =
		await getProblemJsonProblemProblemIdJsonGet(problemId);

	if (response.status !== 200) {
		console.error('Failed to download problem:', response.status);
		return;
	}

	const blob = new Blob([JSON.stringify(response.data, null, 4)], { type: 'application/json' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = `${problemName || 'problem'}.json`;
	a.click();
	URL.revokeObjectURL(url);
}

export async function getAssignedSolver(problemId: number): Promise<string | null> {
	const response = await getMetadataProblemGetMetadataPost({
		problem_id: problemId,
		metadata_type: 'solver_selection_metadata'
	});

	if (response.status !== 200 || !response.data?.length) {
		return null;
	}

	return (response.data[0] as any).solver_string_representation;
}

export async function getAvailableSolvers(): Promise<string[]> {
	const response = await getAvailableSolversProblemAssignSolverGet();

	if (response.status !== 200) {
		console.error('Failed to fetch available solvers:', response.status);
		return [];
	}

	return response.data;
}

export async function assignSolver(problemId: number, solver: string): Promise<boolean> {
	const response = await selectSolverProblemAssignSolverPost({
		problem_id: problemId,
		solver_string_representation: solver
	});

	if (response.status !== 200) {
		console.error('Failed to assign solver:', response.status);
		return false;
	}

	return true;
}

export async function addRepresentativeSolutionSet(
	payload: RepresentativeSolutionSetRequest
): Promise<boolean> {
	const response =
		await addRepresentativeSolutionSetProblemAddRepresentativeSolutionSetPost(payload);

	if (response.status !== 200) {
		console.error('Failed to add representative solution set:', response.status);
		return false;
	}

	return true;
}
