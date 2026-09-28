'use client';

import Link from 'next/link';
import { useAuth } from '../../hooks/useAuth';
import { BrandMark } from '../BrandMark';

export function LoginForm() {
  const { form, updateField, handleSubmit, error, isReady } = useAuth();
  if (!isReady) return null;

  return <>
    <div className="mb-6 text-center"><BrandMark size={48} alt="VaultPulse.AI" className="mx-auto mb-3 rounded-xl" /><h1 className="auth-heading text-2xl font-semibold">Welcome back</h1><p className="auth-muted mt-2 text-sm">Sign in to continue to VaultPulse.AI</p></div>
    <form onSubmit={handleSubmit} className="space-y-4">
      <label className="block"><span className="auth-label mb-2 block text-sm">Email</span><input required type="email" value={form.email} onChange={(event) => updateField('email', event.target.value)} placeholder="you@example.com" className="auth-input w-full rounded-xl border px-3 py-3 outline-none focus:border-[#70934f]" /></label>
      <label className="block"><span className="auth-label mb-2 block text-sm">Password</span><input required type="password" value={form.password} onChange={(event) => updateField('password', event.target.value)} placeholder="Enter your password" className="auth-input w-full rounded-xl border px-3 py-3 outline-none focus:border-[#70934f]" /></label>
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      <button type="submit" className="w-full rounded-xl bg-[#b8e978] px-4 py-3 font-medium text-[#20351f] transition hover:bg-[#c7f28c]">Sign in</button>
    </form>
    <div className="auth-muted mt-6 text-center text-sm">Don&apos;t have an account? <Link href="/register" className="auth-link font-medium">Create one</Link></div>
  </>;
}
