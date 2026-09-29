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
  const [retryText, setRetryText] = useState<string | null>(null);

  const submitMessage = async (text: string, active: NonNullable<typeof conversation.active>, reuseOptimisticMessage: boolean) => {
    setError(null);
    const userMessage: Message | null = reuseOptimisticMessage ? null : { id: `local-${Date.now()}`, role: 'user', content: text, createdAt: new Date().toISOString() };
    if (userMessage) {
      setDraft('');
      const previewTitle = text.replace(/\s+/g, ' ').trim().slice(0, 80);
      conversation.setConversations((current) => current.map((item) => item.id === active.id ? {
        ...item,
        title: item.title === 'New conversation' ? previewTitle : item.title,
        updatedAt: userMessage.createdAt,
        messages: [...item.messages, userMessage],
      } : item));
    }
    setSending(true);

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
      setRetryText(null);
      console.info('[chat] message exchange completed', { conversationId });
    } catch {
      const message = 'The message could not be sent. Check your connection and try again.';
      console.error('[chat] message exchange failed', { conversationId });
      setError(message);
      setRetryText(text);
      if (!reuseOptimisticMessage) setDraft(text);
    } finally {
      setSending(false);
    }
  };

  const send = async () => {
    const { active } = conversation;
    const text = draft.trim();
    if (!active || !text || sending) return;
    await submitMessage(text, active, retryText === text);
  };

  const retrySend = () => {
    const { active } = conversation;
    if (!active || !retryText || sending) return;
    setDraft('');
    void submitMessage(retryText, active, true);
  };

  const updateDraft = (value: string) => {
    setDraft(value);
    if (value !== retryText) setRetryText(null);
  };

  return { ...conversation, draft, setDraft: updateDraft, sending, error, send, retrySend };
}
