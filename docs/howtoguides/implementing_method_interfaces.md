# Implementing method interfaces in the Web-GUI

This guide explains how to implement a new interactive method interface in
DESDEO's Web-GUI. It covers the file structure, the separation between API
handling and UI logic, and how to reuse existing components.

This guide is meant as a general guideline, not as an absolute pattern.

!!! note "Prerequisites"
    - A working API endpoint for the method (defined in `desdeo/api/routers/`).
    - The endpoint registered in the FastAPI app.
    - Orval-generated TypeScript types and endpoint functions
      (run `npm run generate:client` after adding API endpoints).

## File structure

Each method lives in its own SvelteKit route directory:

```
webui/src/routes/interactive_methods/<METHOD>/
    +page.ts            # Data loader, fetches problems, passes to page
    handler.ts          # API interaction layer, wraps orval endpoints
    +page.svelte        # UI component, state, interaction, rendering
    +page.server.ts     # (optional) Server-side auth guard
    types.ts            # (optional) Method-specific TypeScript types
    helper-functions.ts # (optional) Pure utility functions
```

### Why this structure?

- `handler.ts` isolates all API calls. The page component never imports
  orval endpoints directly.
- `+page.ts` runs before the page renders, loading data the component needs
  (e.g., the problem list).
- `+page.svelte` focuses on state management and rendering, delegating API
  work to the handler.
- `types.ts` and `helper-functions.ts` keep the main files focused.

## The handler pattern

**Design principle: separate API handling from UI logic.**

Each function in `handler.ts` wraps a single orval-generated endpoint. It calls
the endpoint, checks the response status, and returns typed data or `null` on
failure. The page component never sees raw HTTP responses. You should never
have the need to manually specify URL's or endpoints; these should be handled
through the Orval generated client. Otherwise, you might run into
problems with user validation, for instance.

### Example: E-NAUTILUS handler

```typescript
// handler.ts
import type { ENautilusStepRequest, ENautilusStepResponse } from "$lib/gen/endpoints/DESDEOFastAPI";
import type { stepMethodEnautilusStepPostResponse } from "$lib/gen/endpoints/DESDEOFastAPI";
import { stepMethodEnautilusStepPost } from "$lib/gen/endpoints/DESDEOFastAPI";

export async function initialize_enautilus_state(
    request: ENautilusStepRequest
): Promise<ENautilusStepResponse | null> {
    const response: stepMethodEnautilusStepPostResponse =
        await stepMethodEnautilusStepPost(request);

    if (response.status != 200) {
        console.log("E-NAUTILUS init failed.", response.status);
        return null;
    }

    return response.data;
}
```

Key points:

- Typed inputs and outputs: the function signature documents what it expects and returns.
- Status check: the handler decides what constitutes success, not the UI.
- Returns `null` on failure: the page component checks for `null` and logs an error.

### Re-exporting shared handlers

Methods often need session management. Rather than reimplementing it, re-export from the shared session handler:

```typescript
// handler.ts or +page.svelte
import { fetch_sessions, create_session } from '../../methods/sessions/handler';
export { fetch_sessions, create_session };
```

## The page loader (`+page.ts`)

The loader fetches data before the page renders. Most methods need the problem list:

```typescript
// +page.ts
import type { PageLoad } from './$types';
import { getProblemsInfoProblemAllInfoGet } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';

type ProblemList = ProblemInfo[];

export const load: PageLoad = async () => {
    const res = await getProblemsInfoProblemAllInfoGet();
    if (res.status !== 200) throw new Error('Failed to fetch problems');
    return { problems: res.data satisfies ProblemList };
};
```

## Reusable components

The Web-GUI provides several composable components that handle common UI
patterns across all methods.  These should be reused, when possible.

### Layout

Every method page should use one of the layout components from `$lib/components/custom/method_layout/`:

- `base-layout.svelte`: Simple flexbox layout with left sidebar, resizable center panes, and optional right sidebar.
- `explainable-layout.svelte`: — Enhanced grid layout with sidebar state management. Use this for methods that need the advanced/explainable sidebar.

Both layouts use Svelte 5 snippets for their slots:

```svelte
<BaseLayout showLeftSidebar={true} showRightSidebar={false}>
    {#snippet leftSidebar()}
        <!-- Preference controls go here -->
    {/snippet}

    {#snippet visualizationArea()}
        <!-- Charts and plots go here -->
    {/snippet}

    {#snippet numericalValues()}
        <!-- Solution tables go here -->
    {/snippet}
</BaseLayout>
```

### Preferences sidebar

`$lib/components/custom/preferences-bar/preferences-sidebar.svelte` handles preference input for methods that use reference points, aspiration levels, or classifications.

```svelte
<PreferencesSidebar
    {problem}
    preferenceTypes={PREFERENCE_TYPES}
    typePreferences={type_preferences}
    preferenceValues={current_preference}
    objectiveValues={current_objectives}
    numSolutions={num_solutions}
    onPreferenceChange={handle_preference_change}
/>
```

### Visualizations panel

`$lib/components/custom/visualizations-panel/visualizations-panel.svelte` renders parallel coordinate plots for comparing solutions.

```svelte
<VisualizationsPanel
    {problem}
    previousPreferenceValues={[last_preference]}
    currentPreferenceValues={current_preference}
    previousPreferenceType={type_preferences}
    currentPreferenceType={type_preferences}
    solutionsObjectiveValues={objective_values_matrix}
    externalSelectedIndexes={selected_indexes}
    onSelectSolution={handle_select}
/>
```

### Solution table

`$lib/components/custom/nimbus/solution-table.svelte` provides a data table with sorting, pagination, save/bookmark, and selection.

```svelte
<SolutionTable
    {problem}
    solverResults={solutions}
    selectedSolutions={selected_indexes}
    handle_row_click={handle_solution_click}
    handle_save={handle_save}
    isSaved={is_saved}
/>
```

### Dialogs

Reusable dialog utilities from `$lib/components/custom/dialogs/dialogs`:

```typescript
import { openConfirmDialog, openInputDialog, openHelpDialog } from '$lib/components/custom/dialogs/dialogs';

// Confirmation before destructive action
const confirmed = await openConfirmDialog("Revert to this iteration?", "This cannot be undone.");

// Prompt for user input
const name = await openInputDialog("Save solution", "Enter a name:");
```

## Putting it together

The data flow through a method interface follows this pattern:

```
+page.ts (load problems)
    |
    v
+page.svelte (receive data as props, manage state)
    |
    |--- user interacts (clicks iterate, selects solution, etc.)
    |       |
    |       v
    |   handler.ts (call API, return typed data)
    |       |
    |       v
    |--- update state ($state variables)
    |       |
    |       v
    |--- components react (visualizations, tables, sidebars re-render)
```

### Minimal skeleton

**handler.ts:**
```typescript
import { myMethodSolvePost } from "$lib/gen/endpoints/DESDEOFastAPI";
import type { MyMethodRequest, MyMethodResponse } from "$lib/gen/endpoints/DESDEOFastAPI";

export async function solve(request: MyMethodRequest): Promise<MyMethodResponse | null> {
    const response = await myMethodSolvePost(request);
    if (response.status !== 200) {
        console.error("Solve failed:", response.status);
        return null;
    }
    return response.data;
}
```

**+page.ts:**
```typescript
import type { PageLoad } from './$types';
import { getProblemsInfoProblemAllInfoGet } from '$lib/gen/endpoints/DESDEOFastAPI';

export const load: PageLoad = async () => {
    const res = await getProblemsInfoProblemAllInfoGet();
    if (res.status !== 200) throw new Error('Failed to fetch problems');
    return { problems: res.data };
};
```

**+page.svelte:**
```typescript
<script lang="ts">
    import { BaseLayout } from '$lib/components/custom/method_layout';
    import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
    import { solve } from './handler';
    import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';

    const { data } = $props();
    let problem: ProblemInfo | null = $state(null);
    let results = $state(null);

    async function handleSolve() {
        results = await solve({ problem_id: problem.id, /* ... */ });
    }
</script>

<BaseLayout>
    {#snippet leftSidebar()}
        <!-- Preference controls -->
    {/snippet}

    {#snippet visualizationArea()}
        {#if problem && results}
            <VisualizationsPanel {problem} solutionsObjectiveValues={results} />
        {/if}
    {/snippet}
</BaseLayout>
```
