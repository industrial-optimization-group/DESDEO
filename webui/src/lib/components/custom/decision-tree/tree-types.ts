/** Re-export generated types and define frontend-only types for the decision tree. */

export type {
    ENautilusTreeNodeResponse as TreeNodeResponse,
    ENautilusDecisionEventResponse as DecisionEventResponse,
    ENautilusSessionTreeResponse as SessionTreeResponse,
} from "$lib/gen/models";

import type { ENautilusTreeNodeResponse } from "$lib/gen/models";

/** Internal node type used for d3-hierarchy. */
export interface TreeHierarchyDatum {
    id: number;
    node: ENautilusTreeNodeResponse;
    children: TreeHierarchyDatum[];
}
