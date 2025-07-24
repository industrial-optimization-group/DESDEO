# EMO (Evolutionary Multi-Objective Optimization) Integration

This directory contains the complete integration of the DESDEO EMO router functionality into the SvelteKit frontend.

## Files Overview

### `+page.server.ts`
Server-side actions that interface with the DESDEO API EMO router (`/method/emo/*` endpoints):

- **`solve`**: Starts EMO optimization using NSGA3 or RVEA algorithms
- **`save`**: Saves selected solutions from optimization results
- **`getSavedSolutions`**: Retrieves previously saved solutions for the user

### `types.ts`
TypeScript type definitions for EMO operations, matching the API models.

### `example-usage.svelte`
Complete example showing how to use the server actions in a Svelte component.

## API Endpoints Integrated

The server actions correspond to these DESDEO API endpoints:

1. **POST `/method/emo/solve`** → `solve` action
2. **POST `/method/emo/save`** → `save` action  
3. **GET `/method/emo/saved-solutions`** → `getSavedSolutions` action

## Usage in Svelte Components

### 1. Solve EMO Problem

```typescript
// Form data required:
{
  problem_id: number,
  method: 'NSGA3' | 'RVEA',
  max_evaluations: number,
  number_of_vectors: number,
  use_archive: boolean,
  preference: JSON.stringify({
    aspiration_levels: {
      f_1_min: 0.5,
      f_2_min: 0.3,
      // ... other objectives
    }
  })
}
```

```svelte
<form method="POST" action="?/solve" use:enhance={handleSolveSubmit}>
  <input type="hidden" name="problem_id" value={problemId} />
  <select name="method">
    <option value="NSGA3">NSGA3</option>
    <option value="RVEA">RVEA</option>
  </select>
  <input type="number" name="max_evaluations" value="1000" />
  <input type="number" name="number_of_vectors" value="20" />
  <input type="checkbox" name="use_archive" checked />
  <input type="hidden" name="preference" value={JSON.stringify(preference)} />
  <button type="submit">Solve Problem</button>
</form>
```

### 2. Save Solutions

```typescript
// Form data required:
{
  problem_id: number,
  solutions: JSON.stringify([
    {
      name: 'Solution Name',
      optimal_variables: { x_1: 0.5, x_2: 0.3 },
      optimal_objectives: { f_1_min: 0.2, f_2_min: 0.1 },
      constraint_values: {},
      extra_func_values: {}
    }
  ])
}
```

### 3. Get Saved Solutions

```svelte
<form method="POST" action="?/getSavedSolutions">
  <button type="submit">Load Saved Solutions</button>
</form>
```

## Method Support

### NSGA3 (Non-dominated Sorting Genetic Algorithm III)
- **Method name**: `"NSGA3"` (uppercase)
- **Best for**: Many-objective optimization (3+ objectives)
- **Uses reference vectors** for diversity preservation

### RVEA (Reference Vector guided Evolutionary Algorithm)  
- **Method name**: `"RVEA"` (uppercase)
- **Best for**: Large-scale multi-objective optimization
- **Adaptive reference vector approach**

## Preference Types Supported

The EMO methods support several preference types:

1. **Reference Point**: Aspiration levels for objectives
2. **Preferred Ranges**: Ranges of acceptable values
3. **Preferred Solutions**: Example solutions the DM likes
4. **Non-Preferred Solutions**: Example solutions the DM dislikes

## Response Handling

All actions return structured responses:

```typescript
// Success response
{
  success: true,
  data: EMOState | EMOSaveState | SavedSolution[],
  message: string
}

// Error response
{
  success: false,
  error: string
}
```

## Error Handling

The server actions include comprehensive error handling:

- **401**: Authentication errors (missing/invalid tokens)
- **400**: Invalid request data (malformed JSON, missing fields)
- **404**: Resource not found (invalid problem/session IDs)
- **500**: Server errors (API unavailable, internal errors)

## Integration with Existing Components

To integrate with your existing EMO page:

1. Use the server actions in your `+page.svelte`
2. Import types from `types.ts` for type safety
3. Handle form submissions with SvelteKit's `enhance` function
4. Display results and handle errors appropriately

## Authentication

All actions require:
- Valid `refresh_token` cookie (checked in `load` function)
- Valid `access_token` cookie (sent to API)

The authentication is handled automatically by the existing auth system.

## Configuration

The API base URL is currently hardcoded to `http://localhost:8000`. For production, you may want to:

1. Use environment variables
2. Make it configurable based on deployment environment
3. Use the same pattern as the client-side API client

## Example Integration

See `example-usage.svelte` for a complete working example that demonstrates:
- Form creation and submission
- Result handling and display
- Error handling
- Loading states
- Type safety with TypeScript
