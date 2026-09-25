'use client';

import { MessageSquare, MoreHorizontal, PanelLeftClose, Plus, Search, Settings } from 'lucide-react';
import { useRouter } from 'next/navigation';
import type { Conversation } from '../../types/conversation';
import { DEFAULT_CHAT_ROUTE, LOGIN_ROUTE, SETTINGS_ROUTE } from '../../routes';
import { useAuthContext } from '../../context/AuthContext';

export function Sidebar({ open, conversations, selectedId, onSelect, onNew, onClose }: { open: boolean; conversations: Conversation[]; selectedId: string | null; onSelect: (id: string) => void; onNew: () => void; onClose: () => void }) {
  const router = useRouter();
  const { user, logOut } = useAuthContext();
  const firstLetter = user?.name.charAt(0).toUpperCase() || 'U';

  return <aside className={`fixed inset-y-0 left-0 z-30 flex w-[290px] flex-col border-r border-white/10 bg-[#0a1221] transition-transform md:static md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
    <div className="flex items-center justify-between border-b border-white/10 p-4"><div className="flex items-center gap-3"><div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 font-bold">V</div><span className="font-semibold">VaultPulse.AI</span></div><button type="button" title="Close sidebar" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 md:hidden"><PanelLeftClose size={17} /></button></div>
    <div className="p-3"><button type="button" onClick={onNew} className="flex w-full items-center gap-2 rounded-xl bg-indigo-600 px-3 py-2.5 text-sm font-medium hover:bg-indigo-500"><Plus size={16} />New chat</button></div>
    <div className="px-3"><div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-400"><Search size={15} />Search conversations</div></div>
    <div className="mt-5 flex-1 space-y-5 overflow-y-auto px-3">{['Today', 'Yesterday', 'Previous 7 Days', 'Older'].map((group) => <div key={group}><div className="px-2 pb-2 text-xs font-medium uppercase tracking-wider text-slate-600">{group}</div>{conversations.map((conversation) => <div key={`${group}-${conversation.id}`} className="mb-1 flex items-center gap-1"><button type="button" onClick={() => onSelect(conversation.id)} className={`flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-2 text-left text-sm ${selectedId === conversation.id ? 'bg-white/10 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'}`}><MessageSquare size={14} /><span className="truncate">{conversation.title}</span></button><button type="button" title="Conversation options" className="rounded p-1 text-slate-600 hover:text-white"><MoreHorizontal size={15} /></button></div>)}</div>)}</div>
    <div className="border-t border-white/10 p-3"><div className="mb-2 flex items-center gap-3"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold">{firstLetter}</div><span className="min-w-0 flex-1 truncate text-sm text-slate-200">{user?.name || 'User'}</span></div><div className="flex gap-2"><button type="button" onClick={() => router.push(DEFAULT_CHAT_ROUTE)} className="flex-1 rounded-lg px-2 py-2 text-left text-xs text-slate-400 hover:bg-white/10 hover:text-white"><MessageSquare size={14} className="mr-2 inline" />Chats</button><button type="button" onClick={() => router.push(SETTINGS_ROUTE)} title="Settings" className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><Settings size={16} /></button><button type="button" onClick={() => { logOut(); router.replace(LOGIN_ROUTE); }} title="Sign out" className="rounded-lg px-2 text-xs text-slate-400 hover:bg-white/10 hover:text-white">Sign out</button></div></div>
  </aside>;
}
