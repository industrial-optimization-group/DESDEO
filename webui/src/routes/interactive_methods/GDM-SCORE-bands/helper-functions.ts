/**
 * helper-functions.ts
 *
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created December 2025
 * @updated December 2025
 *
 * @description
 * Utility functions for GDM SCORE Bands visualization and group decision making.
 * Provides calculations for axis agreement analysis, visual styling generation,
 * scale computation, and voting charts using native SVG rendering.
 *
 * @functions
 * - calculateAxisAgreement: Analyzes voting patterns to determine agreement levels per axis
 * - generate_cluster_colors: Creates consistent color palette for cluster visualization
 * - generate_axis_options: Generates axis styling based on agreement levels
 * - calculateScales: Computes axis scales from problem definition or data
 * - drawVotesChart: Renders SVG voting chart without external dependencies
 *
 * @dependencies
 * - $lib/api/client-types for OpenAPI-generated TypeScript types
 * - Native SVG DOM manipulation (no external charting libraries)
 */
import type { components } from "$lib/api/client-types";


/**
 * Calculate agreement level for each axis based on voting data
 * 
 * Analyzes the spread of voted cluster medians on each axis to determine if voters
 * are in agreement, disagreement, or neutral. Uses normalized disagreement scores
 * based on the total objective range to classify agreement levels.
 * 
 * @param votes_and_confirms - Contains votes and confirms data from group voting
 * @param medians - Medians data from SCORE bands: {clusterId: {axisName: medianValue}}
 * @param scales - Scales data: {axisName: [ideal, nadir]} for normalization
 * @param agreementThreshold - Threshold below which we consider agreement (default: 0.1)
 * @param disagreementThreshold - Threshold above which we consider disagreement (default: 0.9)
 * @returns Agreement status per axis ('agreement' | 'disagreement' | 'neutral')
 */
export function calculateAxisAgreement(
    votes_and_confirms: {
        confirms: number[];
        votes: Record<number, number>;
    },
    medians: Record<string, Record<string, number>>,
    scales: Record<string, [number, number]>,
    agreementThreshold = 0.1,
    disagreementThreshold = 0.9
): Record<string, 'agreement' | 'disagreement' | 'neutral'> {
    const agreement: Record<string, 'agreement' | 'disagreement' | 'neutral'> = {};
    
    // Get bands that have votes
    const votedBandIds = Object.values(votes_and_confirms.votes || {});
    
    if (votedBandIds.length < 2) {
        // In the case of only one vote, just return neutral
        Object.keys(scales).forEach(axisName => {
            agreement[axisName] = 'neutral';
        });
        return agreement;
    }
    
    // For each axis, calculate agreement
    Object.keys(scales).forEach(axisName => {
        // Get medians for voted bands on this axis
        const votedMedians = votedBandIds
            .map(bandId => medians[bandId.toString()]?.[axisName])
            .filter(median => median !== undefined);
        
        // Calculate spread: max - min
        const maxMedian = Math.max(...votedMedians);
        const minMedian = Math.min(...votedMedians);
        const spread = maxMedian - minMedian;
        
        // Get nadir-ideal range for this axis
        const [nadir, ideal] = scales[axisName];
        const totalRange = Math.abs(nadir - ideal);
        
        // Calculate normalized disagreement score
        const disagreementScore = totalRange > 0 ? spread / totalRange : 0;
        
        // Classify agreement level
        if (disagreementScore <= agreementThreshold) {
            agreement[axisName] = 'agreement';
        } else if (disagreementScore >= disagreementThreshold) {
            agreement[axisName] = 'disagreement';
        } else {
            agreement[axisName] = 'neutral';
        }
    });
    
    return agreement;
}

/**
 * Generate consistent cluster colors from predefined palette
 * 
 * Maps cluster IDs to colors using a predefined color palette with good contrast.
 * Colors cycle through the palette if more clusters exist than available colors.
 * 
 * @param clusterIds - Array of cluster IDs to assign colors to
 * @returns Record mapping cluster ID to hex color string
 */
export function generate_cluster_colors(clusterIds: number[]): Record<number, string> {
    const color_palette = [
        '#1f77b4', // Strong blue
        '#ff7f0e', // Vibrant orange
        '#2ca02c', // Strong green
        '#d62728', // Bold red
        '#9467bd', // Purple
        '#8c564b', // Brown
        '#e377c2', // Pink
        '#7f7f7f', // Gray
        '#bcbd22', // Olive/yellow-green
        '#17becf' // Cyan
    ];

    const cluster_colors: Record<number, string> = {};

    clusterIds.forEach((clusterId, index) => {
        cluster_colors[clusterId] = color_palette[index % color_palette.length];
    });

    return cluster_colors;
}

/**
 * Generate axis styling options based on agreement levels
 * 
 * Creates visual styling for axes based on calculated agreement levels.
 * Agreement axes are green with dashed lines, disagreement axes are red with thick dashed lines,
 * and neutral/unknown axes are gray with solid lines.
 * 
 * TODO: maybe here or maybe in the visualization component:
 * make different axis styles more visible.
 * 
 * @param axisNames - Array of axis names to generate options for
 * @param axis_agreement - Agreement status per axis, or null if not calculated
 * @returns Array of styling options with color, strokeWidth, and strokeDasharray properties
 */
export function generate_axis_options(axisNames: string[], axis_agreement: Record<string, 'agreement' | 'disagreement' | 'neutral'> | null) {
    return axisNames.map((axisName) => {
        if(axis_agreement && axisName in axis_agreement) {
            // Set specific styles for axis 1 (green) and axis 3 (red)
            if (axis_agreement[axisName] === 'agreement') {
                return {
                    color: '#15803d', // Green for agreement
                    strokeWidth: 2,
                    strokeDasharray: '5,5'
                };
            }
            if (axis_agreement[axisName] === 'disagreement') {
                return {
                    color: '#b91c1c', // Red for disagreement
                    strokeWidth: 3,
                    strokeDasharray: '5,5' // Dashed line
                };
            }
    }
        // Default gray color and solid line for all other axes
        return {
            color: '#666666', // Gray for all other axes
            strokeWidth: 1,
            strokeDasharray: 'none'
        };
    });
}

/**
 * Calculate axis scales for SCORE bands visualization
 * 
 * Determines the min/max range for each axis using a priority order:
 * 1. Problem definition (ideal/nadir from objectives)
 * 2. API-provided scales from result.options.scales
 * 3. Fallback: calculate from actual bands and medians data
 * 
 * TODO: When API scales functionality is fully implemented, prioritize using 
 * result.options.scales over problem definition. Evaluate if fallback calculation
 * from bands data is still needed or should be removed.
 * 
 * @param problem - Problem definition containing objectives with ideal/nadir values
 * @param result - SCORE bands result containing bands data and configuration
 * @returns Record mapping axis name to [min, max] range tuple
 */
export function calculateScales(problem: components['schemas']['ProblemInfo'], result: components['schemas']['SCOREBandsResult']): Record<string, [number, number]> {
    // First, try to use ideal and nadir from problem definition
    const scales: Record<string, [number, number]> = {};
    let allObjectivesHaveScales = true;
    
    problem.objectives.forEach((objective: any) => {
        const name = objective.name;
        const ideal = objective.ideal;
        const nadir = objective.nadir;
        if (ideal !== undefined && nadir !== undefined) {
            scales[name] = [nadir, ideal];
        } else {
            allObjectivesHaveScales = false;
        }
    });
    
    // Only use problem scales if ALL objectives have complete ideal/nadir values
    if (allObjectivesHaveScales && Object.keys(scales).length === problem.objectives.length) {
        return scales;
    }
    
    // Second, try to use scales from API
    if (result.options?.scales) {
        return result.options.scales;
    }
    
    // Fallback: calculate scales from bands data
    const fallbackScales: Record<string, [number, number]> = {};
    
    result.ordered_dimensions.forEach(axisName => {
        let min = Infinity;
        let max = -Infinity;
        
        // Find min/max across all clusters for this axis
        Object.values(result.bands).forEach(clusterBands => {
            if (clusterBands[axisName]) {
                const [bandMin, bandMax] = clusterBands[axisName];
                min = Math.min(min, bandMin);
                max = Math.max(max, bandMax);
            }
        });
        
        // Also check medians for additional range
        Object.values(result.medians).forEach(clusterMedians => {
            if (clusterMedians[axisName] !== undefined) {
                const median = clusterMedians[axisName];
                min = Math.min(min, median);
                max = Math.max(max, median);
            }
        });
        
        fallbackScales[axisName] = [min, max];
    });
    
    return fallbackScales;
}

/**
 * Draw voting results as SVG bar chart
 * 
 * Renders a vertical bar chart showing vote distribution across clusters using native SVG.
 * Only displays clusters that have received at least one vote. Each bar shows the vote count
 * and is colored according to the cluster's assigned color scheme.
 * 
 * @param container - HTML container element to render the chart into
 * @param votes_per_cluster - Record mapping cluster ID to vote count
 * @param totalVoters - Total number of voters for reference and scaling
 * @param cluster_colors - Record mapping cluster ID to hex color string
 */
export function drawVotesChart(
    container: HTMLElement,
    votes_per_cluster: Record<number, number>,
    totalVoters: number,
    cluster_colors: Record<number, string>
): void {
    const width = 300;
    const height = 200;
    const margin = { top: 30, right: 20, bottom: 40, left: 40 };
    
    // Filter to only show clusters with votes > 0
    const clustersWithVotes = Object.entries(votes_per_cluster)
        .filter(([_, votes]) => votes > 0)
        .map(([clusterId, votes]) => ({
            clusterId: Number(clusterId),
            name: `Cluster ${clusterId}`,
            votes: votes
        }));
    
    // If no votes, don't draw anything
    if (clustersWithVotes.length === 0) {
        container.innerHTML = '<p class="text-sm text-gray-500 p-4">No votes yet</p>';
        return;
    }
    
    // Clear previous chart
    container.innerHTML = '';
    
    // Create SVG
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', width.toString());
    svg.setAttribute('height', height.toString());
    container.appendChild(svg);
    
    // Create title
    const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    title.setAttribute('x', (width / 2).toString());
    title.setAttribute('y', '20');
    title.setAttribute('text-anchor', 'middle');
    title.setAttribute('font-size', '14');
    title.setAttribute('font-weight', 'bold');
    title.setAttribute('fill', '#333');
    title.textContent = 'Votes';
    svg.appendChild(title);
    
    // Calculate scales
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    
    const xScale = innerWidth / clustersWithVotes.length;
    const maxVotes = Math.max(...clustersWithVotes.map(d => d.votes), totalVoters);
    const yScale = innerHeight / maxVotes;
    
    // Draw bars
    clustersWithVotes.forEach((cluster, index) => {
        const barWidth = xScale * 0.8; // 80% of available space
        const barHeight = cluster.votes * yScale;
        const x = margin.left + (index * xScale) + (xScale * 0.1); // 10% padding on each side
        const y = margin.top + innerHeight - barHeight;
        
        // Bar
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', x.toString());
        rect.setAttribute('y', y.toString());
        rect.setAttribute('width', barWidth.toString());
        rect.setAttribute('height', barHeight.toString());
        rect.setAttribute('fill', cluster_colors[cluster.clusterId] || '#666666');
        rect.setAttribute('opacity', '0.7');
        rect.setAttribute('stroke', '#333');
        rect.setAttribute('stroke-width', '1');
        svg.appendChild(rect);
        
        // Value label on top of bar
        const valueLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        valueLabel.setAttribute('x', (x + barWidth / 2).toString());
        valueLabel.setAttribute('y', (y+20).toString());
        valueLabel.setAttribute('text-anchor', 'middle');
        valueLabel.setAttribute('font-size', '12');
        valueLabel.setAttribute('font-weight', 'bold');
        valueLabel.setAttribute('fill', '#333');
        valueLabel.textContent = `${cluster.votes}/${totalVoters}`;
        svg.appendChild(valueLabel);
        
        // Cluster label below bar
        const clusterLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        clusterLabel.setAttribute('x', (x + barWidth / 2).toString());
        clusterLabel.setAttribute('y', (margin.top + innerHeight + 15).toString());
        clusterLabel.setAttribute('text-anchor', 'middle');
        clusterLabel.setAttribute('font-size', '10');
        clusterLabel.setAttribute('fill', '#666');
        clusterLabel.textContent = cluster.name;
        svg.appendChild(clusterLabel);
    });
    
    // Draw Y-axis
    const yAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    yAxis.setAttribute('x1', margin.left.toString());
    yAxis.setAttribute('y1', margin.top.toString());
    yAxis.setAttribute('x2', margin.left.toString());
    yAxis.setAttribute('y2', (margin.top + innerHeight).toString());
    yAxis.setAttribute('stroke', '#333');
    yAxis.setAttribute('stroke-width', '1');
    svg.appendChild(yAxis);
    
    // Draw X-axis
    const xAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    xAxis.setAttribute('x1', margin.left.toString());
    xAxis.setAttribute('y1', (margin.top + innerHeight).toString());
    xAxis.setAttribute('x2', (margin.left + innerWidth).toString());
    xAxis.setAttribute('y2', (margin.top + innerHeight).toString());
    xAxis.setAttribute('stroke', '#333');
    xAxis.setAttribute('stroke-width', '1');
    svg.appendChild(xAxis);
}
