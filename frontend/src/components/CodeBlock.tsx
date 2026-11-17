import { useState } from "react";

type CodeBlockProps = {
  label: string;
  code: string;
  className?: string;
};

export function CodeBlock({ label, code, className = "" }: CodeBlockProps) {
  const [copyMessage, setCopyMessage] = useState("");

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setCopyMessage("Copié dans le presse-papiers.");
    } catch (error) {
      const reason =
        error instanceof Error ? error.message : "presse-papiers indisponible";
      setCopyMessage(`Copie impossible : ${reason}`);
    }
  }

  return (
    <div className={`code-block ${className}`}>
      <div className="code-block__top">
        <span className="code-block__dots" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <span>{label}</span>
        <button className="copy-button" type="button" onClick={copyCode}>
          Copier
        </button>
      </div>
      <pre>
        <code>{code}</code>
      </pre>
      <span className="sr-only" aria-live="polite">
        {copyMessage}
      </span>
    </div>
  );
}
