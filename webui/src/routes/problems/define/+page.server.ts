import { redirect, error } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import { api } from '$lib/api/client';
import { setError, superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { schemas } from '$lib/api/zod-schemas';

let problemSchema = schemas.Problem

// Enhanced validation function that returns detailed error info
function parseAndValidateJSON(text: string, fieldName: string): { 
    success: boolean; 
    data: any; 
    error?: string 
} {
    try {
        const trimmed = text.trim();
        if (trimmed === '') return { success: true, data: null };
        
        const parsed = JSON.parse(trimmed);
        
        // Additional validation - ensure it's an array for bounds/values
        if (fieldName.includes('bounds') || fieldName.includes('values')) {
            if (!Array.isArray(parsed)) {
                return { 
                    success: false, 
                    data: null, 
                    error: `${fieldName} must be an array (e.g., [[1,2],[3,4]])` 
                };
            }
        }
        
        return { success: true, data: parsed };
    } catch (e) {
        return { 
            success: false, 
            data: null, 
            error: `Invalid JSON format in ${fieldName}. Expected format like [[1,2],[3,4]] or [1,2,3]` 
        };
    }
}

export const load: PageServerLoad = async ({ cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    throw redirect(307, '/home');
  }
  return {};
};


export const actions: Actions = {
  create: async ({ request, cookies }) => {
    const form = await superValidate(request, zod(problemSchema));
    const name = form.data.name;
    const description = form.data.description;
    // Parse and validate variables with proper error handling
    const variableErrors: string[] = [];
    const variables = form.data.variables.map((variable, idx) => {
      // For tensor variables, parse lowerbounds, upperbounds, initial_values if they are strings
      if (Array.isArray(variable.shape)) {
          const result = { ...variable };
          
          // Parse lowerbounds
          if (typeof variable.lowerbounds === 'string') {
              const parseResult = parseAndValidateJSON(variable.lowerbounds, 'lowerbounds');
              if (!parseResult.success) {
                  variableErrors.push(`Variable ${idx + 1}: ${parseResult.error}`);
              } else {
                  result.lowerbounds = parseResult.data;
              }
          }
          
          // Parse upperbounds
          if (typeof variable.upperbounds === 'string') {
              const parseResult = parseAndValidateJSON(variable.upperbounds, 'upperbounds');
              if (!parseResult.success) {
                  variableErrors.push(`Variable ${idx + 1}: ${parseResult.error}`);
              } else {
                  result.upperbounds = parseResult.data;
              }
          }
          
          // Parse initial_values
          if (typeof variable.initial_values === 'string') {
              const parseResult = parseAndValidateJSON(variable.initial_values, 'initial_values');
              if (!parseResult.success) {
                  variableErrors.push(`Variable ${idx + 1}: ${parseResult.error}`);
              } else {
                  result.initial_values = parseResult.data;
              }
          }
          
          return result;
      }
      return variable;
    });
    
    // If there were parsing errors, return the form with errors
    if (variableErrors.length > 0) {
        return setError(form, variableErrors.join('; '));
    }
    // Parse and validate constants with proper error handling
    const constantErrors: string[] = [];
    const constants = form.data.constants?.map((constant, idx) => {
      // For tensor constants, parse values if it's a string
      if (Array.isArray(constant.shape)) {
          const result = { ...constant };
          
          if (typeof constant.values === 'string') {
              const parseResult = parseAndValidateJSON(constant.values, 'values');
              if (!parseResult.success) {
                  constantErrors.push(`Constant ${idx + 1}: ${parseResult.error}`);
              } else {
                  result.values = parseResult.data;
              }
          }
          
          return result;
      }
      return constant;
    });
    
    // If there were parsing errors, return the form with errors
    if (constantErrors.length > 0) {
        return setError(form, constantErrors.join('; '));
    }
    // if objectives.objective_type is not defined, define it as "analytical".
    // This wont happen since it is a dropdown in the UI, but the type checking will complain otherwise
    const objectives = form.data.objectives.map(obj => ({
      ...obj,
      objective_type: obj.objective_type ?? "analytical"
    }));
    
    // create an item to print in the console for debugging purposes
    const debug = {
          name,
          description,
          variables,
          objectives,
          constants,
        };
      console.log("All the values right before POST: ",JSON.stringify(debug));

    // 1. Get refresh token from cookies
    const refreshToken = cookies.get('refresh_token');
    if (!refreshToken) {
      return { form, error: 'Not authenticated' };
    }

    // 2. Get a new access token from backend
    const refreshRes = await fetch(`${import.meta.env.VITE_API_URL}/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        cookie: `refresh_token=${refreshToken}`
      }
    });

    if (!refreshRes.ok) {
      return { form, error: 'Failed to refresh token' };
    }

    const { access_token } = await refreshRes.json();

    // 3. Use the access token in the Authorization header for the API call
    try {
      const res = await api.POST('/problem/add', {
        body: {
          name,
          description,
          variables,
          objectives,
          constants,
        },
        headers: {
          Authorization: `Bearer ${access_token}`,
          'Content-Type': 'application/json'
        }
      });
      // There is something wrong: In backend (desdeo/api/routers/problem.py), it seems like the route is trying to send useful error message,
      // but the response here is not very useful:
      console.log("What is response: ",JSON.stringify(res));
      if ( res.error) {
          let errorMsg = 'Internal server error';
          // Handle different error formats from backend
          if (typeof res.error.detail === 'string') {
              errorMsg = res.error.detail;
          } else if (Array.isArray(res.error.detail) && res.error.detail.length > 0) {
              // Validation errors (array of validation error objects)
              errorMsg = res.error.detail.map(e => e.msg || JSON.stringify(e)).join('; ');
          }
          
          throw error(500, { message: errorMsg });
      }

      
      return { form, result: res.data };
      } catch (e) {
        // Type guard for SvelteKit errors
        if (e && typeof e === 'object' && 'status' in e && 'body' in e) {
          // This is a SvelteKit error we threw - let it bubble up
          throw e;
        }
        
        // This is a network/connection error - use setError to preserve form data
        return setError(form, 'Network error: Failed to connect to server');
      }
    }
  };
