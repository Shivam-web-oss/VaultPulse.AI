import type { ReactNode } from 'react';

export function Modal({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}><div className="w-full max-w-lg rounded-2xl border border-white/10 bg-[#101621] p-6" onClick={(event) => event.stopPropagation()}>{children}</div></div>;
}
