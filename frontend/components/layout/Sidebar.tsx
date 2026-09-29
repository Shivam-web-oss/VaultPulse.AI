'use client';

import { LoaderCircle, MessageSquare, MoreHorizontal, PanelLeftClose, Pencil, Plus, Search, Settings, Share2, Trash2, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState, type FormEvent } from 'react';
import type { Conversation } from '../../types/conversation';
import { DEFAULT_CHAT_ROUTE, LOGIN_ROUTE, SETTINGS_ROUTE } from '../../routes';
import { useAuthContext } from '../../context/AuthContext';
import { ThemeToggle } from '../ui/ThemeToggle';
import { BrandMark } from '../BrandMark';
import { ConversationListSkeleton } from '../ui/Skeleton';

const GROUPS = ['Today', 'Yesterday', 'Previous 7 Days', 'Older'] as const;

function conversationGroups(conversations: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterday = today - 24 * 60 * 60 * 1000;
  const previousSevenDays = today - 7 * 24 * 60 * 60 * 1000;
  const groups: Record<(typeof GROUPS)[number], Conversation[]> = {
    Today: [],
    Yesterday: [],
    'Previous 7 Days': [],
    Older: [],
  };

  for (const conversation of conversations) {
    const updated = new Date(conversation.updatedAt);
    const updatedDay = new Date(updated.getFullYear(), updated.getMonth(), updated.getDate()).getTime();
    const group = updatedDay === today ? 'Today' : updatedDay === yesterday ? 'Yesterday' : updatedDay > previousSevenDays ? 'Previous 7 Days' : 'Older';
    groups[group].push(conversation);
  }

  return groups;
}

type SidebarProps = {
  open: boolean;
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onNew: () => void;
  onClose: () => void;
  loading: boolean;
  loadError: string | null;
  onRetryLoad: () => void;
  creating: boolean;
  createError: string | null;
};

export function Sidebar({ open, conversations, selectedId, onSelect, onRename, onDelete, onNew, onClose, loading, loadError, onRetryLoad, creating, createError }: SidebarProps) {
  const router = useRouter();
  const { user, logOut } = useAuthContext();
  const [searchTerm, setSearchTerm] = useState('');
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [renameTarget, setRenameTarget] = useState<Conversation | null>(null);
  const [renameTitle, setRenameTitle] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);

  useEffect(() => {
    if (!menuFor) return;
    const closeMenu = (event: PointerEvent) => {
      if (event.target instanceof Element && !event.target.closest('[data-conversation-menu]')) setMenuFor(null);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuFor(null);
    };
    document.addEventListener('pointerdown', closeMenu);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeMenu);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [menuFor]);

  const submitRename = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!renameTarget || actionBusy) return;
    const title = renameTitle.trim();
    if (!title) {
      setActionError('Enter a conversation name.');
      return;
    }
    setActionBusy(true);
    setActionError(null);
    try {
      await onRename(renameTarget.id, title);
      setRenameTarget(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Unable to rename this conversation.');
    } finally {
      setActionBusy(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget || actionBusy) return;
    setActionBusy(true);
    setActionError(null);
    try {
      await onDelete(deleteTarget.id);
      setDeleteTarget(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Unable to delete this conversation.');
    } finally {
      setActionBusy(false);
    }
  };
  const firstLetter = user?.name.charAt(0).toUpperCase() || 'U';
  const normalizedSearch = searchTerm.trim().toLocaleLowerCase();
  const visibleConversations = normalizedSearch
    ? conversations.filter((conversation) => conversation.title.toLocaleLowerCase().includes(normalizedSearch))
    : conversations;
  const groupedConversations = conversationGroups(visibleConversations);

  return <aside className={`chat-sidebar relative fixed inset-y-0 left-0 z-30 flex w-[290px] flex-col border-r border-white/10 bg-[#183528] transition-transform md:static md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
    <div className="flex items-center justify-between border-b border-white/10 p-4"><div className="flex items-center gap-3"><BrandMark size={32} className="rounded-lg" /><span className="font-semibold">VaultPulse.AI</span></div><div className="flex items-center gap-1"><ThemeToggle /><button type="button" title="Close sidebar" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 md:hidden"><PanelLeftClose size={17} /></button></div></div>
    <div className="p-3"><button type="button" onClick={onNew} disabled={creating} className="flex w-full items-center gap-2 rounded-xl bg-[#b8e978] px-3 py-2.5 text-sm font-medium text-[#20351f] hover:bg-[#c7f28c] disabled:cursor-wait disabled:opacity-70">{creating ? <LoaderCircle size={16} className="animate-spin" /> : <Plus size={16} />}{creating ? 'Creating...' : 'New chat'}</button>{createError && <div role="alert" className="mt-2 rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-700 dark:text-red-200"><p>{createError}</p><button type="button" onClick={onNew} className="mt-1 font-semibold underline underline-offset-2">Try again</button></div>}</div>
    <div className="px-3"><label className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-400"><Search size={15} /><input aria-label="Search conversations" type="search" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Search conversations" className="min-w-0 flex-1 bg-transparent text-slate-200 outline-none placeholder:text-slate-400" /></label></div>
    <div className="mt-5 flex-1 space-y-5 overflow-y-auto px-3" aria-busy={loading}>
      {actionError && !renameTarget && !deleteTarget && <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-700 dark:text-red-200">{actionError}</div>}
      {loading ? <ConversationListSkeleton rows={4} /> : loadError ? <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-700 dark:text-red-200"><p>{loadError}</p><button type="button" onClick={onRetryLoad} className="mt-2 font-semibold underline underline-offset-2">Try again</button></div> : <>
        {GROUPS.map((group) => <div key={group}>{groupedConversations[group].length > 0 && <><div className="px-2 pb-2 text-xs font-medium uppercase tracking-wider text-slate-400">{group}</div>{groupedConversations[group].map((conversation) => <div key={conversation.id} data-conversation-menu className="relative mb-1 flex items-center gap-1"><button type="button" onClick={() => onSelect(conversation.id)} className={`flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-2 text-left text-sm ${selectedId === conversation.id ? 'bg-white/10 text-white' : 'text-slate-300 hover:bg-white/5 hover:text-white'}`}><MessageSquare size={14} /><span className="truncate">{conversation.title}</span></button><button type="button" title="Conversation options" aria-label={`Options for ${conversation.title}`} aria-haspopup="menu" aria-expanded={menuFor === conversation.id} onClick={() => { setMenuFor((current) => current === conversation.id ? null : conversation.id); setActionError(null); }} className="rounded p-1 text-slate-400 hover:bg-white/10 hover:text-white"><MoreHorizontal size={15} /></button>
          {menuFor === conversation.id && <div role="menu" className="absolute right-0 top-full z-40 mt-1 min-w-40 overflow-visible rounded-lg border border-[var(--app-border)] bg-[var(--app-surface)] p-1 text-[var(--app-text)] shadow-xl">
            <button role="menuitem" type="button" onClick={() => { setRenameTarget(conversation); setRenameTitle(conversation.title); setActionError(null); setMenuFor(null); }} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-[var(--app-surface-muted)]"><Pencil size={14} />Rename</button>
            <div className="group relative">
              <button role="menuitem" type="button" aria-disabled="true" className="flex w-full cursor-not-allowed items-center gap-2 rounded-md px-3 py-2 text-left text-sm opacity-55"><Share2 size={14} />Share</button>
              <span role="tooltip" className="pointer-events-none absolute right-1 top-0 hidden -translate-y-full whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-xs text-white shadow group-hover:block group-focus-within:block">Coming soon</span>
            </div>
            <div className="my-1 border-t border-[var(--app-border)]" />
            <button role="menuitem" type="button" onClick={() => { setDeleteTarget(conversation); setActionError(null); setMenuFor(null); }} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-red-600 hover:bg-red-500/10 dark:text-red-300"><Trash2 size={14} />Delete</button>
          </div>}
        </div>)}</>}</div>)}
        {visibleConversations.length === 0 && <p className="px-2 py-4 text-sm text-slate-400">{searchTerm ? 'No chats match your search.' : 'Your previous chats will appear here.'}</p>}
      </>}
    </div>
    <div className="border-t border-white/10 p-3"><div className="mb-2 flex items-center gap-3"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#b8e978] text-sm font-semibold text-[#20351f]">{firstLetter}</div><span className="min-w-0 flex-1 truncate text-sm text-slate-200">{user?.name || 'User'}</span></div><div className="flex gap-2"><button type="button" onClick={() => router.push(DEFAULT_CHAT_ROUTE)} className="flex-1 rounded-lg px-2 py-2 text-left text-xs text-slate-400 hover:bg-white/10 hover:text-white"><MessageSquare size={14} className="mr-2 inline" />Chats</button><button type="button" onClick={() => router.push(SETTINGS_ROUTE)} title="Settings" className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><Settings size={16} /></button><button type="button" onClick={() => { logOut(); router.replace(LOGIN_ROUTE); }} title="Sign out" className="rounded-lg px-2 text-xs text-slate-400 hover:bg-white/10 hover:text-white">Sign out</button></div></div>
    {renameTarget && <div className="absolute inset-0 z-50 grid place-items-center bg-black/55 p-4"><form role="dialog" aria-modal="true" aria-labelledby="rename-conversation-title" onSubmit={(event) => void submitRename(event)} className="w-full max-w-sm rounded-xl border border-[var(--app-border)] bg-[var(--app-surface)] p-4 text-[var(--app-text)] shadow-2xl"><div className="mb-4 flex items-center justify-between"><h2 id="rename-conversation-title" className="font-semibold">Rename conversation</h2><button type="button" aria-label="Close rename dialog" onClick={() => { setRenameTarget(null); setActionError(null); }} className="rounded p-1 text-[var(--app-muted)] hover:bg-[var(--app-surface-muted)]"><X size={17} /></button></div><label htmlFor="conversation-title" className="mb-1 block text-sm text-[var(--app-muted)]">Name</label><input id="conversation-title" autoFocus maxLength={120} value={renameTitle} onChange={(event) => setRenameTitle(event.target.value)} className="w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-bg)] px-3 py-2 text-sm outline-none focus:border-[#70934f]" />{actionError && <p role="alert" className="mt-2 text-sm text-red-600 dark:text-red-300">{actionError}</p>}<div className="mt-4 flex justify-end gap-2"><button type="button" disabled={actionBusy} onClick={() => { setRenameTarget(null); setActionError(null); }} className="rounded-lg px-3 py-2 text-sm hover:bg-[var(--app-surface-muted)]">Cancel</button><button type="submit" disabled={actionBusy || !renameTitle.trim()} className="rounded-lg bg-[#b8e978] px-3 py-2 text-sm font-medium text-[#20351f] disabled:opacity-60">{actionBusy ? 'Saving…' : 'Save'}</button></div></form></div>}
    {deleteTarget && <div className="absolute inset-0 z-50 grid place-items-center bg-black/55 p-4"><div role="alertdialog" aria-modal="true" aria-labelledby="delete-conversation-title" className="w-full max-w-sm rounded-xl border border-[var(--app-border)] bg-[var(--app-surface)] p-4 text-[var(--app-text)] shadow-2xl"><div className="mb-2 flex items-center justify-between"><h2 id="delete-conversation-title" className="font-semibold">Delete conversation?</h2><button type="button" aria-label="Close delete dialog" onClick={() => { setDeleteTarget(null); setActionError(null); }} className="rounded p-1 text-[var(--app-muted)] hover:bg-[var(--app-surface-muted)]"><X size={17} /></button></div><p className="text-sm text-[var(--app-muted)]">“{deleteTarget.title}” and its messages will be permanently deleted.</p>{actionError && <p role="alert" className="mt-2 text-sm text-red-600 dark:text-red-300">{actionError}</p>}<div className="mt-4 flex justify-end gap-2"><button type="button" disabled={actionBusy} onClick={() => { setDeleteTarget(null); setActionError(null); }} className="rounded-lg px-3 py-2 text-sm hover:bg-[var(--app-surface-muted)]">Cancel</button><button type="button" disabled={actionBusy} onClick={() => void confirmDelete()} className="rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-60">{actionBusy ? 'Deleting…' : 'Delete'}</button></div></div></div>}
  </aside>;
}
