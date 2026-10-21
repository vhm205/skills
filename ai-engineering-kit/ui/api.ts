import type { Feature, ProjectInfo, ProjectsResponse, ReviewState, Workflow, CopilotModel } from '../src/types';
export interface FeatureResponse { feature: Feature; review: ReviewState; reviewError: string | null; workflow: Workflow }
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export async function api<T>(path: string, value?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { method: value === undefined ? 'GET' : 'POST',
    headers: value === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: value === undefined ? undefined : JSON.stringify(value), signal });
  const data = await response.json();
  if (!response.ok) throw new ApiError(response.status, data.error ?? 'Không thể kết nối server.');
  return data as T;
}
export async function connect() {
  const token = new URLSearchParams(location.hash.slice(1)).get('token');
  if (token) {
    await api('/api/session', { token });
    history.replaceState(null, '', location.pathname + location.search);
  }
  return api<ProjectInfo>('/api/project');
}
export const featurePath = (id: string) => `/api/features/${encodeURIComponent(id)}`;

export async function getProjects() {
  return api<ProjectsResponse>('/api/projects');
}
export async function addProject(path: string, setActive = true) {
  return api<{ ok: boolean; active: string; project: ProjectInfo }>('/api/projects', { path, setActive });
}
export async function switchProject(root: string) {
  return api<{ ok: boolean; active: string; project: ProjectInfo }>('/api/projects/switch', { root });
}
export async function removeProject(root: string) {
  return api<{ ok: boolean; active: string }>('/api/projects/remove', { root });
}
export async function fetchCopilotModels(provider: string, endpoint?: string, apiKey?: string) {
  return api<{ models: CopilotModel[] }>('/api/copilot/models', { provider, endpoint, apiKey });
}
