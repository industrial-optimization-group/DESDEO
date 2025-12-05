import * as d3 from "d3";
import { getClusterColor } from "../utils/helpers";

interface BandDrawOptions {
  quantile: number;
  showMedian?: boolean;
  showSolutions?: boolean;
  bandOpacity?: number;
  bands?: boolean;  // Add this for pre-calculated bands
}

export function drawBand(
  svg: any,
  rows: { values: number[] }[],
  groupId: number,
  xPositions: number[],
  yScales: d3.ScaleLinear<number, number>[],
  clusterColors: Record<number, string>,
  options: BandDrawOptions,
  isSelected: boolean,
  onBandSelect?: (clusterId: number | null) => void
) {
  if (rows.length === 0) return;
  const numAxes = xPositions.length;
  const clusterColor = getClusterColor(groupId, clusterColors);

  // --- Compute stats ---
  const bandData = d3.transpose(rows.map((d) => d.values));
  const low = bandData.map((arr) => d3.quantile(arr.sort(d3.ascending), options.quantile)!);
  const high = bandData.map((arr) => d3.quantile(arr.sort(d3.ascending), 1 - options.quantile)!);
  const medians = bandData.map((arr) => d3.median(arr.sort(d3.ascending))!);

  // --- Band ---
  const area = d3.area<number>()
    .x((_, i) => xPositions[i])
    .y0((_, i) => yScales[i](low[i]))
    .y1((_, i) => yScales[i](high[i]))
    .curve(d3.curveMonotoneX);

  const bandElement = svg.append("path")
    .datum(Array(numAxes).fill(0))
    .attr("fill", clusterColor)
    .attr("opacity", isSelected ? 0.7 : options.bandOpacity ?? 0.5)
    .attr("stroke", isSelected ? "#000" : "none")
    .attr("stroke-width", isSelected ? 2 : 0)
    .attr("d", area)
    .style("cursor", "pointer");

  if (onBandSelect) {
    bandElement.on("click", (event) => {
      event.stopPropagation();
      onBandSelect(isSelected ? null : groupId);
    });
  }

  // --- Median ---
  if (options.showMedian) {
    const line = d3.line<number>()
      .x((_, i) => xPositions[i])
      .y((_, i) => yScales[i](medians[i]))
      .curve(d3.curveMonotoneX);

    svg.append("path")
      .datum(medians)
      .attr("fill", "none")
      .attr("stroke", clusterColor)
      .attr("stroke-width", 2)
      .attr("opacity", 0.9)
      .attr("d", line);
  }

  // --- Individual solutions ---
  if (options.showSolutions) {
    const line = d3.line<number>()
      .x((_, i) => xPositions[i])
      .y((val, i) => yScales[i](val))
      .curve(d3.curveMonotoneX);

    rows.forEach((d) => {
      svg.append("path")
        .datum(d.values)
        .attr("fill", "none")
        .attr("stroke", clusterColor)
        .attr("stroke-opacity", 0.3)
        .attr("stroke-width", 1)
        .attr("d", line);
    });
  }
}



	/**
	 * Draws a single cluster using pre-calculated band and median data
	 */
	export function drawPreCalculatedCluster(
		svg: any,
		clusterId: number,
		bandsData: Record<string, Record<string, [number, number]>>,
		mediansData: Record<string, Record<string, number>>,
		axisNames: string[],
		xPositions: number[],
		yScales: any[],
		clusterColors: Record<number, string>,
		axisSigns: number[],
		options: any,
		isSelected: boolean,
		scales: Record<string, [number, number]> | undefined,
		onBandSelect?: (clusterId: number | null) => void
	) {
		const clusterColor = clusterColors[clusterId] || '#1f77b4';
		const clusterKey = clusterId.toString();
		
		// Get band and median data for this cluster
		const clusterBands = bandsData[clusterKey]; // Record<string, [number, number]>
		const clusterMedians = mediansData[clusterKey]; // Record<string, number>
		
		if (!clusterBands || !clusterMedians) {
			console.warn(`No data for cluster ${clusterId} (key: ${clusterKey})`);
			return;
		}

		// Helper function to normalize raw value to [0,1] using scales
		function normalizeValue(rawValue: number, axisName: string): number {
			if (!scales || !scales[axisName]) {
				console.warn(`No scales available for axis ${axisName}, using raw value as normalized`);
				return rawValue;
			}
			
			const [min, max] = scales[axisName];
			if (max === min) {
				console.warn(`Min equals max for axis ${axisName}: [${min}, ${max}], returning 0.5`);
				return 0.5;
			}
			
			const normalized = (rawValue - min) / (max - min);
			// Clamp to [0,1] range in case of edge cases
			return Math.max(0, Math.min(1, normalized));
		}

		// Prepare data arrays, normalizing raw values and applying axis signs for flipping
		const low: number[] = [];
		const high: number[] = [];
		const medians: number[] = [];

		for (let axisIndex = 0; axisIndex < axisNames.length; axisIndex++) {
			const axisName = axisNames[axisIndex];
			const [rawMinVal, rawMaxVal] = clusterBands[axisName] || [0, 1];
			const rawMedianVal = clusterMedians[axisName] ?? 0.5;
			
			// Normalize raw values to [0,1] using scales
			const normalizedMin = normalizeValue(rawMinVal, axisName);
			const normalizedMax = normalizeValue(rawMaxVal, axisName);
			const normalizedMedian = normalizeValue(rawMedianVal, axisName);
			
			const sign = axisSigns[axisIndex] || 1;
			
			// Apply axis flipping if needed (invert normalized values)
			if (sign === -1) {
				low.push(1 - normalizedMax);
				high.push(1 - normalizedMin);
				medians.push(1 - normalizedMedian);
			} else {
				low.push(normalizedMin);
				high.push(normalizedMax);
				medians.push(normalizedMedian);
			}
		}

		// --- Draw Band ---
		if (options.bands) {
			const area = d3.area<number>()
				.x((_, i) => xPositions[i])
				.y0((_, i) => yScales[i](low[i]))
				.y1((_, i) => yScales[i](high[i]))
				.curve(d3.curveMonotoneX);

			const bandElement = svg.append("path")
				.datum(Array(axisNames.length).fill(0))
				.attr("fill", clusterColor)
				.attr("opacity", isSelected ? 0.7 : 0.5)
				.attr("stroke", isSelected ? "#000" : "none")
				.attr("stroke-width", isSelected ? 2 : 0)
				.attr("d", area)
				.style("cursor", "pointer");

			if (onBandSelect) {
				bandElement.on("click", (event: any) => {
					event.stopPropagation();
					onBandSelect(isSelected ? null : clusterId);
				});
			}
		}

		// --- Draw Median ---
		if (options.medians) {
			const line = d3.line<number>()
				.x((_, i) => xPositions[i])
				.y((_, i) => yScales[i](medians[i]))
				.curve(d3.curveMonotoneX);

			svg.append("path")
				.datum(medians)
				.attr("fill", "none")
				.attr("stroke", clusterColor)
				.attr("stroke-width", 2)
				.attr("opacity", 0.9)
				.attr("d", line);
		}
	}
