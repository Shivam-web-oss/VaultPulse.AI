'use client';

import { Copy, ThumbsDown, ThumbsUp, RotateCcw } from 'lucide-react';

export function MessageActions({ content, assistant = false }: { content: string; assistant?: boolean }) {
  const copy = async () => navigator.clipboard?.writeText(content);
  return (
    <div className="message-actions mt-1 flex gap-1 opacity-100 md:opacity-0 md:group-hover:opacity-100">
      <button type="button" title="Copy" onClick={copy} className="rounded-md p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"><Copy size={14} /></button>
      {assistant && <>
        <button type="button" title="Regenerate" className="rounded-md p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"><RotateCcw size={14} /></button>
        <button type="button" title="Like" className="rounded-md p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"><ThumbsUp size={14} /></button>
        <button type="button" title="Dislike" className="rounded-md p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"><ThumbsDown size={14} /></button>
      </>}
    </div>
  );
}
