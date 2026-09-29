import { clearAuth, readStoredSession } from '../types/user';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiRequestError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const session = readStoredSession();
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (session?.accessToken) headers.set('Authorization', `Bearer ${session.accessToken}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  console.info('[api] response', { method: options.method || 'GET', path, status: response.status });
  if (response.status === 401) {
    clearAuth();
    if (typeof window !== 'undefined') window.dispatchEvent(new Event('vaultpulse-auth-change'));
  }
  if (!response.ok) {
    const body = await response.text();
    let message = body || response.statusText || 'Request failed';
    try {
      const parsed = JSON.parse(body) as { detail?: unknown; message?: unknown };
      if (typeof parsed.detail === 'string') message = parsed.detail;
      else if (typeof parsed.message === 'string') message = parsed.message;
    } catch {
      // Keep non-JSON API error bodies visible for actionable feedback.
    }
    throw new ApiRequestError(response.status, message);
  }
  return response.json() as Promise<T>;
}
