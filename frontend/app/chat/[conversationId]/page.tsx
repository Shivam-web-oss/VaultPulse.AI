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

export default function ConversationPage() {
	const params = useParams<{ conversationId: string }>();
	const { conversations, selectedId, setSelectedId, active, newConversation, draft, setDraft, sending, send } = useChat(params.conversationId);
	const [sidebarOpen, setSidebarOpen] = useState(false);

	return <ProtectedRoute><main className="flex min-h-screen bg-[#020817] text-slate-100"><Sidebar open={sidebarOpen} conversations={conversations} selectedId={selectedId} onSelect={(id) => { setSelectedId(id); setSidebarOpen(false); }} onNew={newConversation} onClose={() => setSidebarOpen(false)} /><section className="flex min-w-0 flex-1 flex-col"><div className="flex items-center border-b border-white/10 md:hidden"><button type="button" title="Open sidebar" onClick={() => setSidebarOpen(true)} className="p-4 text-slate-300"><Menu size={19} /></button><span className="text-sm font-semibold">VaultPulse.AI</span></div>{active && <ChatHeader title={active.title} onNew={newConversation} />}<div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-6 md:px-8">{active?.messages.length ? <div className="mx-auto w-full max-w-4xl"><ChatMessages messages={active.messages} /></div> : <EmptyChat onSelect={setDraft} />}</div><MessageComposer value={draft} onChange={setDraft} onSend={() => void send()} sending={sending} /></section></main></ProtectedRoute>;
}
