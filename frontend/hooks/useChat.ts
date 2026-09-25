'use client';

import { useState } from 'react';
import { sendMessage } from '../lib/chatApi';
import { useConversation } from './useConversation';
import type { Message } from '../types/chat';

export function useChat(initialConversationId?: string) {
  const conversation = useConversation(initialConversationId);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);

  const send = async () => {
    const { active } = conversation;
    if (!active || !draft.trim() || sending) return;

    const text = draft.trim();
    const userMessage: Message = { id: `local-${Date.now()}`, role: 'user', content: text, createdAt: new Date().toISOString() };
    setDraft('');
    setSending(true);
    conversation.setConversations((current) => current.map((item) => item.id === active.id ? { ...item, messages: [...item.messages, userMessage] } : item));

    try {
      const reply = await sendMessage(active.id, text);
      conversation.setConversations((current) => current.map((item) => item.id === active.id ? { ...item, messages: [...item.messages, reply] } : item));
    } catch {
      const reply: Message = { id: `mock-${Date.now()}`, role: 'assistant', content: 'The backend is unavailable right now. Start FastAPI with `uvicorn app.main:app --reload` and try again.', createdAt: new Date().toISOString() };
      conversation.setConversations((current) => current.map((item) => item.id === active.id ? { ...item, messages: [...item.messages, reply] } : item));
    } finally {
      setSending(false);
    }
  };

  return { ...conversation, draft, setDraft, sending, send };
}
