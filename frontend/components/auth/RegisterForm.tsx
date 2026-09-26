'use client';

import Link from 'next/link';
import { useRegistration } from '../../hooks/useAuth';

export function RegisterForm() {
  const { form, updateField, handleSubmit, error, isReady } = useRegistration();
  if (!isReady) return null;

  return <>
    <div className="mb-6 text-center"><div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-[#1d2a44] text-lg font-bold">V</div><h1 className="text-2xl font-semibold">Create your account</h1><p className="mt-2 text-sm text-white/60">Start using VaultPulse.AI</p></div>
    <form onSubmit={handleSubmit} className="space-y-4">
      {(['name', 'email', 'password', 'confirmPassword'] as const).map((field) => <label key={field} className="block"><span className="mb-2 block text-sm capitalize text-white/70">{field === 'confirmPassword' ? 'Confirm password' : field}</span><input required type={field === 'email' ? 'email' : field === 'name' ? 'text' : 'password'} value={form[field]} onChange={(event) => updateField(field, event.target.value)} placeholder={field === 'name' ? 'Your name' : field === 'email' ? 'you@example.com' : 'At least 8 characters'} className="w-full rounded-xl border border-white/10 bg-[#171f2d] px-3 py-3 text-white outline-none transition focus:border-blue-400" /></label>)}
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      <button type="submit" className="w-full rounded-xl bg-[#2b6efb] px-4 py-3 font-medium text-white transition hover:brightness-110">Create account</button>
    </form>
    <div className="mt-6 text-center text-sm text-white/60">Already have an account? <Link href="/login" className="font-medium text-blue-400 hover:text-blue-300">Sign in</Link></div>
  </>;
}
