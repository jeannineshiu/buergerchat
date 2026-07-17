import type { ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import remarkCjkFriendly from "remark-cjk-friendly";
import remarkGfm from "remark-gfm";

type MdProps<T extends keyof React.JSX.IntrinsicElements> = ComponentProps<T> & {
  node?: unknown;
};

function Anchor({ node: _node, ...props }: MdProps<"a">) {
  return (
    <a
      {...props}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-blue-700 underline decoration-blue-300 underline-offset-2 transition hover:decoration-blue-600 dark:text-blue-400 dark:decoration-blue-800 dark:hover:decoration-blue-400"
    />
  );
}

// Answers come from the model as markdown (bold, lists, links). Rendering it
// properly — instead of showing literal ** — is what keeps plain-language
// answers scannable. Headings are flattened to bold paragraphs: a chat bubble
// is no place for h1 typography.
export function Markdown({ children }: { children: string }) {
  return (
    // dir="auto": answers can be Arabic (RTL) — let the browser pick per block.
    <div dir="auto" className="space-y-2.5 break-words">
      {/* remark-cjk-friendly: CommonMark refuses to close `**` when it sits
          between CJK punctuation and a CJK letter (e.g. `**（家庭金辦公室）**可以`),
          leaving literal asterisks in Chinese/Japanese answers. */}
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkCjkFriendly]}
        components={{
          a: Anchor,
          p: ({ node: _node, ...props }: MdProps<"p">) => (
            <p {...props} className="leading-relaxed" />
          ),
          strong: ({ node: _node, ...props }: MdProps<"strong">) => (
            <strong {...props} className="font-semibold" />
          ),
          ul: ({ node: _node, ...props }: MdProps<"ul">) => (
            <ul {...props} className="list-disc space-y-1.5 ps-5" />
          ),
          ol: ({ node: _node, ...props }: MdProps<"ol">) => (
            <ol {...props} className="list-decimal space-y-1.5 ps-5" />
          ),
          li: ({ node: _node, ...props }: MdProps<"li">) => (
            <li {...props} className="leading-relaxed" />
          ),
          h1: ({ node: _node, children, ...props }: MdProps<"h1">) => (
            <p {...props} className="font-semibold">{children}</p>
          ),
          h2: ({ node: _node, children, ...props }: MdProps<"h2">) => (
            <p {...props} className="font-semibold">{children}</p>
          ),
          h3: ({ node: _node, children, ...props }: MdProps<"h3">) => (
            <p {...props} className="font-semibold">{children}</p>
          ),
          h4: ({ node: _node, children, ...props }: MdProps<"h4">) => (
            <p {...props} className="font-semibold">{children}</p>
          ),
          blockquote: ({ node: _node, ...props }: MdProps<"blockquote">) => (
            <blockquote
              {...props}
              className="border-s-2 border-zinc-300 ps-3 text-zinc-600 dark:border-zinc-600 dark:text-zinc-300"
            />
          ),
          code: ({ node: _node, ...props }: MdProps<"code">) => (
            <code
              {...props}
              className="rounded bg-zinc-200/70 px-1 py-0.5 font-mono text-[0.85em] dark:bg-zinc-700/70"
            />
          ),
          hr: () => <hr className="border-zinc-200 dark:border-zinc-700" />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
