'use client';

import { useState } from 'react';
import { ArrowLeft, Check, Moon, Monitor, Sun } from 'lucide-react';
import Link from 'next/link';
import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { DEFAULT_CHAT_ROUTE } from '../../routes';

type Settings = { appearance: 'light' | 'dark' | 'system'; enterToSend: boolean; autoScroll: boolean; timestamps: boolean };
const defaults: Settings = { appearance: 'dark', enterToSend: true, autoScroll: true, timestamps: false };

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(() => {
    if (typeof window === 'undefined') return defaults;
    const stored = localStorage.getItem('ai-assistant-settings');
    return stored ? JSON.parse(stored) as Settings : defaults;
  });
  const update = (next: Partial<Settings>) => { const value = { ...settings, ...next }; setSettings(value); localStorage.setItem('ai-assistant-settings', JSON.stringify(value)); };
  return <ProtectedRoute><main className="min-h-screen bg-[#020817] px-4 py-8 text-slate-100"><div className="mx-auto max-w-2xl"><Link href={DEFAULT_CHAT_ROUTE} className="mb-8 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"><ArrowLeft size={16} />Back to chat</Link><h1 className="text-3xl font-semibold">Settings</h1><p className="mt-2 text-sm text-slate-400">Personalize your assistant workspace.</p><section className="mt-8 border-t border-white/10 py-6"><h2 className="font-medium">Appearance</h2><div className="mt-4 grid grid-cols-3 gap-2">{(['light', 'dark', 'system'] as const).map((appearance) => { const Icon = appearance === 'light' ? Sun : appearance === 'dark' ? Moon : Monitor; return <button key={appearance} type="button" onClick={() => update({ appearance })} className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-3 text-sm capitalize ${settings.appearance === appearance ? 'border-indigo-400 bg-indigo-500/15 text-white' : 'border-white/10 text-slate-400 hover:bg-white/5'}`}><Icon size={16} />{appearance}{settings.appearance === appearance && <Check size={14} />}</button>; })}</div></section><section className="border-t border-white/10 py-6"><h2 className="font-medium">Chat</h2>{[['enterToSend', 'Enter to send'], ['autoScroll', 'Auto-scroll'], ['timestamps', 'Show timestamps']].map(([key, label]) => <label key={key} className="mt-4 flex items-center justify-between text-sm text-slate-300"><span>{label}</span><input type="checkbox" checked={settings[key as keyof Settings] as boolean} onChange={(event) => update({ [key]: event.target.checked })} className="h-4 w-4 accent-indigo-500" /></label>)}</section></div></main></ProtectedRoute>;
}
