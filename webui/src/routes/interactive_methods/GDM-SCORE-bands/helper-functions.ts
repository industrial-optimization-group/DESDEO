// /**
//  * Calculate agreement level for each axis based on voting data
//  * @param {Object} votes_and_confirms - Contains votes and confirms data
//  * @param {Object} medians - Medians data from SCORE bands: {clusterId: {axisName: medianValue}}
//  * @param {Object} scoreBandsResult - Full SCORE bands result with scales info
//  * @param {number} agreementThreshold - Threshold below which we consider agreement (e.g., 0.1)
//  * @param {number} disagreementThreshold - Threshold above which we consider disagreement (e.g., 0.9)
//  * @returns {Record<string, 'agreement' | 'disagreement' | 'neutral'>} - Agreement status per axis
//  */
// function calculateAxisAgreement(
//     votes_and_confirms: {
//         confirms: number[];
//         votes: Record<number, number>;
//     },
//     medians,
//     scoreBandsResult,
//     agreementThreshold = 0.1,
//     disagreementThreshold = 0.9
// ): Record<string, 'agreement' | 'disagreement' | 'neutral'> {
//     const agreement = {};
    
//     // Get bands that have votes
//     const votedBandIds = Object.values(votes_and_confirms.votes || {});
//     const uniqueVotedBands = [...new Set(votedBandIds)];
    
//     if (uniqueVotedBands.length < 2) {
//         // If less than 2 bands voted for, no disagreement possible
//         scoreBandsResult.ordered_dimensions.forEach(axisName => {
//             agreement[axisName] = 'neutral';
//         });
//         return agreement;
//     }
    
//     // For each axis, calculate agreement
//     scoreBandsResult.ordered_dimensions.forEach(axisName => {
//         // Get medians for voted bands on this axis
//         const votedMedians = uniqueVotedBands
//             .map(bandId => medians[bandId.toString()]?.[axisName])
//             .filter(median => median !== undefined);
            
//         if (votedMedians.length < 2) {
//             agreement[axisName] = 'neutral';
//             return;
//         }
        
//         // Calculate spread: max - min
//         const maxMedian = Math.max(...votedMedians);
//         const minMedian = Math.min(...votedMedians);
//         const spread = maxMedian - minMedian;
        
//         // Get nadir-ideal range for this axis
//         let totalRange;
//         if (scoreBandsResult.options?.scales?.[axisName]) {
//             const [idealValue, nadirValue] = scoreBandsResult.options.scales[axisName];
//             totalRange = Math.abs(nadirValue - idealValue);
//         } else {
//             // Fallback: calculate from all available medians and bands
//             let allValues = [];
//             Object.values(medians).forEach(clusterMedians => {
//                 if (clusterMedians[axisName] !== undefined) {
//                     allValues.push(clusterMedians[axisName]);
//                 }
//             });
//             Object.values(scoreBandsResult.bands).forEach(clusterBands => {
//                 if (clusterBands[axisName]) {
//                     allValues.push(...clusterBands[axisName]);
//                 }
//             });
//             totalRange = allValues.length > 0 ? Math.max(...allValues) - Math.min(...allValues) : 1;
//         }
        
//         // Calculate normalized disagreement score
//         const disagreementScore = totalRange > 0 ? spread / totalRange : 0;
        
//         // Classify agreement level
//         if (disagreementScore <= agreementThreshold) {
//             agreement[axisName] = 'agreement';
//         } else if (disagreementScore >= disagreementThreshold) {
//             agreement[axisName] = 'disagreement';
//         } else {
//             agreement[axisName] = 'neutral';
//         }
//     });
    
//     return agreement;
// }

/**
 * Draws a vertical bar chart showing votes per cluster using D3.
 * @param container - HTML container element for the chart
 * @param votes_per_cluster - Record mapping cluster ID to vote count
 * @param totalVoters - Total number of voters for reference
 * @param cluster_colors - Record mapping cluster ID to color string
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
