'use client';

import { useEffect, useRef, useState } from 'react';
import { useAuthContext } from '../context/AuthContext';
import { createConversation, getConversation, getConversations } from '../lib/chatApi';
import type { Conversation } from '../types/conversation';

export function useConversation(initialConversationId?: string) {
  const { user } = useAuthContext();
  const accountId = user?.id ?? null;
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const detailRequestId = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const requestId = ++detailRequestId.current;
    const loadConversations = async () => {
      setConversations([]);
      setSelectedId(null);
      setLoading(true);
      setLoadError(null);
      if (!accountId) {
        setLoading(false);
        return;
      }
      try {
        const items = await getConversations();
        console.info('[conversation] loaded', { count: items.length, requestedId: initialConversationId ?? null, accountId });
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
        const selected = items.find((item) => item.id === initialConversationId) ?? items[0];
        const detail = await getConversation(selected.id);
        if (cancelled || requestId !== detailRequestId.current) return;
        if (!cancelled) {
          setConversations(items.map((item) => item.id === detail.id ? detail : item));
          setSelectedId(detail.id);
        }
      } catch {
        console.error('[conversation] failed to load conversations', { accountId });
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
  }, [accountId, initialConversationId, loadAttempt]);

  const active = conversations.find((item) => item.id === selectedId) ?? null;

  const newConversation = async () => {
    if (creating) return;
    setCreating(true);
    setCreateError(null);
    setDetailError(null);
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

  const openConversation = async (conversationId: string) => {
    if (!accountId) return;
    const requestId = ++detailRequestId.current;
    setSelectedId(conversationId);
    setDetailLoadingId(conversationId);
    setDetailError(null);
    try {
      const detail = await getConversation(conversationId);
      if (requestId !== detailRequestId.current) return;
      setConversations((current) => current.map((item) => item.id === detail.id ? detail : item));
      setSelectedId(detail.id);
    } catch {
      if (requestId !== detailRequestId.current) return;
      console.error('[conversation] failed to load conversation detail', { accountId });
      setDetailError('Unable to load this conversation. Check your connection and try again.');
    } finally {
      if (requestId === detailRequestId.current) setDetailLoadingId(null);
    }
  };

  const retryLoad = () => setLoadAttempt((attempt) => attempt + 1);

  return { conversations, setConversations, selectedId, setSelectedId, openConversation, active, newConversation, loading, loadError, retryLoad, creating, createError, detailLoading: detailLoadingId === selectedId, detailError };
}
