import { Bot, User } from 'lucide-react';
import type { Message as MessageType } from '../../types/chat';
import { MessageActions } from './MessageActions';

function renderContent(content: string) {
  return content.split('\n').map((line, index) => {
    const formatted = line.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part, partIndex) => {
      if (part.startsWith('`') && part.endsWith('`')) return <code key={partIndex} className="rounded bg-black/30 px-1.5 py-0.5 text-cyan-200">{part.slice(1, -1)}</code>;
      if (part.startsWith('**') && part.endsWith('**')) return <strong key={partIndex}>{part.slice(2, -2)}</strong>;
      return part;
    });
    return <p key={index} className={index > 0 ? 'mt-2' : ''}>{formatted}</p>;
  });
}

export function Message({ message }: { message: MessageType }) {
  const assistant = message.role === 'assistant';
  return (
    <article className={`group flex gap-3 ${assistant ? 'justify-start' : 'justify-end'}`}>
      {assistant && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-300"><Bot size={16} /></div>}
      <div className={`max-w-3xl rounded-2xl px-4 py-3 text-sm leading-6 ${assistant ? 'border border-white/10 bg-[#101a2d] text-slate-200' : 'bg-blue-600 text-white'}`}>
        <div className="whitespace-pre-wrap">{renderContent(message.content)}</div>
        <MessageActions content={message.content} assistant={assistant} />
      </div>
      {!assistant && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-700 text-slate-200"><User size={16} /></div>}
    </article>
  );
}
