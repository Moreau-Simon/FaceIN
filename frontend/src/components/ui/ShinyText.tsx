import type { PropsWithChildren } from "react";

type ShinyTextProps = PropsWithChildren<{
  className?: string;
}>;

/**
 * Reflet balayant sur un texte (inspiré de ShinyText, react-bits, licence MIT + Commons Clause).
 * Pur CSS : dégradé masqué par background-clip, animé par keyframes.
 * prefers-reduced-motion : reflet figé, lisibilité inchangée.
 */
export function ShinyText({ children, className }: ShinyTextProps) {
  return <span className={`shiny-text${className ? ` ${className}` : ""}`}>{children}</span>;
}
