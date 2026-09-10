import * as Label from "@radix-ui/react-label";
import { Check, Search } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";

import { cn } from "../../lib/cn";
import type { SelectOption } from "./Select";

type ComboboxProps = {
  label: string;
  options: SelectOption[];
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  noResults: string;
};

function fold(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-PT")
    .trim();
}

/** Searchable single-select for long catalogues, with native combobox semantics. */
export function Combobox({
  label,
  options,
  value,
  onValueChange,
  placeholder,
  noResults,
}: ComboboxProps) {
  const id = useId();
  const listId = `${id}-listbox`;
  const blurTimer = useRef<number>();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const selected = options.find((option) => option.value === value);
  const sorted = useMemo(
    () =>
      [...options].sort((a, b) =>
        a.label.localeCompare(b.label, "pt-PT", { sensitivity: "base" }),
      ),
    [options],
  );
  const visible = useMemo(() => {
    const prefix = fold(query);
    return prefix ? sorted.filter((option) => fold(option.label).startsWith(prefix)) : sorted;
  }, [query, sorted]);

  useEffect(() => {
    if (!open) setQuery(selected?.label ?? "");
  }, [open, selected?.label]);

  useEffect(() => () => window.clearTimeout(blurTimer.current), []);

  function choose(option: SelectOption) {
    window.clearTimeout(blurTimer.current);
    onValueChange(option.value);
    setQuery(option.label);
    setOpen(false);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      setQuery(selected?.label ?? "");
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      const direction = event.key === "ArrowDown" ? 1 : -1;
      setActive((current) => Math.max(0, Math.min(visible.length - 1, current + direction)));
      return;
    }
    if (event.key === "Enter" && open) {
      event.preventDefault();
      if (visible[active]) choose(visible[active]);
    }
  }

  return (
    <div className="relative flex min-w-0 flex-col gap-1">
      <Label.Root htmlFor={id} className="text-sm font-medium text-ink">
        {label}
      </Label.Root>
      <div className="relative">
        <Search
          size={18}
          className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-ink-muted"
          aria-hidden="true"
        />
        <input
          id={id}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={listId}
          aria-activedescendant={
            open && visible[active] ? `${id}-option-${visible[active].value}` : undefined
          }
          autoComplete="off"
          enterKeyHint="search"
          inputMode="search"
          className="min-h-[var(--touch-target)] w-full rounded-[var(--radius-md)] border border-border-strong bg-surface-raised pe-3 ps-10 text-base text-ink placeholder:text-ink-muted"
          placeholder={placeholder}
          value={query}
          onFocus={() => {
            window.clearTimeout(blurTimer.current);
            setQuery("");
            setActive(0);
            setOpen(true);
          }}
          onBlur={() => {
            blurTimer.current = window.setTimeout(() => setOpen(false), 100);
          }}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
            setOpen(true);
            if (value) onValueChange("");
          }}
          onKeyDown={onKeyDown}
        />
      </div>
      {open ? (
        <div
          id={listId}
          role="listbox"
          className={cn(
            "relative z-50 mt-1 max-h-48 touch-pan-y overscroll-contain overflow-y-auto",
            "rounded-[var(--radius-md)] border border-border-strong bg-surface-raised p-1 shadow-lg",
            "sm:absolute sm:inset-x-0 sm:top-full sm:max-h-64",
          )}
        >
          {visible.length === 0 ? (
            <p className="px-3 py-3 text-sm text-ink-muted">{noResults}</p>
          ) : (
            visible.map((option, index) => (
              <div
                id={`${id}-option-${option.value}`}
                key={option.value}
                role="option"
                aria-selected={option.value === value}
                className={cn(
                  "flex min-h-[var(--touch-target)] cursor-pointer items-center justify-between gap-3 rounded-[var(--radius-sm)] px-3 py-2 text-sm text-ink",
                  index === active ? "bg-band" : "hover:bg-band",
                )}
                onPointerDown={(event) => event.preventDefault()}
                onMouseEnter={() => setActive(index)}
                onClick={() => choose(option)}
              >
                <span className="min-w-0 break-words">{option.label}</span>
                {option.value === value ? <Check size={17} aria-hidden="true" /> : null}
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
