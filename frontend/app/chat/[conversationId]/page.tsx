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
import { ChatThreadSkeleton, ChatTypingIndicator, Skeleton } from '../../../components/ui/Skeleton';

export default function ConversationPage() {
	const params = useParams<{ conversationId: string }>();
	const { conversations, selectedId, openConversation, active, newConversation, draft, setDraft, sending, error, send, retrySend, loading, loadError, retryLoad, creating, createError } = useChat(params.conversationId);
	const [sidebarOpen, setSidebarOpen] = useState(false);

	return (
		<ProtectedRoute>
			<main className="chat-shell flex h-dvh min-h-0 overflow-hidden text-slate-100">
				<Sidebar open={sidebarOpen} conversations={conversations} selectedId={selectedId} onSelect={(id) => { void openConversation(id); setSidebarOpen(false); }} onNew={newConversation} onClose={() => setSidebarOpen(false)} loading={loading} loadError={loadError} onRetryLoad={retryLoad} creating={creating} createError={createError} />
				<section className="chat-main flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
					<div className="chat-mobile-header flex shrink-0 items-center justify-between border-b border-white/10 md:hidden">
						<div className="flex items-center"><button type="button" title="Open sidebar" onClick={() => setSidebarOpen(true)} className="p-4 text-slate-300"><Menu size={19} /></button><BrandMark size={24} className="mr-2 rounded-md" /><span className="text-sm font-semibold">VaultPulse.AI</span></div>
						<ThemeToggle className="mr-3" />
					</div>
					{active ? <ChatHeader title={active.title} onNew={newConversation} /> : loading ? <header className="chat-header flex shrink-0 items-center border-b border-white/10 px-4 py-4 md:px-6" aria-busy="true"><Skeleton className="h-4 w-40 rounded" /></header> : null}
					<div className="chat-scroll-region flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain px-4 py-4 md:px-8 md:py-5" aria-busy={loading && !active}>
						{active?.messages.length ? <div className="mx-auto w-full max-w-4xl"><ChatMessages messages={active.messages} />{sending && <div className="mt-3"><ChatTypingIndicator /></div>}</div> : active ? <EmptyChat onSelect={setDraft} /> : loading ? <ChatThreadSkeleton /> : loadError ? <div role="alert" className="api-error mx-auto my-auto max-w-md rounded-xl border p-5 text-center"><p>{loadError}</p><button type="button" onClick={retryLoad} className="mt-3 rounded-lg bg-[#b8e978] px-4 py-2 text-sm font-semibold text-[#20351f]">Try again</button></div> : null}
					</div>
					{error && <div role="alert" className="api-error flex shrink-0 items-center justify-center gap-3 border-t px-4 py-2 text-center text-xs"><p>{error}</p><button type="button" onClick={retrySend} disabled={sending} className="font-semibold underline underline-offset-2 disabled:opacity-60">Retry</button></div>}
					<MessageComposer value={draft} onChange={setDraft} onSend={() => void send()} sending={sending} canSend={Boolean(active)} />
				</section>
			</main>
		</ProtectedRoute>
	);
}
