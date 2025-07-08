import { redirect, fail } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    throw redirect(307, '/home');
  }
  return {};
};

export const actions: Actions = {
  // Solve EMO optimization problem
  solve: async ({ request, cookies }) => {
    const refreshToken = cookies.get('refresh_token');
    if (!refreshToken) {
      return fail(401, { error: 'Not authenticated' });
    }

    try {
      const formData = await request.formData();
      const problemId = Number(formData.get('problem_id'));
      const method = String(formData.get('method') || 'NSGA3');
      const maxEvaluations = Number(formData.get('max_evaluations') || 1000);
      const numberOfVectors = Number(formData.get('number_of_vectors') || 20);
      const useArchive = formData.get('use_archive') === 'true';
      
      // Parse preference data (expecting JSON string)
      const preferenceData = formData.get('preference');
      let preference;
      try {
        preference = preferenceData ? JSON.parse(String(preferenceData)) : {
          aspiration_levels: {}
        };
      } catch (e) {
        return fail(400, { error: 'Invalid preference data format' });
      }

      const solveRequest = {
        problem_id: problemId,
        method,
        preference,
        max_evaluations: maxEvaluations,
        number_of_vectors: numberOfVectors,
        use_archive: useArchive
      };

      const response = await fetch(`${BASE_URL}/method/emo/solve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${cookies.get('access_token')}`
        },
        body: JSON.stringify(solveRequest)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return fail(response.status, { 
          error: errorData.detail || `HTTP ${response.status}: Failed to solve problem` 
        });
      }

      const result = await response.json();
      return {
        success: true,
        data: result,
        message: 'Problem solved successfully'
      };

    } catch (error) {
      console.error('EMO solve error:', error);
      return fail(500, { 
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      });
    }
  },

  // Save EMO solutions
  save: async ({ request, cookies }) => {
    const refreshToken = cookies.get('refresh_token');
    if (!refreshToken) {
      return fail(401, { error: 'Not authenticated' });
    }

    try {
      const formData = await request.formData();
      const problemId = Number(formData.get('problem_id'));
      const solutionsData = formData.get('solutions');
      
      let solutions;
      try {
        solutions = solutionsData ? JSON.parse(String(solutionsData)) : [];
      } catch (e) {
        return fail(400, { error: 'Invalid solutions data format' });
      }

      const saveRequest = {
        problem_id: problemId,
        solutions
      };

      const response = await fetch(`${BASE_URL}/method/emo/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${cookies.get('access_token')}`
        },
        body: JSON.stringify(saveRequest)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return fail(response.status, { 
          error: errorData.detail || `HTTP ${response.status}: Failed to save solutions` 
        });
      }

      const result = await response.json();
      return {
        success: true,
        data: result,
        message: 'Solutions saved successfully'
      };

    } catch (error) {
      console.error('EMO save error:', error);
      return fail(500, { 
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      });
    }
  },

  // Get saved solutions
  getSavedSolutions: async ({ cookies }) => {
    const refreshToken = cookies.get('refresh_token');
    if (!refreshToken) {
      return fail(401, { error: 'Not authenticated' });
    }

    try {
      const response = await fetch(`${BASE_URL}/method/emo/saved-solutions`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${cookies.get('access_token')}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return fail(response.status, { 
          error: errorData.detail || `HTTP ${response.status}: Failed to get saved solutions` 
        });
      }

      const result = await response.json();
      return {
        success: true,
        data: result,
        message: 'Saved solutions retrieved successfully'
      };

    } catch (error) {
      console.error('EMO get saved solutions error:', error);
      return fail(500, { 
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      });
    }
  }
};