import type { ReactNode } from 'react';

export function Dropdown({ children }: { children: ReactNode }) {
  return <div className="relative">{children}</div>;
}
