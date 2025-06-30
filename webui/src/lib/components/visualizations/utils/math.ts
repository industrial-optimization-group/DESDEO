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