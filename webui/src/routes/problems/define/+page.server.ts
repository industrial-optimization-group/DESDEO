import { redirect } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import { api } from '$lib/api/client';
import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { schemas } from '$lib/api/zod-types';

let problemSchema = schemas.Problem

function tryParseJSON(text: string): any | null {
    try {
        const trimmed = text.trim();
        return trimmed === '' ? null : JSON.parse(trimmed);
    } catch {
        return null;
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
    const variables = form.data.variables.map((variable) => {
    // For tensor variables, parse lowerbounds, upperbounds, initial_values if they are strings
    if (Array.isArray(variable.shape)) {
        return {
            ...variable,
            lowerbounds: typeof variable.lowerbounds === 'string' ? tryParseJSON(variable.lowerbounds) : variable.lowerbounds,
            upperbounds: typeof variable.upperbounds === 'string' ? tryParseJSON(variable.upperbounds) : variable.upperbounds,
            initial_values: typeof variable.initial_values === 'string' ? tryParseJSON(variable.initial_values) : variable.initial_values,
        };
    }
    return variable;
});

const constants = form.data.constants?.map((constant) => {
    // For tensor constants, parse values if it's a string
    if (Array.isArray(constant.shape)) {
        return {
            ...constant,
            values: typeof constant.values === 'string' ? tryParseJSON(constant.values) : constant.values,
        };
    }
    return constant;
});
    // if objectives.objective_type is not defined, define it as "analytical".
    // This wont happen since it is a dropdown in the UI, but the type checking will complain otherwise
    const objectives = form.data.objectives.map(obj => ({
      ...obj,
      objective_type: obj.objective_type ?? "analytical"
    }));

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
      return { form, result: res.data };
  } catch (e) {
      return { form, error: 'Failed to add problem' };
    }
  }
};
