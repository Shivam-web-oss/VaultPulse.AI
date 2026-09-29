import { apiRequest } from './api';
import type { Conversation } from '../types/conversation';
import type { Message } from '../types/chat';

type ApiMessage = { id: string; role: Message['role']; content: string; created_at: string };
type ApiConversation = { id: string; title: string; created_at: string; updated_at: string; messages?: ApiMessage[] };

const messageFromApi = (item: ApiMessage): Message => ({ id: item.id, role: item.role, content: item.content, createdAt: item.created_at });
const conversationFromApi = (item: ApiConversation): Conversation => ({
  id: item.id,
  title: item.title,
  createdAt: item.created_at,
  updatedAt: item.updated_at,
  messages: (item.messages || []).map(messageFromApi),
});

export async function createConversation(title = 'New conversation') {
  return conversationFromApi(await apiRequest<ApiConversation>('/api/conversations', { method: 'POST', body: JSON.stringify({ title }) }));
}
export async function getConversations() {
  return (await apiRequest<ApiConversation[]>('/api/conversations')).map(conversationFromApi);
}
export async function getConversation(id: string) {
  return conversationFromApi(await apiRequest<ApiConversation>(`/api/conversations/${id}`));
}
export async function sendMessage(conversationId: string, message: string, clientMessageId: string) {
  return messageFromApi(await apiRequest<ApiMessage>(`/api/chat/${conversationId}/messages`, { method: 'POST', body: JSON.stringify({ message, client_message_id: clientMessageId }) }));
}
export async function renameConversation(id: string, title: string) {
  return apiRequest<{ id: string; title: string; created_at: string; updated_at: string }>(`/api/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) });
}
export async function deleteConversation(id: string) {
  return apiRequest(`/api/conversations/${id}`, { method: 'DELETE' });
}
