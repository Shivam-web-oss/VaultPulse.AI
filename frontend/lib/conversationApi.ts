import type { Conversation } from '../types/conversation';

export const mockConversation: Conversation = {
  id: 'local-new',
  title: 'New conversation',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  messages: [],
};
