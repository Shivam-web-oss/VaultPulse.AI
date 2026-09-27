'use client';

import { useState } from 'react';
import { createConversation, sendMessage } from '../lib/chatApi';
import { useConversation } from './useConversation';
import type { Message } from '../types/chat';

export function useChat(initialConversationId?: string) {
  const conversation = useConversation(initialConversationId);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async () => {
    const { active } = conversation;
    if (!active || !draft.trim() || sending) return;

    const text = draft.trim();
    setError(null);
    const userMessage: Message = { id: `local-${Date.now()}`, role: 'user', content: text, createdAt: new Date().toISOString() };
    setDraft('');
    setSending(true);
    conversation.setConversations((current) => current.map((item) => item.id === active.id ? { ...item, messages: [...item.messages, userMessage] } : item));

    let conversationId = active.id;
    try {
      if (conversationId.startsWith('local-')) {
        const persisted = await createConversation(active.title);
        conversationId = persisted.id;
        conversation.setConversations((current) => current.map((item) => item.id === active.id ? { ...persisted, messages: [...item.messages] } : item));
        conversation.setSelectedId(conversationId);
      }

      const reply = await sendMessage(conversationId, text);
      conversation.setConversations((current) => current.map((item) => item.id === conversationId ? { ...item, messages: [...item.messages, reply] } : item));
      console.info('[chat] message exchange completed', { conversationId });
    } catch (caughtError) {
      let message = 'The message could not be sent. Check the backend connection and try again.';
      if (caughtError instanceof Error) {
        try {
          const details = JSON.parse(caughtError.message) as { detail?: string };
          if (details.detail) message = details.detail;
        } catch {
          // Keep the user-facing fallback for non-JSON network errors.
        }
      }
      console.error('[chat] message exchange failed', { conversationId });
      setError(message);
    } finally {
      setSending(false);
    }
  };

  return { ...conversation, draft, setDraft, sending, error, send };
}
