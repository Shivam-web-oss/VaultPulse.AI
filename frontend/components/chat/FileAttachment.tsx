import { FileText, X } from 'lucide-react';
import type { Attachment } from '../../types/chat';

export function FileAttachment({ file, onRemove }: { file: Attachment; onRemove: () => void }) {
  return <div className="chat-attachment flex max-w-xs items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs"><FileText size={15} className="text-[#4f7838]" /><span className="truncate">{file.name}</span><button type="button" title="Remove attachment" onClick={onRemove} className="ml-auto text-slate-500 hover:text-white"><X size={14} /></button></div>;
}
