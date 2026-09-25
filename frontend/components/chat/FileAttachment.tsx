import { FileText, X } from 'lucide-react';
import type { Attachment } from '../../types/chat';

export function FileAttachment({ file, onRemove }: { file: Attachment; onRemove: () => void }) {
  return <div className="flex max-w-xs items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-300"><FileText size={15} className="text-indigo-300" /><span className="truncate">{file.name}</span><button type="button" title="Remove attachment" onClick={onRemove} className="ml-auto text-slate-500 hover:text-white"><X size={14} /></button></div>;
}
