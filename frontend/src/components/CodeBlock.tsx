import { useState } from "react";

type CodeBlockProps = { label: string; code: string; className?: string };

export function CodeBlock({ label, code, className = "" }: CodeBlockProps) {
  const [copied, setCopied] = useState<"idle" | "ok" | "error">("idle");

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied("ok");
    } catch {
      setCopied("error");
    }
    window.setTimeout(() => setCopied("idle"), 1800);
  }

  return (
    <div className={`code-block ${className}`}>
      <div className="code-block__top">
        <span className="code-block__dots" aria-hidden="true"><i /><i /><i /></span>
        <span>{label}</span>
        <button className={`copy-button${copied === "ok" ? " is-done" : ""}`} type="button" onClick={copyCode}>
          {copied === "ok" ? "Copié" : copied === "error" ? "Copie impossible" : "Copier"}
        </button>
      </div>
      <pre><code>{code}</code></pre>
      <span className="sr-only" aria-live="polite">{copied === "ok" ? "Code copié dans le presse-papiers." : copied === "error" ? "Copie impossible." : ""}</span>
    </div>
  );
}
