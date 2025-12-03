export function normalize(value: number, min: number, max: number): number {
    if (max === min) return 0.5;
    return (value - min) / (max - min);
}

export function getValueRange(data: { value: number }[], axisRanges?: [number, number][]): [number, number] {
    if (axisRanges && axisRanges.length === 1) {
        const [min, max] = axisRanges[0];
        if (isFinite(min) && isFinite(max) && min < max) return [min, max];
    }
    const values = data.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    if (min === max) return [min - 1, max + 1];
    return [min, max];
}

export function roundToDecimal(val: number, decimals = 2) {
	return Math.round(val * 10 ** decimals) / 10 ** decimals;
}

export function normalize_data(input_data: number[][]): number[][] {
	if (input_data.length === 0) return input_data;

	const num_objectives = input_data[0].length;
	const normalized_data: number[][] = [];

	// Find min and max for each objective
	const min_values = new Array(num_objectives).fill(Infinity);
	const max_values = new Array(num_objectives).fill(-Infinity);

	// Calculate min and max for each column
	for (const row of input_data) {
		for (let j = 0; j < num_objectives; j++) {
			min_values[j] = Math.min(min_values[j], row[j]);
			max_values[j] = Math.max(max_values[j], row[j]);
		}
	}

	// Normalize each row
	for (const row of input_data) {
		const normalized_row: number[] = [];
		for (let j = 0; j < num_objectives; j++) {
			const range = max_values[j] - min_values[j];
			if (range === 0) {
				// If all values are the same, set to 0.5
				normalized_row.push(0.5);
			} else {
				const normalized_value = (row[j] - min_values[j]) / range;
				normalized_row.push(normalized_value);
			}
		}
		normalized_data.push(normalized_row);
	}

	return normalized_data;
}