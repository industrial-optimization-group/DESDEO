import * as d3 from "d3";
import { getClusterColor } from "../utils/helpers";

interface BandDrawOptions {
  quantile: number;
  showMedian?: boolean;
  showSolutions?: boolean;
  bandOpacity?: number;
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
