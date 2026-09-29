import type { HTMLAttributes } from 'react';

type SkeletonProps = HTMLAttributes<HTMLSpanElement> & {
  animated?: boolean;
};

export function Skeleton({ className = '', animated = true, ...props }: SkeletonProps) {
  return <span aria-hidden="true" className={`skeleton ${animated ? 'skeleton-animated' : ''} ${className}`} {...props} />;
}

export function ConversationListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading conversations" aria-busy="true" className="space-y-3 px-2 py-2">
      <span className="sr-only">Loading conversations</span>
      {Array.from({ length: Math.min(Math.max(rows, 1), 6) }, (_, index) => (
        <div key={index} className="flex items-center gap-2.5 py-1">
          <Skeleton className="h-4 w-4 rounded" />
          <Skeleton className="h-3.5 flex-1 rounded" />
        </div>
      ))}
    </div>
  );
}

export function ChatThreadSkeleton() {
  return (
    <div role="status" aria-label="Loading conversation" aria-busy="true" className="mx-auto w-full max-w-4xl space-y-7 py-2">
      <span className="sr-only">Loading conversation</span>
      <div className="flex items-start gap-3">
        <Skeleton className="mt-1 h-7 w-7 shrink-0 rounded-lg" />
        <div className="w-full max-w-xl space-y-2 rounded-2xl border border-[var(--app-border)] bg-[var(--app-surface)] p-4">
          <Skeleton className="h-3.5 w-4/5 rounded" />
          <Skeleton className="h-3.5 w-full rounded" />
          <Skeleton className="h-3.5 w-2/3 rounded" />
        </div>
      </div>
      <div className="flex justify-end">
        <div className="w-full max-w-sm space-y-2 rounded-2xl bg-[var(--vp-lime)] p-4">
          <Skeleton className="h-3.5 w-full rounded" />
          <Skeleton className="h-3.5 w-3/5 rounded" />
        </div>
      </div>
      <div className="flex items-start gap-3">
        <Skeleton className="mt-1 h-7 w-7 shrink-0 rounded-lg" />
        <div className="w-full max-w-lg space-y-2 rounded-2xl border border-[var(--app-border)] bg-[var(--app-surface)] p-4">
          <Skeleton className="h-3.5 w-full rounded" />
          <Skeleton className="h-3.5 w-5/6 rounded" />
          <Skeleton className="h-3.5 w-1/2 rounded" />
        </div>
      </div>
    </div>
  );
}

export function ChatTypingIndicator() {
  return (
    <div role="status" aria-label="Assistant is responding" className="flex items-start gap-3">
      <span aria-hidden="true" className="chat-bot-avatar mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg">AI</span>
      <div className="chat-assistant-message flex items-center gap-1.5 rounded-2xl border px-4 py-3">
        <span className="sr-only">Assistant is responding</span>
        <span aria-hidden="true" className="chat-typing-dot" />
        <span aria-hidden="true" className="chat-typing-dot chat-typing-dot-delay-1" />
        <span aria-hidden="true" className="chat-typing-dot chat-typing-dot-delay-2" />
      </div>
    </div>
  );
}