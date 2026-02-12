import type { deleteProblemProblemProblemIdDeleteResponse } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { getProblemJsonProblemProblemIdJsonGetResponse } from '$lib/gen/endpoints/DESDEOFastAPI';
import { deleteProblemProblemProblemIdDelete } from '$lib/gen/endpoints/DESDEOFastAPI';
import { getProblemJsonProblemProblemIdJsonGet } from '$lib/gen/endpoints/DESDEOFastAPI';

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
