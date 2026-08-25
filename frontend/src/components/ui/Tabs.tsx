import * as RadixTabs from "@radix-ui/react-tabs";
import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

export type TabItem = { value: string; label: string; content: ReactNode };

type TabsProps = {
  items: TabItem[];
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  "aria-label": string;
};

export function Tabs({ items, defaultValue, value, onValueChange, ...props }: TabsProps) {
  return (
    <RadixTabs.Root
      defaultValue={defaultValue ?? items[0]?.value}
      value={value}
      onValueChange={onValueChange}
    >
      <RadixTabs.List
        aria-label={props["aria-label"]}
        className="flex gap-1 overflow-x-auto border-b border-border"
      >
        {items.map((item) => (
          <RadixTabs.Trigger
            key={item.value}
            value={item.value}
            className={cn(
              "min-h-[var(--touch-target)] whitespace-nowrap px-3 text-base text-ink-muted",
              "border-b-2 border-transparent transition-colors duration-[var(--duration-fast)]",
              "data-[state=active]:border-primary data-[state=active]:text-ink",
            )}
          >
            {item.label}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {items.map((item) => (
        <RadixTabs.Content key={item.value} value={item.value} className="pt-4">
          {item.content}
        </RadixTabs.Content>
      ))}
    </RadixTabs.Root>
  );
}
