import { apiRequest } from './api';

export interface AuthResponse {
  user: { id: string; name: string; email: string };
  access_token: string;
  token_type: string;
}

export function registerUser(name: string, email: string, password: string) {
  return apiRequest<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  });
}

export function loginUser(email: string, password: string) {
  return apiRequest<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}
