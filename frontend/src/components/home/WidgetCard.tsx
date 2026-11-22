import { useEffect, useId, useRef, useState } from "react";
import type { PointerEvent, ReactNode } from "react";
import { animate, useReducedMotion } from "motion/react";

type WidgetCardProps = {
  title: ReactNode;
  label: string;
  className?: string;
  children: (expanded: boolean) => ReactNode;
};

const INTERACTIVE = "button, a, input, label, [data-interactive]";

/**
 * Carte de la page d'accueil : halo qui suit le pointeur, élévation au survol,
 * pression au clic, puis ouverture agrandie animée depuis la position de la carte.
 */
export function WidgetCard({ title, label, className = "", children }: WidgetCardProps) {
  const cardRef = useRef<HTMLElement>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const closing = useRef(false);
  const reduce = useReducedMotion();
  const titleId = useId();

  function track(event: PointerEvent<HTMLElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty("--mx", `${event.clientX - rect.left}px`);
    event.currentTarget.style.setProperty("--my", `${event.clientY - rect.top}px`);
  }

  function flipFrom() {
    const card = cardRef.current?.getBoundingClientRect();
    const panel = panelRef.current?.getBoundingClientRect();
    if (!card || !panel) return null;
    return {
      x: card.left + card.width / 2 - (panel.left + panel.width / 2),
      y: card.top + card.height / 2 - (panel.top + panel.height / 2),
      scaleX: card.width / panel.width,
      scaleY: card.height / panel.height,
    };
  }

  function openDialog() {
    if (open) return;
    setOpen(true);
  }

  useEffect(() => {
    const dialog = dialogRef.current;
    const panel = panelRef.current;
    if (!open || !dialog || !panel) return;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    const from = flipFrom();
    if (from && !reduce) {
      animate(panel, { x: [from.x, 0], y: [from.y, 0], scaleX: [from.scaleX, 1], scaleY: [from.scaleY, 1], opacity: [0.4, 1] }, { type: "spring", stiffness: 260, damping: 30 });
    }
    return () => { document.body.style.overflow = ""; };
  }, [open, reduce]);

  async function closeDialog() {
    const dialog = dialogRef.current;
    const panel = panelRef.current;
    if (!dialog || !panel || closing.current) return;
    closing.current = true;
    const from = flipFrom();
    if (from && !reduce) {
      await animate(panel, { x: from.x, y: from.y, scaleX: from.scaleX, scaleY: from.scaleY, opacity: 0 }, { duration: 0.28, ease: [0.4, 0, 0.2, 1] });
    }
    dialog.close();
    panel.style.transform = "";
    panel.style.opacity = "";
    closing.current = false;
    setOpen(false);
    cardRef.current?.querySelector<HTMLButtonElement>(".widget-card__expand")?.focus();
  }

  return (
    <>
      <article
        ref={cardRef}
        className={`widget-card ${className}`}
        onPointerMove={track}
        onClick={(event) => {
          if ((event.target as HTMLElement).closest(INTERACTIVE)) return;
          openDialog();
        }}
      >
        <header className="widget-card__head">
          <h3>{title}</h3>
          <button className="widget-card__expand" type="button" aria-label={`Agrandir : ${label}`} onClick={openDialog}>
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M9.5 2.5h4v4M6.5 13.5h-4v-4M13.5 2.5 9 7M2.5 13.5 7 9" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        </header>
        <div className="widget-card__body">{children(false)}</div>
      </article>
      <dialog
        ref={dialogRef}
        className="widget-dialog"
        aria-labelledby={titleId}
        onCancel={(event) => { event.preventDefault(); void closeDialog(); }}
        onClick={(event) => { if (event.target === dialogRef.current) void closeDialog(); }}
      >
        <div ref={panelRef} className={`widget-dialog__panel ${className}`}>
          <header className="widget-dialog__head">
            <h2 id={titleId}>{label}</h2>
            <button className="widget-dialog__close" type="button" aria-label="Fermer" onClick={() => void closeDialog()}>
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
            </button>
          </header>
          <div className="widget-dialog__body">{open && children(true)}</div>
        </div>
      </dialog>
    </>
  );
}
