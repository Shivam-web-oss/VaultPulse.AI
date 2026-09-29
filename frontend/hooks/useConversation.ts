'use client';

import { useEffect, useState } from 'react';
import { createConversation, getConversations } from '../lib/chatApi';
import type { Conversation } from '../types/conversation';

export function useConversation(initialConversationId?: string) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const loadConversations = async () => {
      setLoading(true);
      setLoadError(null);
      try {
        const items = await getConversations();
        console.info('[conversation] loaded', { count: items.length, requestedId: initialConversationId ?? null });
        if (initialConversationId && items.some((item) => item.id === initialConversationId)) {
          if (!cancelled) {
            setConversations(items);
            setSelectedId(initialConversationId);
          }
          return;
        }
        if (items.length === 0) {
          try {
            const conversation = await createConversation();
            if (!cancelled) {
              setConversations([conversation]);
              setSelectedId(conversation.id);
              console.info('[conversation] created initial conversation', { conversationId: conversation.id });
            }
          } catch {
            console.error('[conversation] failed to create initial conversation');
            if (!cancelled) {
              setConversations([]);
              setSelectedId(null);
              setLoadError('Unable to prepare a conversation. Check your connection and try again.');
            }
          }
          return;
        }
        if (!cancelled) {
          setConversations(items);
          setSelectedId(items[0].id);
        }
      } catch {
        console.error('[conversation] failed to load conversations');
        if (!cancelled) {
          setConversations([]);
          setSelectedId(null);
          setLoadError('Unable to load conversations. Check your connection and try again.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void loadConversations();
    return () => {
      cancelled = true;
    };
  }, [initialConversationId, loadAttempt]);

  const active = conversations.find((item) => item.id === selectedId) ?? null;

  const newConversation = async () => {
    if (creating) return;
    setCreating(true);
    setCreateError(null);
    try {
      const conversation = await createConversation();
      setConversations((current) => [conversation, ...current]);
      setSelectedId(conversation.id);
      console.info('[conversation] created conversation', { conversationId: conversation.id });
    } catch {
      console.error('[conversation] failed to create conversation');
      setCreateError('Unable to create a conversation. Check your connection and try again.');
    } finally {
      setCreating(false);
    }
  };

  const retryLoad = () => setLoadAttempt((attempt) => attempt + 1);

  return { conversations, setConversations, selectedId, setSelectedId, active, newConversation, loading, loadError, retryLoad, creating, createError };
}
