'use client';

import { useEffect, useState } from 'react';
import { createConversation, getConversations } from '../lib/chatApi';
import type { Conversation } from '../types/conversation';

export function useConversation(initialConversationId?: string) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getConversations().then(async (items) => {
      console.info('[conversation] loaded', { count: items.length, requestedId: initialConversationId ?? null });
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
            console.info('[conversation] created initial conversation', { conversationId: conversation.id });
          }
          return;
        } catch {
          console.error('[conversation] failed to create initial conversation');
          if (!cancelled) {
            setConversations([]);
            setSelectedId(null);
          }
          return;
        }
      }
      if (!cancelled) {
        setConversations(items);
        setSelectedId(items[0].id);
      }
    }).catch(() => {
      console.error('[conversation] failed to load conversations');
      if (!cancelled) {
        setConversations([]);
        setSelectedId(null);
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
      console.info('[conversation] created conversation', { conversationId: conversation.id });
    } catch {
      console.error('[conversation] failed to create conversation');
    }
  };

  return { conversations, setConversations, selectedId, setSelectedId, active, newConversation };
}
