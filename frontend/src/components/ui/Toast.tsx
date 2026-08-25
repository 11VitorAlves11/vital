import * as RadixToast from "@radix-ui/react-toast";
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

type ToastTone = "success" | "error";
type ToastMessage = { id: number; title: string; tone: ToastTone };

const ToastContext = createContext<((title: string, tone?: ToastTone) => void) | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  const notify = useCallback((title: string, tone: ToastTone = "success") => {
    setMessages((current) => [...current, { id: Date.now() + current.length, title, tone }]);
  }, []);

  const dismiss = useCallback((id: number) => {
    setMessages((current) => current.filter((message) => message.id !== id));
  }, []);

  const value = useMemo(() => notify, [notify]);

  return (
    <ToastContext.Provider value={value}>
      <RadixToast.Provider swipeDirection="right">
        {children}
        {messages.map((message) => (
          <RadixToast.Root
            key={message.id}
            duration={5000}
            onOpenChange={(open) => !open && dismiss(message.id)}
            className={cn(
              "rounded-[var(--radius-md)] border bg-surface-raised px-4 py-3 shadow-[var(--shadow-card)]",
              message.tone === "error" ? "border-flag-alert" : "border-flag-normal",
            )}
          >
            <RadixToast.Title className="text-ink">{message.title}</RadixToast.Title>
          </RadixToast.Root>
        ))}
        <RadixToast.Viewport className="fixed bottom-20 right-4 z-50 flex w-[min(24rem,90vw)] flex-col gap-2 md:bottom-4" />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}

/**
 * Confirmations only. Anything the user has to act on belongs next to the thing
 * that failed, not in a message that disappears on its own.
 */
export function useToast() {
  const notify = useContext(ToastContext);
  if (!notify) throw new Error("useToast must be used inside a ToastProvider");
  return notify;
}
