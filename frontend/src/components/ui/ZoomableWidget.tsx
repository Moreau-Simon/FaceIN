import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";

type ZoomableWidgetProps = {
  title: string;
  children: ReactNode;
};

export function ZoomableWidget({ title, children }: ZoomableWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen && !dialog.open) dialog.showModal();
    if (!isOpen && dialog.open) dialog.close();
  }, [isOpen]);

  return (
    <div className="zoomable-widget">
      {children}
      <button
        className="widget-zoom-trigger"
        type="button"
        aria-label={`Agrandir : ${title}`}
        onClick={() => setIsOpen(true)}
      >
        <span aria-hidden="true">⤢</span>
      </button>
      <dialog
        className="widget-dialog"
        ref={dialogRef}
        aria-labelledby={titleId}
        onCancel={() => setIsOpen(false)}
        onClose={() => setIsOpen(false)}
        onClick={(event) => {
          if (event.target === event.currentTarget) setIsOpen(false);
        }}
      >
        <div className="widget-dialog__header">
          <h2 id={titleId}>{title}</h2>
          <button
            className="widget-dialog__close"
            type="button"
            aria-label="Fermer l’aperçu agrandi"
            onClick={() => setIsOpen(false)}
          >
            ×
          </button>
        </div>
        <div className="widget-dialog__content">{children}</div>
      </dialog>
    </div>
  );
}
