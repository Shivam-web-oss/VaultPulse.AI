import { Code2, Lightbulb, MessageCircle, Search } from 'lucide-react';

const suggestions = [
  { label: 'Explain React Server Components', icon: Code2 },
  { label: 'Build a FastAPI API', icon: Search },
  { label: 'Explain JWT authentication', icon: MessageCircle },
  { label: 'Help me debug this code', icon: Lightbulb },
];

export function EmptyChat({ onSelect }: { onSelect: (value: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/20 text-indigo-300"><MessageCircle size={26} /></div>
      <h1 className="text-3xl font-semibold tracking-tight text-white">How can I help you?</h1>
      <p className="mt-3 max-w-md text-sm leading-6 text-slate-400">Ask questions, write code, analyze information, or brainstorm ideas.</p>
      <div className="mt-8 grid w-full max-w-2xl gap-2 sm:grid-cols-2">
        {suggestions.map(({ label, icon: Icon }) => <button key={label} type="button" onClick={() => onSelect(label)} className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3 text-left text-sm text-slate-300 hover:bg-white/[0.08]"><Icon size={16} className="text-indigo-300" />{label}</button>)}
      </div>
    </div>
  );
}
