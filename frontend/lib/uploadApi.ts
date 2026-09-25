import { apiRequest } from './api';

export function uploadFile(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return apiRequest<{ id: string; name: string; size: number; type: string }>('/api/upload', { method: 'POST', body: formData });
}
