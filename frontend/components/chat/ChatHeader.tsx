'use client';

import { ChevronDown, MoreHorizontal, Plus } from 'lucide-react';

export function ChatHeader({ title, onNew }: { title: string; onNew: () => void }) {
  return <header className="flex items-center justify-between border-b border-white/10 px-4 py-3 md:px-6"><div><div className="text-sm font-semibold text-white">{title}</div><button type="button" className="mt-1 flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300">Balanced <ChevronDown size={13} /></button></div><div className="flex items-center gap-1"><button type="button" onClick={onNew} title="New conversation" className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><Plus size={18} /></button><button type="button" title="More options" className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><MoreHorizontal size={18} /></button></div></header>;
}
