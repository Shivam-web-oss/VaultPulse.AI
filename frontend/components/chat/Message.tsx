import { Bot } from 'lucide-react';
import type { Message as MessageType } from '../../types/chat';
import { MessageActions } from './MessageActions';

function renderContent(content: string) {
  return content.split('\n').map((line, index) => {
    const formatted = line.split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\(https?:\/\/[^)\s]+\))/g).map((part, partIndex) => {
      if (part.startsWith('`') && part.endsWith('`')) return <code key={partIndex} className="chat-inline-code rounded bg-black/30 px-1.5 py-0.5 text-[#c8ef94]">{part.slice(1, -1)}</code>;
      if (part.startsWith('**') && part.endsWith('**')) return <strong key={partIndex}>{part.slice(2, -2)}</strong>;
      const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/);
      if (link) return <a key={partIndex} href={link[2]} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 text-[#c8ef94]">{link[1]}</a>;
      return part;
    });
    return <p key={index} className={index > 0 ? 'mt-2' : ''}>{formatted}</p>;
  });
}

export function Message({ message }: { message: MessageType }) {
  const assistant = message.role === 'assistant';
  return (
    <article className={`group flex gap-2 ${assistant ? 'justify-start' : 'justify-end'}`}>
      {assistant && <div className="chat-bot-avatar mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#b8e978]/15 text-[#c8ef94]"><Bot size={15} /></div>}
      <div className={`min-w-0 max-w-[min(88%,48rem)] rounded-2xl px-3 py-2 text-sm leading-5 break-words ${assistant ? 'chat-assistant-message border border-white/10 bg-[#183528] text-slate-200' : 'chat-user-message bg-[#b8e978] text-[#20351f]'}`}>
        <div className="whitespace-pre-wrap break-words">{renderContent(message.content)}</div>
        <MessageActions content={message.content} assistant={assistant} />
      </div>
    </article>
  );
}
