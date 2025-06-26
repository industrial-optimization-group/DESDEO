import { z } from 'zod';

const VariableSchema = z.object({
  name: z.string(),
  symbol: z.string(),
  variable_type: z.enum(['real', 'integer', 'binary']),
  lowerbound: z.number().or(z.boolean()).nullable().optional(),
  upperbound: z.number().or(z.boolean()).nullable().optional(),
  initial_value: z.number().or(z.boolean()).nullable().optional(),
});

const TensorVariableSchema = z.object({
  name: z.string(),
  symbol: z.string(),
  variable_type: z.enum(['real', 'integer', 'binary']),
  shape: z.array(z.number()),
  lowerbounds: z.array(z.number())
    .or(z.number())
    .or(z.boolean())
    .nullable()
    .optional(),
  upperbounds: z.array(z.number())
    .or(z.number())
    .or(z.boolean())
    .nullable()
    .optional(),
  initial_values: z.array(z.number())
  .or(z.number())
  .or(z.boolean())
  .nullable()
  .optional(),
});


// Zod schema for Problem, matching the OpenAPI Problem type
// Only name, description, variables, and objectives are required for the minimal form
export const problemSchema = z.object({
  // Problem name (required)
  name: z.string().min(1, 'Name is required'),
  // Problem description (required, but can be empty string)
  description: z.string(),
  // Variables (required, can be empty array for now)
  variables: z.array(z.union([TensorVariableSchema, VariableSchema])),
  // Objectives (required, can be empty array for now)
  objectives: z.array(z.unknown()), // TODO: Replace z.any() with a more specific schema as UI grows
  // Optional fields (nullable or optional in OpenAPI)
  constants: z.array(z.unknown()).optional().nullable(),
  // constraints: z.array(z.any()).optional().nullable(),
  // extra_funcs: z.array(z.any()).optional().nullable(),
  // scalarization_funcs: z.array(z.any()).optional().nullable(),
  // discrete_representation: z.any().optional().nullable(),
  // scenario_keys: z.array(z.string()).optional().nullable(),
  // simulators: z.array(z.any()).optional().nullable(),
  // is_convex: z.boolean().optional().nullable(),
  // is_linear: z.boolean().optional().nullable(),
  // is_twice_differentiable: z.boolean().optional().nullable(),
});

export type Variable = z.infer<typeof VariableSchema>;

export type TensorVariable = z.infer<typeof TensorVariableSchema>;
