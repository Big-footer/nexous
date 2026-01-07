/**
 * NEXOUS API Client
 */

const API_BASE = '/api';

async function request(method, path, data = null) {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };
  
  if (data) {
    options.body = JSON.stringify(data);
  }
  
  const response = await fetch(`${API_BASE}${path}`, options);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

// Projects API
export const projectsApi = {
  list: () => request('GET', '/projects'),
  get: (id) => request('GET', `/projects/${id}`),
  create: (data) => request('POST', '/projects', data),
  update: (id, yamlContent) => request('PUT', `/projects/${id}`, { yaml_content: yamlContent }),
  delete: (id) => request('DELETE', `/projects/${id}`),
  validate: (yamlContent) => request('POST', '/projects/validate', { yaml_content: yamlContent }),
};

// Runs API
export const runsApi = {
  list: (projectId) => request('GET', `/projects/${projectId}/runs`),
  start: (projectId, runId = null) => request('POST', `/projects/${projectId}/runs`, { run_id: runId }),
  getStatus: (projectId, runId) => request('GET', `/projects/${projectId}/runs/${runId}`),
};

// Traces API
export const tracesApi = {
  get: (projectId, runId) => request('GET', `/projects/${projectId}/runs/${runId}/trace`),
  getArtifacts: (projectId, runId) => request('GET', `/projects/${projectId}/runs/${runId}/artifacts`),
  getAgents: (projectId, runId) => request('GET', `/projects/${projectId}/runs/${runId}/agents`),
  getSummary: (projectId, runId) => request('GET', `/projects/${projectId}/runs/${runId}/summary`),
};
