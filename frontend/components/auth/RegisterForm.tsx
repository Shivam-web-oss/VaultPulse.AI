'use client';

import Link from 'next/link';
import { useRegistration } from '../../hooks/useAuth';
import { BrandMark } from '../BrandMark';

export function RegisterForm() {
  const { form, updateField, handleSubmit, error, isReady } = useRegistration();
  if (!isReady) return null;

  return <>
    <div className="mb-6 text-center"><BrandMark size={48} alt="VaultPulse.AI" className="mx-auto mb-3 rounded-xl" /><h1 className="auth-heading text-2xl font-semibold">Create your account</h1><p className="auth-muted mt-2 text-sm">Start using VaultPulse.AI</p></div>
    <form onSubmit={handleSubmit} className="space-y-4">
      {(['name', 'email', 'password', 'confirmPassword'] as const).map((field) => <label key={field} className="block"><span className="auth-label mb-2 block text-sm capitalize">{field === 'confirmPassword' ? 'Confirm password' : field}</span><input required type={field === 'email' ? 'email' : field === 'name' ? 'text' : 'password'} value={form[field]} onChange={(event) => updateField(field, event.target.value)} placeholder={field === 'name' ? 'Your name' : field === 'email' ? 'you@example.com' : 'At least 8 characters'} className="auth-input w-full rounded-xl border px-3 py-3 outline-none focus:border-[#70934f]" /></label>)}
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      <button type="submit" className="w-full rounded-xl bg-[#b8e978] px-4 py-3 font-medium text-[#20351f] transition hover:bg-[#c7f28c]">Create account</button>
    </form>
    <div className="auth-muted mt-6 text-center text-sm">Already have an account? <Link href="/login" className="auth-link font-medium">Sign in</Link></div>
  </>;
}
