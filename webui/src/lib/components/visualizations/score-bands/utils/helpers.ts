import type { AxisOptions } from "./types";

// --- Helper function to get axis style options ---
export function getAxisOptions(axisIndex: number, axisOptions: AxisOptions[]): {
		color: string;
		strokeWidth: number;
		strokeDasharray: string;
	} {
		const options = axisOptions[axisIndex] || {};
		return {
			color: options.color || '#333333',
			strokeWidth: options.strokeWidth || 1,
			strokeDasharray: options.strokeDasharray || 'none'
		};
	}

export function getClusterColor(clusterId: number, clusterColors: Record<number, string>): string {
	return clusterColors[clusterId] || '#999999';
}