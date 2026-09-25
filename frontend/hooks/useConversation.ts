'use client';

import { useEffect, useState } from 'react';
import { createConversation, getConversations } from '../lib/chatApi';
import { mockConversation } from '../lib/conversationApi';
import type { Conversation } from '../types/conversation';

export function useConversation(initialConversationId?: string) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    getConversations().then((items) => {
      setConversations(items);
      setSelectedId(initialConversationId && items.some((item) => item.id === initialConversationId) ? initialConversationId : items[0]?.id ?? null);
    }).catch(() => {
      setConversations([mockConversation]);
      setSelectedId(mockConversation.id);
    });
  }, [initialConversationId]);

  const active = conversations.find((item) => item.id === selectedId) ?? null;

  const newConversation = async () => {
    try {
      const conversation = await createConversation();
      setConversations((current) => [conversation, ...current]);
      setSelectedId(conversation.id);
    } catch {
      const local = { ...mockConversation, id: `local-${Date.now()}`, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
      setConversations((current) => [local, ...current]);
      setSelectedId(local.id);
    }
  };

  return { conversations, setConversations, selectedId, setSelectedId, active, newConversation };
}
