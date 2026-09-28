'use client';

import { Menu } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useState } from 'react';
import { ChatHeader } from '../../../components/chat/ChatHeader';
import { ChatMessages } from '../../../components/chat/ChatMessages';
import { EmptyChat } from '../../../components/chat/EmptyChat';
import { MessageComposer } from '../../../components/chat/MessageComposer';
import { ProtectedRoute } from '../../../components/auth/ProtectedRoute';
import { Sidebar } from '../../../components/layout/Sidebar';
import { useChat } from '../../../hooks/useChat';
import { ThemeToggle } from '../../../components/ui/ThemeToggle';
import { BrandMark } from '../../../components/BrandMark';

export default function ConversationPage() {
	const params = useParams<{ conversationId: string }>();
	const { conversations, selectedId, setSelectedId, active, newConversation, draft, setDraft, sending, error, send } = useChat(params.conversationId);
	const [sidebarOpen, setSidebarOpen] = useState(false);

		 return <ProtectedRoute><main className="chat-shell flex h-dvh min-h-0 overflow-hidden text-slate-100"><Sidebar open={sidebarOpen} conversations={conversations} selectedId={selectedId} onSelect={(id) => { setSelectedId(id); setSidebarOpen(false); }} onNew={newConversation} onClose={() => setSidebarOpen(false)} /><section className="chat-main flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"><div className="chat-mobile-header flex shrink-0 items-center justify-between border-b border-white/10 md:hidden"><div className="flex items-center"><button type="button" title="Open sidebar" onClick={() => setSidebarOpen(true)} className="p-4 text-slate-300"><Menu size={19} /></button><BrandMark size={24} className="mr-2 rounded-md" /><span className="text-sm font-semibold">VaultPulse.AI</span></div><ThemeToggle className="mr-3" /></div>{active && <ChatHeader title={active.title} onNew={newConversation} />}<div className="chat-scroll-region flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain px-4 py-4 md:px-8 md:py-5">{active?.messages.length ? <div className="mx-auto w-full max-w-4xl"><ChatMessages messages={active.messages} /></div> : <EmptyChat onSelect={setDraft} />}</div>{error && <p role="alert" className="shrink-0 border-t border-red-400/20 bg-red-950/30 px-4 py-2 text-center text-xs text-red-200">{error}</p>}<MessageComposer value={draft} onChange={setDraft} onSend={() => void send()} sending={sending} /></section></main></ProtectedRoute>;
}
