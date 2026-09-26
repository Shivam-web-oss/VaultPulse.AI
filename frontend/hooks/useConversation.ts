'use client';

import { useEffect, useState } from 'react';
import { createConversation, getConversations } from '../lib/chatApi';
import { mockConversation } from '../lib/conversationApi';
import type { Conversation } from '../types/conversation';

export function useConversation(initialConversationId?: string) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getConversations().then(async (items) => {
      if (initialConversationId && items.some((item) => item.id === initialConversationId)) {
        if (!cancelled) {
          setConversations(items);
          setSelectedId(initialConversationId);
        }
        return;
      }
      if (items.length === 0) {
        // No conversations yet: create one so the composer has an active target to send to.
        try {
          const conversation = await createConversation();
          if (!cancelled) {
            setConversations([conversation]);
            setSelectedId(conversation.id);
          }
          return;
        } catch {
          // Backend unavailable: fall back to the local mock conversation.
          if (!cancelled) {
            setConversations([mockConversation]);
            setSelectedId(mockConversation.id);
          }
          return;
        }
      }
      if (!cancelled) {
        setConversations(items);
        setSelectedId(items[0].id);
      }
    }).catch(() => {
      if (!cancelled) {
        setConversations([mockConversation]);
        setSelectedId(mockConversation.id);
      }
    });
    return () => {
      cancelled = true;
    };
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
