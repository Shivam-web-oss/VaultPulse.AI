'use client';

import { useRef, useState } from 'react';
import { FileText, Image as ImageIcon, LoaderCircle, Mic, Paperclip, Send } from 'lucide-react';
import { uploadFile } from '../../lib/uploadApi';
import type { Attachment } from '../../types/chat';
import { FileAttachment } from './FileAttachment';
import { Skeleton } from '../ui/Skeleton';

type UploadIssue = { key: string; file: File };

export function MessageComposer({ value, onChange, onSend, sending, canSend = true }: { value: string; onChange: (value: string) => void; onSend: () => void; sending: boolean; canSend?: boolean }) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState<UploadIssue[]>([]);
  const [uploadErrors, setUploadErrors] = useState<UploadIssue[]>([]);

  const uploadFileWithStatus = async (file: File, key: string) => {
    setUploadErrors((current) => current.filter((issue) => issue.key !== key));
    setUploadingFiles((current) => current.some((issue) => issue.key === key) ? current : [...current, { key, file }]);
    try {
      const uploaded = await uploadFile(file);
      setAttachments((current) => [...current, uploaded]);
    } catch {
      setUploadErrors((current) => [...current.filter((issue) => issue.key !== key), { key, file }]);
    } finally {
      setUploadingFiles((current) => current.filter((issue) => issue.key !== key));
    }
  };

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((file, index) => {
      const key = `${Date.now()}-${index}-${file.name}`;
      void uploadFileWithStatus(file, key);
    });
  };

  return <div className="chat-composer shrink-0 border-t border-white/10 bg-[#102219] px-4 py-3"><div className="mx-auto max-w-4xl">
    {uploadingFiles.length > 0 && <div className="mb-2 space-y-2" aria-live="polite">{uploadingFiles.map(({ key, file }) => <div key={key} role="status" aria-busy="true" className="upload-status rounded-lg border px-3 py-2"><div className="mb-2 flex items-center gap-2 text-xs"><FileText size={14} /><span className="min-w-0 flex-1 truncate">{file.name}</span><LoaderCircle size={14} className="animate-spin" /><span>Uploading...</span></div><Skeleton className="h-1.5 w-full rounded-full" /></div>)}</div>}
    {uploadErrors.length > 0 && <div className="mb-2 space-y-2">{uploadErrors.map(({ key, file }) => <div key={key} role="alert" className="upload-error flex items-center gap-2 rounded-lg border px-3 py-2 text-xs"><FileText size={14} /><span className="min-w-0 flex-1 truncate">Could not upload {file.name}.</span><button type="button" onClick={() => void uploadFileWithStatus(file, key)} className="font-semibold underline underline-offset-2">Retry</button></div>)}</div>}
    {attachments.length > 0 && <div className="mb-3 flex flex-wrap gap-2">{attachments.map((file) => <FileAttachment key={file.id} file={file} onRemove={() => setAttachments((current) => current.filter((item) => item.id !== file.id))} />)}</div>}
    <div className="chat-composer-panel rounded-2xl border border-white/10 bg-[#183528] p-2 shadow-2xl">
      <textarea ref={inputRef} value={value} onChange={(event) => { onChange(event.target.value); event.currentTarget.style.height = 'auto'; event.currentTarget.style.height = `${Math.min(event.currentTarget.scrollHeight, 160)}px`; }} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); onSend(); } }} rows={1} placeholder="Message AI Assistant..." className="max-h-40 min-h-11 w-full resize-none bg-transparent px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500" />
      <div className="flex items-center justify-between"><div className="flex gap-1">
        <span className="group relative">
          <button type="button" title="Coming soon" aria-describedby="attach-coming-soon" onClick={() => fileRef.current?.click()} className="rounded-lg p-2 text-slate-400 transition-opacity duration-150 hover:opacity-40 focus-visible:opacity-40"><Paperclip size={17} /></button>
          <span id="attach-coming-soon" role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">Coming soon</span>
        </span>
        <span className="group relative">
          <button type="button" title="Coming soon" aria-describedby="image-coming-soon" onClick={() => fileRef.current?.click()} className="rounded-lg p-2 text-slate-400 transition-opacity duration-150 hover:opacity-40 focus-visible:opacity-40"><ImageIcon size={17} /></button>
          <span id="image-coming-soon" role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">Coming soon</span>
        </span>
        <span className="group relative">
          <button type="button" title="Coming soon" aria-describedby="voice-coming-soon" className="rounded-lg p-2 text-slate-400 transition-opacity duration-150 hover:opacity-40 focus-visible:opacity-40"><Mic size={17} /></button>
          <span id="voice-coming-soon" role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">Coming soon</span>
        </span>
        <input ref={fileRef} type="file" hidden multiple accept=".pdf,.docx,.txt,.csv,image/*" onChange={(event) => { handleFiles(event.target.files); event.currentTarget.value = ''; }} />
      </div><button type="button" onClick={onSend} disabled={sending || !value.trim() || !canSend} title={sending ? 'Assistant is responding' : !canSend ? 'Conversation is still loading' : 'Send message'} className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#b8e978] text-[#20351f] hover:bg-[#c7f28c] disabled:cursor-not-allowed disabled:opacity-40">{sending ? <LoaderCircle size={16} className="animate-spin" /> : <Send size={16} />}</button></div>
    </div><p className="chat-composer-hint mt-1 text-center text-[11px]">Enter to send · Shift+Enter for a new line</p>
  </div></div>;
}
