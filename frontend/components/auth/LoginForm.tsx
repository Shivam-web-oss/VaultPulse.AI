'use client';

import Link from 'next/link';
import { useAuth } from '../../hooks/useAuth';

export function LoginForm() {
  const { form, updateField, handleSubmit, error, isReady } = useAuth();
  if (!isReady) return null;

  return <>
    <div className="mb-6 text-center"><div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-[#b8e978] text-lg font-bold text-[#20351f]">V</div><h1 className="text-2xl font-semibold">Welcome back</h1><p className="mt-2 text-sm text-white/60">Sign in to continue to VaultPulse.AI</p></div>
    <form onSubmit={handleSubmit} className="space-y-4">
      <label className="block"><span className="mb-2 block text-sm text-white/70">Email</span><input required type="email" value={form.email} onChange={(event) => updateField('email', event.target.value)} placeholder="you@example.com" className="w-full rounded-xl border border-white/10 bg-[#102219] px-3 py-3 text-white outline-none transition focus:border-[#b8e978]" /></label>
      <label className="block"><span className="mb-2 block text-sm text-white/70">Password</span><input required type="password" value={form.password} onChange={(event) => updateField('password', event.target.value)} placeholder="Enter your password" className="w-full rounded-xl border border-white/10 bg-[#102219] px-3 py-3 text-white outline-none transition focus:border-[#b8e978]" /></label>
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      <button type="submit" className="w-full rounded-xl bg-[#b8e978] px-4 py-3 font-medium text-[#20351f] transition hover:bg-[#c7f28c]">Sign in</button>
    </form>
    <div className="mt-6 text-center text-sm text-white/60">Don&apos;t have an account? <Link href="/register" className="font-medium text-[#c8ef94] hover:text-[#d8f6b0]">Create one</Link></div>
  </>;
}
