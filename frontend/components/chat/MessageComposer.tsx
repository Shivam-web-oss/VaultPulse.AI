'use client';

import { useRef, useState } from 'react';
import { Image as ImageIcon, Mic, Paperclip, Send, Square } from 'lucide-react';
import { uploadFile } from '../../lib/uploadApi';
import type { Attachment } from '../../types/chat';
import { FileAttachment } from './FileAttachment';

export function MessageComposer({ value, onChange, onSend, sending }: { value: string; onChange: (value: string) => void; onSend: () => void; sending: boolean }) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);

  const handleFiles = async (files: FileList | null) => {
    if (!files) return;
    for (const file of Array.from(files)) {
      try {
        const uploaded = await uploadFile(file);
        setAttachments((current) => [...current, uploaded]);
      } catch {
        // Keep the composer usable when an upload fails.
      }
    }
  };

  return <div className="border-t border-white/10 bg-[#102219] px-4 py-4"><div className="mx-auto max-w-4xl">
    {attachments.length > 0 && <div className="mb-3 flex flex-wrap gap-2">{attachments.map((file) => <FileAttachment key={file.id} file={file} onRemove={() => setAttachments((current) => current.filter((item) => item.id !== file.id))} />)}</div>}
    <div className="rounded-2xl border border-white/10 bg-[#183528] p-2 shadow-2xl">
      <textarea ref={inputRef} value={value} onChange={(event) => { onChange(event.target.value); event.currentTarget.style.height = 'auto'; event.currentTarget.style.height = `${Math.min(event.currentTarget.scrollHeight, 160)}px`; }} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); onSend(); } }} rows={1} placeholder="Message AI Assistant..." className="max-h-40 min-h-11 w-full resize-none bg-transparent px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500" />
      <div className="flex items-center justify-between"><div className="flex gap-1"><button type="button" title="Attach file" onClick={() => fileRef.current?.click()} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><Paperclip size={17} /></button><button type="button" title="Add image" onClick={() => fileRef.current?.click()} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><ImageIcon size={17} /></button><button type="button" title="Voice input" className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"><Mic size={17} /></button><input ref={fileRef} type="file" hidden multiple accept=".pdf,.docx,.txt,.csv,image/*" onChange={(event) => void handleFiles(event.target.files)} /></div><button type="button" onClick={onSend} disabled={sending || !value.trim()} title={sending ? 'Stop generating' : 'Send message'} className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#b8e978] text-[#20351f] hover:bg-[#c7f28c] disabled:cursor-not-allowed disabled:opacity-40">{sending ? <Square size={14} /> : <Send size={16} />}</button></div>
    </div><p className="mt-2 text-center text-[11px] text-slate-600">Enter to send · Shift+Enter for a new line</p>
  </div></div>;
}
