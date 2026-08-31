import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "../../lib/cn";

/**
 * The small amount of Markdown a note is worth writing: emphasis, lists, links,
 * and the line breaks someone typed.
 *
 * Raw HTML is not enabled and `rehype-raw` is deliberately absent, so a note is
 * text that renders and never markup that runs. Links are restricted to the
 * protocols react-markdown allows by default — no `javascript:`.
 *
 * Every element is styled explicitly rather than through a prose plugin: this is
 * a handful of tags inside a page that already has a type scale, and inheriting
 * a second one would put two different paragraph sizes on the same card.
 */
export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn("flex max-w-prose flex-col gap-2 text-ink", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p>{children}</p>,
          strong: ({ children }) => <strong className="font-medium">{children}</strong>,
          ul: ({ children }) => <ul className="list-disc pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5">{children}</ol>,
          code: ({ children }) => (
            <code className="data rounded-[var(--radius-sm)] bg-band px-1">{children}</code>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer noopener"
              className="text-primary underline underline-offset-4"
            >
              {children}
            </a>
          ),
          // A note is a paragraph or two inside a card; a heading in one would
          // outrank the card's own title. Rendered as emphasis instead.
          h1: ({ children }) => <p className="font-medium text-ink">{children}</p>,
          h2: ({ children }) => <p className="font-medium text-ink">{children}</p>,
          h3: ({ children }) => <p className="font-medium text-ink">{children}</p>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
